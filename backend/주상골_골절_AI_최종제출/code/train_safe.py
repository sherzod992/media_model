"""
train_safe.py — GPU 메모리 안전 + 과적합 방지 파인튜닝

개선 사항:
  [메모리]  expandable_segments + max_split_size 설정
            그래디언트 누적(accum=4) → 스파이크 없이 유효 배치 32
            매 에포크 cuda.empty_cache()
            cudnn.benchmark=False (알고리즘 탐색 메모리 스파이크 방지)
  [정규화]  Label Smoothing(0.05) + 정상 클래스 가중치 1.5×
            Dropout 0.4  + MixUp(alpha=0.2, p=0.4)
            RandomErasing, 강화된 증강
  [체크포인트]  복합 점수 = AUC + 0.5×Specificity  (민감도≥90% 조건 충족 시)
              조건 미충족 시 → AUC만으로 저장
  [학습]    Phase1 백본 동결 15ep → Phase2 전체 해동 저학습률

Usage:
  # DenseNet (v3ft 사전학습 가중치 사용)
  python train_safe.py --model densenet121 --pretrained runs/v3ft_densenet/weights/best.pth

  # EfficientNet (v3ft 사전학습 가중치 사용)
  python train_safe.py --model efficientnet_b3 --pretrained runs/v3ft_effnet/weights/best.pth

  # 사전학습 없이 ImageNet에서 시작
  python train_safe.py --model efficientnet_b3
"""

# ─── 메모리 설정: torch import 전에 반드시 설정 ────────────────────────────────
import os
os.environ.setdefault(
    "PYTORCH_CUDA_ALLOC_CONF",
    "expandable_segments:True,max_split_size_mb:256",
)

import argparse
import json
import math
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms

torch.backends.cudnn.benchmark = False   # 알고리즘 탐색 메모리 스파이크 방지

try:
    import timm
except ImportError:
    raise SystemExit("timm 필요: pip install timm")

SEED         = 42
CLASSES      = ["fracture", "normal"]
FRACTURE_IDX = 0
NORMAL_IDX   = 1
MEAN = [0.485, 0.456, 0.406]
STD  = [0.229, 0.224, 0.225]

# ─── 모델 설정 ─────────────────────────────────────────────────────────────────
MODEL_CFG = {
    "densenet121": {
        "timm_name": "densenet121",
        "imgsz":      224,
        "lr":         3e-4,
        "lr_backbone": 3e-5,
        "weight_decay": 1e-3,
        "drop_rate":  0.4,
        "batch":      8,
        "accum":      4,   # 유효 배치 = 8×4 = 32
    },
    "efficientnet_b3": {
        "timm_name": "efficientnet_b3",
        "imgsz":      300,
        "lr":         3e-4,
        "lr_backbone": 3e-5,
        "weight_decay": 1e-3,
        "drop_rate":  0.4,
        "batch":      8,
        "accum":      4,   # 유효 배치 = 8×4 = 32
    },
}


# ─── 손실 함수 ─────────────────────────────────────────────────────────────────

class SmoothedFocalLoss(nn.Module):
    """Label Smoothing + 클래스 가중치 + Focal Loss 통합
    - smoothing:    0.05 → 예측 과신 억제
    - normal_w:     정상 클래스 가중치 1.5 → FP 페널티 강화 → 특이도 향상
    - gamma:        2.0  → Focal weighting
    """
    def __init__(self, gamma: float = 2.0, smoothing: float = 0.05,
                 normal_w: float = 1.5):
        super().__init__()
        self.gamma    = gamma
        self.smoothing = smoothing
        self.normal_w  = normal_w

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        n_cls = logits.size(1)
        # 클래스 가중치: [fracture=1.0, normal=normal_w]
        cls_w = torch.ones(n_cls, device=logits.device)
        cls_w[NORMAL_IDX] = self.normal_w

        # Label Smoothing 적용 (hard label → soft label)
        with torch.no_grad():
            smooth = torch.full_like(logits, self.smoothing / n_cls)
            smooth.scatter_(1, targets.unsqueeze(1), 1.0 - self.smoothing + self.smoothing / n_cls)

        log_p = F.log_softmax(logits, dim=1)
        # 클래스 가중치 반영한 CE
        ce = -(smooth * log_p * cls_w.unsqueeze(0)).sum(1)
        pt = torch.exp(-ce)
        return ((1.0 - pt) ** self.gamma * ce).mean()


# ─── MixUp ────────────────────────────────────────────────────────────────────

def mixup_batch(imgs: torch.Tensor, labels: torch.Tensor, alpha: float = 0.2):
    """배치 내 MixUp. (mixed_imgs, label_a, label_b, lam) 반환."""
    lam = float(np.random.beta(alpha, alpha))
    idx = torch.randperm(imgs.size(0), device=imgs.device)
    return lam * imgs + (1.0 - lam) * imgs[idx], labels, labels[idx], lam


def mixup_loss(criterion, pred, y_a, y_b, lam):
    return lam * criterion(pred, y_a) + (1.0 - lam) * criterion(pred, y_b)


# ─── 유틸 ─────────────────────────────────────────────────────────────────────

def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def vram_mb() -> float:
    if torch.cuda.is_available():
        return torch.cuda.memory_reserved() / 1024 ** 2
    return 0.0


def build_transform(imgsz: int, is_train: bool):
    if is_train:
        return transforms.Compose([
            transforms.Resize((imgsz, imgsz)),
            transforms.RandomHorizontalFlip(0.5),
            transforms.RandomRotation(12),
            transforms.RandomAffine(degrees=0, translate=(0.08, 0.08), scale=(0.88, 1.12)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
            transforms.RandomErasing(p=0.2, scale=(0.02, 0.12)),
        ])
    return transforms.Compose([
        transforms.Resize((imgsz, imgsz)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


def make_sampler(dataset) -> WeightedRandomSampler:
    labels  = [s[1] for s in dataset.samples]
    counts  = [labels.count(c) for c in range(len(CLASSES))]
    total   = sum(counts)
    cls_w   = [total / (len(CLASSES) * c) for c in counts]
    smp_w   = [cls_w[l] for l in labels]
    return WeightedRandomSampler(smp_w, len(smp_w), replacement=True)


def cosine_lambda(warmup: int, total: int, lrf: float = 0.01):
    def fn(ep):
        if ep < warmup:
            return (ep + 1) / warmup
        p = (ep - warmup) / max(total - warmup, 1)
        return lrf + 0.5 * (1.0 - lrf) * (1.0 + math.cos(math.pi * p))
    return fn


# ─── 평가 ─────────────────────────────────────────────────────────────────────

@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    tot_loss, tot_n = 0.0, 0
    y_true, y_score = [], []
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        logits = model(imgs)
        tot_loss += criterion(logits, labels).item() * imgs.size(0)
        tot_n    += imgs.size(0)
        probs = torch.softmax(logits, 1)
        y_true.extend(labels.cpu().tolist())
        y_score.extend(probs[:, FRACTURE_IDX].cpu().tolist())
    y_true  = np.array(y_true)
    y_score = np.array(y_score)
    frac    = y_true == FRACTURE_IDX
    y_pred  = (y_score >= 0.5).astype(int)
    tp = int(np.sum((y_pred == 0) & frac))
    fn = int(np.sum((y_pred != 0) & frac))
    tn = int(np.sum((y_pred != 0) & ~frac))
    fp = int(np.sum((y_pred == 0) & ~frac))
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    try:
        auc = roc_auc_score(frac.astype(int), y_score)
    except Exception:
        auc = 0.5
    return tot_loss / tot_n, sens, spec, auc, tp, fn, tn, fp


# ─── 학습 메인 ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",      default="densenet121",
                        choices=list(MODEL_CFG))
    parser.add_argument("--dataset",    default="dataset")
    parser.add_argument("--pretrained", default=None,
                        help="v3ft 사전학습 가중치 경로")
    parser.add_argument("--epochs",     type=int,   default=120)
    parser.add_argument("--patience",   type=int,   default=25)
    parser.add_argument("--phase1",     type=int,   default=15,
                        help="백본 동결 에포크 수")
    parser.add_argument("--mixup-p",    type=float, default=0.4,
                        help="MixUp 적용 확률 (0=비활성)")
    parser.add_argument("--normal-w",   type=float, default=1.5,
                        help="정상 클래스 손실 가중치 (>1 → 특이도 향상)")
    parser.add_argument("--run-name",   default=None)
    args = parser.parse_args()

    set_seed(SEED)
    cfg      = MODEL_CFG[args.model]
    run_name = args.run_name or f"safe_{args.model}"
    run_dir  = Path("runs") / run_name
    wdir     = run_dir / "weights"
    wdir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"\n{'='*65}")
    print(f"모델     : {args.model}  ({cfg['imgsz']}px × {cfg['imgsz']}px)")
    print(f"Device   : {device}  VRAM reserved={vram_mb():.0f}MB")
    print(f"유효배치 : {cfg['batch']} × accum{cfg['accum']} = {cfg['batch']*cfg['accum']}")
    print(f"MixUp    : p={args.mixup_p}  normal_w={args.normal_w}")
    if args.pretrained:
        print(f"사전학습 : {args.pretrained}")
    print(f"{'='*65}\n")

    root = Path(args.dataset)
    train_ds = datasets.ImageFolder(str(root / "train"),
                                    transform=build_transform(cfg["imgsz"], True))
    val_ds   = datasets.ImageFolder(str(root / "val"),
                                    transform=build_transform(cfg["imgsz"], False))

    n_frac = sum(1 for _, l in train_ds.samples if l == FRACTURE_IDX)
    n_norm = len(train_ds) - n_frac
    print(f"Train: 골절={n_frac} 정상={n_norm}  → WeightedSampler 1:1 균형")

    train_loader = DataLoader(train_ds, batch_size=cfg["batch"],
                              sampler=make_sampler(train_ds),
                              num_workers=0, pin_memory=False)
    val_loader   = DataLoader(val_ds, batch_size=cfg["batch"] * 2,
                              shuffle=False, num_workers=0, pin_memory=False)

    # 모델 로드
    model = timm.create_model(
        cfg["timm_name"],
        pretrained=(args.pretrained is None),
        num_classes=len(CLASSES),
        drop_rate=cfg["drop_rate"],
    ).to(device)

    if args.pretrained:
        ckpt = torch.load(args.pretrained, map_location=device, weights_only=True)
        missing, unexpected = model.load_state_dict(ckpt, strict=False)
        if missing:
            print(f"  [경고] 누락된 키 {len(missing)}개 → ImageNet 초기화 사용")
        print(f"  사전학습 가중치 로드 완료")
    print(f"  파라미터: {sum(p.numel() for p in model.parameters())/1e6:.1f}M\n")

    criterion = SmoothedFocalLoss(gamma=2.0, smoothing=0.05, normal_w=args.normal_w)
    scaler    = torch.amp.GradScaler("cuda") if device.type == "cuda" else None

    ACCUM = cfg["accum"]
    is_head = lambda n: any(k in n for k in ("classifier", "head", "fc"))

    # ── Phase 1: 백본 동결 ──────────────────────────────────────────────────
    for n, p in model.named_parameters():
        p.requires_grad_(is_head(n))
    head_ps = [p for n, p in model.named_parameters() if p.requires_grad]
    print(f"[Phase 1] 백본 동결 | 학습 파라미터: {sum(p.numel() for p in head_ps)/1e6:.2f}M")
    optimizer = torch.optim.AdamW(head_ps, lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, cosine_lambda(3, args.phase1))

    best_auc_score  = 0.0
    best_comp_score = 0.0
    patience_cnt    = 0
    history = {k: [] for k in ("train_loss","val_loss","val_auc","val_sens","val_spec")}

    for epoch in range(1, args.epochs + 1):

        # Phase 2 전환
        if epoch == args.phase1 + 1:
            for p in model.parameters():
                p.requires_grad_(True)
            remaining = args.epochs - args.phase1
            optimizer = torch.optim.AdamW([
                {"params": [p for n, p in model.named_parameters() if is_head(n)],
                 "lr": cfg["lr"]},
                {"params": [p for n, p in model.named_parameters() if not is_head(n)],
                 "lr": cfg["lr_backbone"]},
            ], weight_decay=cfg["weight_decay"])
            scheduler = torch.optim.lr_scheduler.LambdaLR(
                optimizer, cosine_lambda(1, remaining))
            print(f"\n[Phase 2] 전체 해동 | "
                  f"파라미터: {sum(p.numel() for p in model.parameters())/1e6:.1f}M")

        # ── Train ─────────────────────────────────────────────────────────
        model.train()
        t_loss, t_n = 0.0, 0
        optimizer.zero_grad()
        for step, (imgs, labels) in enumerate(train_loader):
            imgs, labels = imgs.to(device), labels.to(device)

            # MixUp 적용
            use_mixup = (random.random() < args.mixup_p) and (epoch > args.phase1)
            if use_mixup:
                imgs, y_a, y_b, lam = mixup_batch(imgs, labels)

            if scaler:
                with torch.amp.autocast("cuda"):
                    logits = model(imgs)
                    if use_mixup:
                        loss = mixup_loss(criterion, logits, y_a, y_b, lam)
                    else:
                        loss = criterion(logits, labels)
                    loss = loss / ACCUM
                scaler.scale(loss).backward()
            else:
                logits = model(imgs)
                if use_mixup:
                    loss = mixup_loss(criterion, logits, y_a, y_b, lam)
                else:
                    loss = criterion(logits, labels)
                (loss / ACCUM).backward()

            t_loss += loss.item() * ACCUM * imgs.size(0)
            t_n    += imgs.size(0)

            # 그래디언트 누적 스텝
            if (step + 1) % ACCUM == 0 or step == len(train_loader) - 1:
                if scaler:
                    scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                if scaler:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                optimizer.zero_grad()

        scheduler.step()
        t_loss /= t_n

        # ── Validate ──────────────────────────────────────────────────────
        v_loss, v_sens, v_spec, v_auc, tp, fn, tn, fp = evaluate(
            model, val_loader, criterion, device)

        # 매 에포크 후 VRAM 비움
        torch.cuda.empty_cache()

        for k, v in zip(
            ("train_loss","val_loss","val_auc","val_sens","val_spec"),
            (t_loss, v_loss, v_auc, v_sens, v_spec)
        ):
            history[k].append(v)

        # ── 체크포인트 저장 ───────────────────────────────────────────────
        # 복합 점수: 민감도가 높을수록 특이도 비중 강화
        if v_sens >= 0.95:
            comp_score = 0.5 * v_auc + 0.5 * v_spec   # 특이도와 동등 가중
        elif v_sens >= 0.90:
            comp_score = v_auc + 0.5 * v_spec
        else:
            comp_score = v_auc   # 민감도 미달 시 AUC만으로 판단

        flag = ""
        if v_auc > best_auc_score:
            best_auc_score = v_auc
            torch.save(model.state_dict(), wdir / "best_auc.pth")
            flag += " [AUC]"
        if comp_score > best_comp_score:
            best_comp_score = comp_score
            patience_cnt = 0
            torch.save(model.state_dict(), wdir / "best.pth")   # 최종 사용 체크포인트
            flag += " [BEST]"
        else:
            patience_cnt += 1

        phase = "Ph1" if epoch <= args.phase1 else "Ph2"
        lr_now = optimizer.param_groups[0]["lr"]
        vram = vram_mb()
        print(
            f"Ep{epoch:3d}/{args.epochs} {phase} | "
            f"TrL={t_loss:.4f} | "
            f"VaL={v_loss:.4f} AUC={v_auc:.4f} | "
            f"Sens={v_sens:.1%} Spec={v_spec:.1%} | "
            f"TP={tp} FN={fn} TN={tn} FP={fp} | "
            f"VRAM={vram:.0f}MB lr={lr_now:.1e}{flag}",
            flush=True,
        )

        if patience_cnt >= args.patience:
            print(f"\n조기 종료 (epoch {epoch}, patience={args.patience})")
            break

    # model_info.json 저장
    with open(wdir / "model_info.json", "w") as f:
        json.dump({
            "timm_name": cfg["timm_name"],
            "imgsz":     cfg["imgsz"],
            "drop_rate": cfg["drop_rate"],
        }, f, indent=2)

    # 학습 곡선 저장
    fig, axes = plt.subplots(1, 3, figsize=(18, 4))
    axes[0].plot(history["train_loss"], label="train")
    axes[0].plot(history["val_loss"],   label="val")
    axes[0].set_title("Loss"); axes[0].legend()
    axes[1].plot(history["val_auc"], color="steelblue")
    axes[1].axhline(best_auc_score, ls="--", color="red", alpha=0.5,
                    label=f"Best={best_auc_score:.4f}")
    axes[1].set_title("Val AUC"); axes[1].set_ylim(0, 1); axes[1].legend()
    axes[2].plot(history["val_sens"], label="Sensitivity")
    axes[2].plot(history["val_spec"], label="Specificity")
    axes[2].set_title("Val Sens / Spec"); axes[2].legend()
    plt.tight_layout()
    plt.savefig(run_dir / "curves.png", dpi=150)
    plt.close()

    print(f"\n학습 완료")
    print(f"최고 AUC    : {best_auc_score:.4f}")
    print(f"최고 복합점수: {best_comp_score:.4f}")
    print(f"가중치(최종): {wdir / 'best.pth'}")
    print(f"\n앙상블 평가:")
    print(f"  python ensemble_final.py")


if __name__ == "__main__":
    main()
