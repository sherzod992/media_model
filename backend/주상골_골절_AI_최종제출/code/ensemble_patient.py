"""
ensemble_patient.py — 환자-측면(patient-side) 단위 집계 앙상블

핵심 개선:
  이미지 단위 평가 대신 (환자ID, 손방향) 단위로 집계:
  - 같은 환자·같은 방향의 여러 장 중 MAX 확률을 케이스 확률로 사용
  - 효과: oblique2/lateral 등 특정 뷰에서 낮은 점수라도 AP/oblique에서
          높으면 올바르게 골절로 분류됨

Usage:
  python ensemble_patient.py
  python ensemble_patient.py --dn-ckpt runs/alt_densenet121/weights/best.pth
"""
import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF","expandable_segments:True,max_split_size_mb:256")
import argparse, json, re, warnings
import numpy as np
import torch
import torch.nn as nn
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
from torchvision import transforms
import timm
from ultralytics import YOLO
from sklearn.metrics import roc_auc_score, roc_curve, auc, classification_report, confusion_matrix, ConfusionMatrixDisplay
warnings.filterwarnings("ignore")

torch.backends.cudnn.benchmark = False
CLASSES = ["fracture","normal"]; FRACTURE_IDX = 0
MEAN=[0.485,0.456,0.406]; STD=[0.229,0.224,0.225]
TTA_CONFIGS=[
    (False,  0),(True,   0),(False, 10),(True,  10),
    (False,-10),(True, -10),(False, 20),(True, -20),
]


def collect(d):
    s=[]
    for ci,cls in enumerate(CLASSES):
        for p in sorted(Path(d,cls).glob("*.jpg")): s.append((p,ci))
    return s


def extract_case_key(filepath: Path) -> str:
    """
    파일명에서 (환자ID, 손방향) 키 추출.
    파일명 패턴: {폴더명}_{원본파일명}.jpg
    원본파일명에서 첫 8자리 숫자(환자ID) + Lt/Rt(방향) 추출.
    """
    stem = filepath.stem
    # 환자ID: 처음 8자리 숫자
    m_id = re.search(r'\b(\d{8})\b', stem)
    patient_id = m_id.group(1) if m_id else stem[:8]
    # 방향: Lt 또는 Rt (파일명 후반부에서 마지막 Lt/Rt)
    sides = re.findall(r'\b(Lt|Rt)\b', stem)
    side = sides[-1] if sides else "?"
    return f"{patient_id}_{side}"


def load_timm(ckpt, dev):
    info = json.load(open(Path(ckpt).parent/"model_info.json"))
    m = timm.create_model(info["timm_name"], pretrained=False, num_classes=2,
                          drop_rate=info.get("drop_rate",0.2)).to(dev)
    m.load_state_dict(torch.load(ckpt, map_location=dev, weights_only=True))
    m.eval(); return m, int(info["imgsz"])


@torch.no_grad()
def infer_timm(model, samples, isz, dev, tta=True):
    cfgs = TTA_CONFIGS if tta else [TTA_CONFIGS[0]]
    acc = np.zeros(len(samples))
    for hflip, angle in cfgs:
        ops = [transforms.Resize((isz,isz))]
        if hflip: ops.append(transforms.RandomHorizontalFlip(1.0))
        if angle: ops.append(transforms.RandomRotation((angle,angle)))
        ops += [transforms.ToTensor(), transforms.Normalize(MEAN,STD)]
        tfm = transforms.Compose(ops)
        for i,(path,_) in enumerate(samples):
            img = tfm(Image.open(path).convert("RGB")).unsqueeze(0).to(dev)
            acc[i] += torch.softmax(model(img),1)[0,FRACTURE_IDX].item()
        torch.cuda.empty_cache()
    return acc / len(cfgs)


def aggregate_to_cases(samples, probs):
    """이미지 단위 확률을 환자-측면 단위 MAX로 집계."""
    from collections import defaultdict
    case_probs = defaultdict(list)
    case_labels = {}
    for (path, label), p in zip(samples, probs):
        key = extract_case_key(path)
        case_probs[key].append(p)
        if key in case_labels:
            assert case_labels[key] == label, f"동일 케이스 레이블 불일치: {key}"
        case_labels[key] = label
    keys = sorted(case_probs.keys())
    agg_probs  = np.array([max(case_probs[k]) for k in keys])
    agg_labels = np.array([case_labels[k]     for k in keys])
    return keys, agg_probs, agg_labels


def find_threshold(probs, labels, target_sens=0.98):
    frac = labels == FRACTURE_IDX
    candidates = []
    for thr in np.arange(0.01, 0.99, 0.002):
        pred = probs >= thr
        tp=np.sum(pred&frac); fn=np.sum(~pred&frac)
        tn=np.sum(~pred&~frac); fp=np.sum(pred&~frac)
        sens=tp/(tp+fn) if tp+fn>0 else 0
        spec=tn/(tn+fp) if tn+fp>0 else 0
        candidates.append((thr,sens,spec,sens+spec-1))
    primary=[(t,s,sp,j) for t,s,sp,j in candidates if s>=target_sens]
    if primary:
        best=max(primary,key=lambda x:x[2])
        return best[0], f"sens≥{target_sens:.0%} 중 spec최대"
    best=max(candidates,key=lambda x:x[3])
    return best[0], "Youden-J"


def evaluate(probs, labels, thr, tag, out_dir=None):
    pred_frac = probs >= thr
    frac = labels == FRACTURE_IDX
    tp=int(np.sum(pred_frac&frac)); fn=int(np.sum(~pred_frac&frac))
    fp=int(np.sum(pred_frac&~frac)); tn=int(np.sum(~pred_frac&~frac))
    sens=tp/(tp+fn) if tp+fn>0 else 0
    spec=tn/(tn+fp) if tn+fp>0 else 0
    acc=(tp+tn)/len(labels)
    prec=tp/(tp+fp) if tp+fp>0 else 0
    f1=2*prec*sens/(prec+sens) if prec+sens>0 else 0
    fpr,tpr,_=roc_curve((labels==FRACTURE_IDX).astype(int),probs)
    roc_auc=auc(fpr,tpr)
    preds=(~pred_frac).astype(int)
    print(f"\n{'='*60}")
    print(f"[{tag.upper()}]  임계값={thr:.3f}  케이스수={len(labels)}")
    print(f"  정확도: {acc:.1%}   민감도: {sens:.1%} (TP={tp} FN={fn})")
    print(f"  특이도: {spec:.1%}   AUC: {roc_auc:.4f}   F1: {f1:.4f}")
    print(f"  TN={tn} FP={fp}")
    print(classification_report(labels, preds, target_names=CLASSES, zero_division=0))
    if out_dir:
        fig,axes=plt.subplots(1,2,figsize=(12,5))
        cm=confusion_matrix(labels,preds)
        ConfusionMatrixDisplay(cm,display_labels=CLASSES).plot(ax=axes[0],cmap="Blues",colorbar=False)
        axes[0].set_title(f"Confusion Matrix — {tag}")
        axes[1].plot(fpr,tpr,color="steelblue",lw=2,label=f"AUC={roc_auc:.4f}")
        axes[1].plot([0,1],[0,1],"k--",lw=1)
        axes[1].set(xlabel="1-Specificity",ylabel="Sensitivity",title=f"ROC — {tag}")
        axes[1].legend(loc="lower right")
        plt.tight_layout()
        out=Path(out_dir)/f"patient_{tag}.png"
        plt.savefig(out,dpi=150); plt.close()
    return sens, spec, roc_auc, f1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",    default="dataset")
    parser.add_argument("--yolo",       default="runs/yolov8m-cls/weights/best.pt")
    parser.add_argument("--dn-ckpt",    default="runs/alt_densenet121/weights/best.pth")
    parser.add_argument("--ef-ckpt",    default="runs/alt_efficientnet_b3/weights/best.pth")
    parser.add_argument("--w-yolo",     type=float, default=2.0)
    parser.add_argument("--w-dn",       type=float, default=1.0)
    parser.add_argument("--w-ef",       type=float, default=2.0)
    parser.add_argument("--no-yolo",    action="store_true")
    parser.add_argument("--no-dn",      action="store_true")
    parser.add_argument("--no-tta",     action="store_true")
    parser.add_argument("--target-sens",type=float, default=0.98)
    parser.add_argument("--out-dir",    default="runs/patient_ensemble")
    args = parser.parse_args()

    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tta = not args.no_tta
    root = Path(args.dataset)

    val_s  = collect(root/"val")
    test_s = collect(root/"test")
    print(f"\n이미지 단위:  Val={len(val_s)}  Test={len(test_s)}")

    # ── 추론 ──────────────────────────────────────────────────────────────
    val_pl=[]; test_pl=[]; weights=[]; names=[]

    if not args.no_yolo and Path(args.yolo).exists():
        print("[YOLO] 추론 중...")
        yolo=YOLO(str(args.yolo))
        vpy=np.array([r.probs.data.cpu().numpy()[0] for r in yolo.predict([str(p) for p,_ in val_s],imgsz=640,verbose=False)])
        tpy=np.array([r.probs.data.cpu().numpy()[0] for r in yolo.predict([str(p) for p,_ in test_s],imgsz=640,verbose=False)])
        del yolo; torch.cuda.empty_cache()
        val_pl.append(vpy); test_pl.append(tpy); weights.append(args.w_yolo); names.append("YOLO")

    if not args.no_dn and Path(args.dn_ckpt).exists():
        print("[DenseNet] 추론 중...")
        dn,isz=load_timm(args.dn_ckpt,device)
        val_pl.append(infer_timm(dn,val_s,isz,device,tta))
        test_pl.append(infer_timm(dn,test_s,isz,device,tta))
        del dn; torch.cuda.empty_cache()
        weights.append(args.w_dn); names.append("DenseNet")

    if Path(args.ef_ckpt).exists():
        print("[EfficientNet] 추론 중...")
        ef,isz=load_timm(args.ef_ckpt,device)
        val_pl.append(infer_timm(ef,val_s,isz,device,tta))
        test_pl.append(infer_timm(ef,test_s,isz,device,tta))
        del ef; torch.cuda.empty_cache()
        weights.append(args.w_ef); names.append("EfficientNet")

    w = np.array(weights)/sum(weights)
    print(f"\n가중치: {dict(zip(names,w.round(3)))}")

    val_combined  = sum(wi*p for wi,p in zip(w,val_pl))
    test_combined = sum(wi*p for wi,p in zip(w,test_pl))

    # ── 모델별 Val AUC ─────────────────────────────────────────────────
    frac_v = np.array([l for _,l in val_s]) == FRACTURE_IDX
    print("\n[모델별 Val AUC (이미지 단위)]")
    for name,p in zip(names,val_pl):
        ma=roc_auc_score(frac_v.astype(int),p)
        print(f"  {name:15s}: AUC={ma:.4f}  골절평균={p[frac_v].mean():.3f}  정상평균={p[~frac_v].mean():.3f}")

    # ── 환자-측면 단위 집계 ───────────────────────────────────────────
    val_keys,  val_agg,  val_agg_lbl  = aggregate_to_cases(val_s,  val_combined)
    test_keys, test_agg, test_agg_lbl = aggregate_to_cases(test_s, test_combined)
    print(f"\n환자-측면 케이스 단위: Val={len(val_agg)}  Test={len(test_agg)}")
    frac_cnt_v  = int(np.sum(val_agg_lbl==FRACTURE_IDX))
    frac_cnt_t  = int(np.sum(test_agg_lbl==FRACTURE_IDX))
    print(f"  Val  골절={frac_cnt_v}  정상={len(val_agg)-frac_cnt_v}")
    print(f"  Test 골절={frac_cnt_t}  정상={len(test_agg)-frac_cnt_t}")

    # ── 케이스 점수 출력 ─────────────────────────────────────────────
    print("\n[Test 케이스 확률 (오름차순 — 골절)]")
    frac_t = test_agg_lbl == FRACTURE_IDX
    frac_keys = [(k,p) for k,p,l in zip(test_keys,test_agg,test_agg_lbl) if l==FRACTURE_IDX]
    for k,p in sorted(frac_keys,key=lambda x:x[1])[:8]:
        print(f"  {k:25s}: {p:.4f}")
    print("[Test 케이스 확률 (내림차순 — 정상)]")
    norm_keys = [(k,p) for k,p,l in zip(test_keys,test_agg,test_agg_lbl) if l==FRACTURE_IDX+1]
    for k,p in sorted(norm_keys,key=lambda x:-x[1])[:8]:
        print(f"  {k:25s}: {p:.4f}")

    # ── 임계값 최적화 (val 케이스 기준) ─────────────────────────────
    best_thr, method = find_threshold(val_agg, val_agg_lbl, target_sens=args.target_sens)
    print(f"\n최적 임계값: {best_thr:.3f}  ({method})")

    # ── 평가 ─────────────────────────────────────────────────────────
    print("\n=== Val 케이스 단위 평가 ===")
    vs,vsp,va,vf1 = evaluate(val_agg,  val_agg_lbl,  best_thr, "val",  out_dir)
    print("\n=== Test 케이스 단위 평가 ===")
    ts,tsp,ta,tf1 = evaluate(test_agg, test_agg_lbl, best_thr, "test", out_dir)

    # 목표 달성
    targets={"민감도≥98%":ts>=0.98,"특이도≥85%":tsp>=0.85,"AUC≥0.98":ta>=0.98,"F1≥0.92":tf1>=0.92}
    print(f"\n{'='*60}")
    print("목표 달성 현황 (Test 케이스 기준)")
    for name,ok in targets.items():
        print(f"  {'O' if ok else 'x'} {name}")
    print(f"{'='*60}")

    result={
        "threshold":float(best_thr),"method":method,
        "image_level":{"val_n":len(val_s),"test_n":len(test_s)},
        "case_level":{
            "val_n":len(val_agg),"test_n":len(test_agg),
            "val":{"sens":vs,"spec":vsp,"auc":va,"f1":vf1},
            "test":{"sens":ts,"spec":tsp,"auc":ta,"f1":tf1},
        }
    }
    with open(out_dir/"results.json","w",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
    print(f"\n결과: {out_dir}")


if __name__=="__main__":
    main()
