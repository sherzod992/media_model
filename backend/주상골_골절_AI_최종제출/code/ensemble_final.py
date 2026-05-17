"""
ensemble_final.py — 최종 앙상블 평가 (메모리 안전)

모델 구성 (기본값):
  YOLOv8m-cls       가중치 2.0  (특이도 75%로 가장 높음)
  EfficientNet-B3   가중치 2.0  (민감도·AUC 균형)
  DenseNet-121      가중치 1.0  (민감도 강점, 특이도 낮음)

임계값 전략:
  1) val 세트에서 민감도 ≥ 98% 조건 중 특이도 최대인 임계값 선택
  2) 조건 달성 불가 시 → Youden's J (sens+spec-1 최대화)

Usage:
  python ensemble_final.py                    # 기본 3-모델
  python ensemble_final.py --no-old           # DenseNet 제외 (2-모델)
  python ensemble_final.py --dn-ckpt runs/safe_densenet121/weights/best.pth
  python ensemble_final.py --ef-ckpt runs/safe_efficientnet_b3/weights/best.pth
"""

import os
os.environ.setdefault(
    "PYTORCH_CUDA_ALLOC_CONF",
    "expandable_segments:True,max_split_size_mb:256",
)

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import (auc, classification_report,
                             confusion_matrix, ConfusionMatrixDisplay, roc_curve)
from torchvision import transforms

torch.backends.cudnn.benchmark = False

try:
    import timm
    from ultralytics import YOLO
except ImportError as e:
    raise SystemExit(f"패키지 필요: {e}")

CLASSES      = ["fracture", "normal"]
FRACTURE_IDX = 0
MEAN = [0.485, 0.456, 0.406]
STD  = [0.229, 0.224, 0.225]
TTA_CONFIGS = [
    (False,  0), (True,   0),
    (False, 10), (True,  10),
    (False,-10), (True, -10),
    (False, 20), (True, -20),
]


# ─── 데이터 ───────────────────────────────────────────────────────────────────

def collect(split_dir: Path):
    samples = []
    for ci, cls in enumerate(CLASSES):
        for p in sorted((split_dir / cls).glob("*.jpg")):
            samples.append((p, ci))
    return samples


# ─── 모델 로더 ────────────────────────────────────────────────────────────────

def load_timm_model(ckpt: Path, device: torch.device):
    info = json.load(open(ckpt.parent / "model_info.json"))
    m = timm.create_model(
        info["timm_name"], pretrained=False,
        num_classes=2, drop_rate=info.get("drop_rate", 0.2),
    ).to(device)
    m.load_state_dict(
        torch.load(ckpt, map_location=device, weights_only=True)
    )
    m.eval()
    return m, int(info["imgsz"])


# ─── 추론 ─────────────────────────────────────────────────────────────────────

@torch.no_grad()
def infer_timm(model, samples, imgsz: int, device: torch.device,
               tta: bool = True) -> np.ndarray:
    cfgs = TTA_CONFIGS if tta else [TTA_CONFIGS[0]]
    acc  = np.zeros(len(samples))
    for hflip, angle in cfgs:
        ops = [transforms.Resize((imgsz, imgsz))]
        if hflip:  ops.append(transforms.RandomHorizontalFlip(1.0))
        if angle:  ops.append(transforms.RandomRotation((angle, angle)))
        ops += [transforms.ToTensor(), transforms.Normalize(MEAN, STD)]
        tfm = transforms.Compose(ops)
        for i, (path, _) in enumerate(samples):
            img = tfm(Image.open(path).convert("RGB")).unsqueeze(0).to(device)
            acc[i] += torch.softmax(model(img), 1)[0, FRACTURE_IDX].item()
        torch.cuda.empty_cache()
    return acc / len(cfgs)


def infer_yolo(yolo_model, samples) -> np.ndarray:
    paths   = [str(p) for p, _ in samples]
    results = yolo_model.predict(paths, imgsz=640, augment=True, verbose=False)
    return np.array([r.probs.data.cpu().numpy()[FRACTURE_IDX] for r in results])


# ─── 임계값 최적화 ────────────────────────────────────────────────────────────

def find_threshold(probs: np.ndarray, labels: np.ndarray,
                   target_sens: float = 0.98) -> tuple[float, str]:
    """
    1차: sens >= target_sens 조건 중 특이도 최대인 임계값
    2차: 조건 달성 불가 → Youden's J 최대
    """
    frac = labels == FRACTURE_IDX
    candidates = []
    for thr in np.arange(0.01, 0.99, 0.002):
        pred = probs >= thr
        tp = np.sum(pred & frac);  fn = np.sum(~pred & frac)
        tn = np.sum(~pred & ~frac); fp = np.sum(pred & ~frac)
        sens = tp/(tp+fn) if (tp+fn)>0 else 0.0
        spec = tn/(tn+fp) if (tn+fp)>0 else 0.0
        j    = sens + spec - 1.0
        candidates.append((thr, sens, spec, j))

    # 1차: 민감도 조건 충족 + 특이도 최대
    primary = [(t, s, sp, j) for t, s, sp, j in candidates if s >= target_sens]
    if primary:
        best = max(primary, key=lambda x: x[2])
        return best[0], f"sens≥{target_sens:.0%} 중 spec최대"

    # 2차: Youden's J
    best = max(candidates, key=lambda x: x[3])
    return best[0], "Youden-J (민감도 조건 미달)"


# ─── 평가 & 시각화 ────────────────────────────────────────────────────────────

def evaluate_and_plot(probs: np.ndarray, labels: np.ndarray,
                      thr: float, out_dir: Path, tag: str):
    pred_frac = probs >= thr          # True = 골절 예측 (high prob)
    frac      = labels == FRACTURE_IDX  # True = 실제 골절

    tp = int(np.sum( pred_frac &  frac))
    fn = int(np.sum(~pred_frac &  frac))
    fp = int(np.sum( pred_frac & ~frac))
    tn = int(np.sum(~pred_frac & ~frac))

    sens = tp/(tp+fn) if (tp+fn)>0 else 0.0
    spec = tn/(tn+fp) if (tn+fp)>0 else 0.0
    acc  = (tp+tn) / len(labels)
    prec = tp/(tp+fp) if (tp+fp)>0 else 0.0
    f1   = 2*prec*sens/(prec+sens) if (prec+sens)>0 else 0.0

    fpr, tpr, _ = roc_curve(frac.astype(int), probs)
    roc_auc     = auc(fpr, tpr)

    # sklearn: 0=fracture, 1=normal (pred_frac=True→0, False→1)
    preds = (~pred_frac).astype(int)

    print(f"\n{'='*60}")
    print(f"[{tag.upper()}]  임계값 = {thr:.3f}")
    print(f"  정확도  : {acc:.1%}  ({tp+tn}/{len(labels)})")
    print(f"  민감도  : {sens:.1%}  TP={tp}  FN={fn}")
    print(f"  특이도  : {spec:.1%}  TN={tn}  FP={fp}")
    print(f"  AUC     : {roc_auc:.4f}")
    print(f"  F1      : {f1:.4f}")
    print(classification_report(labels, preds, target_names=CLASSES, zero_division=0))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    cm = confusion_matrix(labels, preds)
    ConfusionMatrixDisplay(cm, display_labels=CLASSES).plot(
        ax=axes[0], cmap="Blues", colorbar=False)
    axes[0].set_title(f"Confusion Matrix — {tag}")
    axes[1].plot(fpr, tpr, color="steelblue", lw=2, label=f"AUC={roc_auc:.4f}")
    axes[1].plot([0,1],[0,1], "k--", lw=1)
    axes[1].set(xlabel="1-Specificity (FPR)", ylabel="Sensitivity (TPR)",
                title=f"ROC — {tag}")
    axes[1].legend(loc="lower right")
    plt.tight_layout()
    out = out_dir / f"ensemble_final_{tag}.png"
    plt.savefig(out, dpi=150); plt.close()
    print(f"  저장: {out}")

    return acc, sens, spec, roc_auc, f1


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",  default="dataset")
    parser.add_argument("--yolo",     default="runs/yolov8m-cls/weights/best.pt")
    parser.add_argument("--dn-ckpt",  default="runs/alt_densenet121/weights/best.pth",
                        help="DenseNet 체크포인트")
    parser.add_argument("--ef-ckpt",  default="runs/alt_efficientnet_b3/weights/best.pth",
                        help="EfficientNet 체크포인트")
    parser.add_argument("--w-yolo",   type=float, default=2.0)
    parser.add_argument("--w-dn",     type=float, default=1.0)
    parser.add_argument("--w-ef",     type=float, default=2.0)
    parser.add_argument("--no-yolo",  action="store_true")
    parser.add_argument("--no-old",   action="store_true",
                        help="DenseNet 제외")
    parser.add_argument("--no-ef",    action="store_true")
    parser.add_argument("--no-tta",   action="store_true")
    parser.add_argument("--target-sens", type=float, default=0.98,
                        help="임계값 최적화 목표 민감도 (기본 0.98)")
    parser.add_argument("--out-dir",  default="runs/ensemble_final_v2")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    device  = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"\n{'='*60}")
    print(f"최종 앙상블 평가  |  Dataset: {args.dataset}")
    print(f"Device: {device}")
    print(f"{'='*60}")

    root = Path(args.dataset)
    val_s  = collect(root / "val")
    test_s = collect(root / "test")
    val_labels  = [l for _, l in val_s]
    test_labels = [l for _, l in test_s]
    print(f"\nVal  : {len(val_s)}장  "
          f"(골절={sum(l==0 for _,l in val_s)}, "
          f"정상={sum(l==1 for _,l in val_s)})")
    print(f"Test : {len(test_s)}장  "
          f"(골절={sum(l==0 for _,l in test_s)}, "
          f"정상={sum(l==1 for _,l in test_s)})")

    val_probs_list  = []
    test_probs_list = []
    weights         = []
    tta = not args.no_tta

    # ── YOLOv8m ──────────────────────────────────────────────────────────────
    if not args.no_yolo:
        yp = Path(args.yolo)
        if yp.exists():
            print(f"\n[YOLO] 추론 중 (augment TTA)  ← {yp.name}")
            yolo = YOLO(str(yp))
            val_probs_list.append(infer_yolo(yolo, val_s))
            test_probs_list.append(infer_yolo(yolo, test_s))
            weights.append(args.w_yolo)
            del yolo; torch.cuda.empty_cache()
        else:
            print(f"[YOLO] 없음 — 건너뜀")

    # ── DenseNet ─────────────────────────────────────────────────────────────
    if not args.no_old:
        dnp = Path(args.dn_ckpt)
        if dnp.exists():
            print(f"\n[DenseNet] TTA×{len(TTA_CONFIGS) if tta else 1}  ← {dnp.name}")
            dn, isz = load_timm_model(dnp, device)
            val_probs_list.append(infer_timm(dn, val_s,  isz, device, tta))
            test_probs_list.append(infer_timm(dn, test_s, isz, device, tta))
            weights.append(args.w_dn)
            del dn; torch.cuda.empty_cache()
        else:
            print(f"[DenseNet] 없음 — 건너뜀")

    # ── EfficientNet ─────────────────────────────────────────────────────────
    if not args.no_ef:
        efp = Path(args.ef_ckpt)
        if efp.exists():
            print(f"\n[EfficientNet] TTA×{len(TTA_CONFIGS) if tta else 1}  ← {efp.name}")
            ef, isz = load_timm_model(efp, device)
            val_probs_list.append(infer_timm(ef, val_s,  isz, device, tta))
            test_probs_list.append(infer_timm(ef, test_s, isz, device, tta))
            weights.append(args.w_ef)
            del ef; torch.cuda.empty_cache()
        else:
            print(f"[EfficientNet] 없음 — 건너뜀")

    if not val_probs_list:
        raise SystemExit("사용 가능한 모델이 없습니다.")

    # ── 모델별 AUC 진단 ──────────────────────────────────────────────────────
    names = (["YOLO"]    if not args.no_yolo else []) + \
            (["DenseNet"] if not args.no_old  else []) + \
            (["EfficientNet"] if not args.no_ef else [])
    frac_val = np.array(val_labels) == FRACTURE_IDX
    print("\n[모델별 Val AUC]")
    for name, p in zip(names, val_probs_list):
        from sklearn.metrics import roc_auc_score
        ma = roc_auc_score(frac_val.astype(int), p)
        print(f"  {name:15s}: AUC={ma:.4f}  "
              f"골절평균={p[frac_val].mean():.3f}  "
              f"정상평균={p[~frac_val].mean():.3f}")

    # ── 앙상블 합산 ──────────────────────────────────────────────────────────
    w = np.array(weights) / sum(weights)
    print(f"\n앙상블 가중치: {dict(zip(names, w.round(3)))}")
    val_combined  = sum(wi * p for wi, p in zip(w, val_probs_list))
    test_combined = sum(wi * p for wi, p in zip(w, test_probs_list))

    # ── 임계값 최적화 (val 세트) ─────────────────────────────────────────────
    best_thr, method = find_threshold(
        val_combined, np.array(val_labels), target_sens=args.target_sens)
    print(f"\n최적 임계값: {best_thr:.3f}  ({method})")

    # ── 평가 ─────────────────────────────────────────────────────────────────
    va  = evaluate_and_plot(val_combined,  np.array(val_labels),  best_thr, out_dir, "val")
    te  = evaluate_and_plot(test_combined, np.array(test_labels), best_thr, out_dir, "test")

    # 목표 달성 체크
    targets = {"민감도≥98%": te[1]>=0.98, "특이도≥85%": te[2]>=0.85,
               "AUC≥0.98":  te[3]>=0.98, "F1≥0.92":   te[4]>=0.92}
    print(f"\n{'='*60}")
    print("목표 달성 현황 (Test 기준)")
    for name, ok in targets.items():
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"{'='*60}")

    # JSON 저장
    result = {
        "threshold": float(best_thr),
        "threshold_method": method,
        "ensemble_weights": dict(zip(names, w.round(4).tolist())),
        "val":  {"acc": va[0], "sens": va[1], "spec": va[2], "auc": va[3], "f1": va[4]},
        "test": {"acc": te[0], "sens": te[1], "spec": te[2], "auc": te[3], "f1": te[4]},
    }
    with open(out_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n결과 저장: {out_dir}")


if __name__ == "__main__":
    main()
