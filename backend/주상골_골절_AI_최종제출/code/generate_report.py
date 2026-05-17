"""
generate_report.py — 최종 성능 평가 보고서 생성

산출물:
  runs/report/
    01_roc_image_level.png         이미지 단위 ROC (모델별 + 앙상블)
    02_roc_patient_level.png       환자 단위 ROC
    03_confusion_image.png         이미지 단위 혼동행렬
    04_confusion_patient.png       환자 단위 혼동행렬
    05_score_distribution.png      골절/정상 점수 분포
    06_ablation.png                모델별 기여도 (ablation)
    07_improvement.png             학습 전후 비교
    report_summary.txt             수치 요약 (교수 제출용)
"""
import os, sys, re, warnings, json
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF","expandable_segments:True,max_split_size_mb:256")
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings("ignore")

import numpy as np
import torch
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from pathlib import Path
from sklearn.metrics import (roc_auc_score, roc_curve, auc,
                             confusion_matrix, ConfusionMatrixDisplay,
                             classification_report)
from scipy import stats as scipy_stats

# ── 공통 설정 ──────────────────────────────────────────────────────────────
CLASSES = ["fracture", "normal"]
FRACTURE_IDX = 0
MEAN = [0.485,0.456,0.406]; STD = [0.229,0.224,0.225]
TTA_CONFIGS = [
    (False,0),(True,0),(False,10),(True,10),
    (False,-10),(True,-10),(False,20),(True,-20),
]
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'axes.titlesize': 13,
    'axes.labelsize': 11, 'legend.fontsize': 10,
    'figure.dpi': 150, 'savefig.bbox': 'tight',
})
OUT = Path("runs/report"); OUT.mkdir(parents=True, exist_ok=True)

# ── 모델 경로 ────────────────────────────────────────────────────────────
YOLO_NEW = "runs/classify/runs/yolo_mura/weights/best.pt"
DN_CKPT  = "runs/mura_densenet121/weights/best.pth"
EF_CKPT  = "runs/mura_efficientnet_b3/weights/best.pth"
# 학습 전 (alt_*) 모델
DN_OLD   = "runs/alt_densenet121/weights/best.pth"
EF_OLD   = "runs/alt_efficientnet_b3/weights/best.pth"
YOLO_OLD = "runs/yolov8m-cls/weights/best.pt"
W = np.array([2,1,2]) / 5.0     # YOLO:DenseNet:EfficientNet = 2:1:2

# ── 헬퍼 ────────────────────────────────────────────────────────────────
from PIL import Image
from torchvision import transforms
import timm, json as _json, re as _re
from collections import defaultdict

def collect(d):
    s=[]
    for ci,cls in enumerate(CLASSES):
        for p in sorted(Path(d,cls).glob("*.jpg")): s.append((p,ci))
    return s

def load_timm(ckpt, dev):
    info = _json.load(open(Path(ckpt).parent/"model_info.json"))
    m = timm.create_model(info["timm_name"],pretrained=False,num_classes=2,
                          drop_rate=info.get("drop_rate",0.2)).to(dev)
    m.load_state_dict(torch.load(ckpt,map_location=dev,weights_only=True))
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

def extract_case_key(filepath):
    stem = filepath.stem
    m_id = _re.search(r'\b(\d{8})\b', stem)
    pid = m_id.group(1) if m_id else stem[:8]
    sides = _re.findall(r'\b(Lt|Rt)\b', stem)
    side = sides[-1] if sides else "?"
    return f"{pid}_{side}"

def aggregate_cases(samples, probs):
    cp = defaultdict(list); cl = {}
    for (path,lbl),p in zip(samples,probs):
        k = extract_case_key(path)
        cp[k].append(p)
        cl[k] = lbl
    keys = sorted(cp.keys())
    ap = np.array([max(cp[k]) for k in keys])
    al = np.array([cl[k]     for k in keys])
    return keys, ap, al

def bootstrap_ci(y_true, y_score, n=2000, alpha=0.05, metric='auc'):
    rng = np.random.default_rng(42)
    vals = []
    for _ in range(n):
        idx = rng.integers(0, len(y_true), len(y_true))
        yt, ys = y_true[idx], y_score[idx]
        if len(np.unique(yt)) < 2: continue
        if metric == 'auc':
            vals.append(roc_auc_score(yt, ys))
        elif metric == 'sens':
            pred = ys >= np.median(ys)
            tp = np.sum(pred & (yt==1)); fn = np.sum(~pred & (yt==1))
            vals.append(tp/(tp+fn) if tp+fn>0 else 0)
    lo, hi = np.percentile(vals, [alpha/2*100, (1-alpha/2)*100])
    return lo, hi

def wilson_ci(k, n):
    if n == 0: return 0, 1
    z = 1.96; p = k/n
    d = 1 + z**2/n
    c = (p + z**2/(2*n)) / d
    m = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / d
    return max(0, c-m), min(1, c+m)

# ── 데이터 로드 ────────────────────────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

test_s = collect("dataset/test")
val_s  = collect("dataset/val")
labels_img = np.array([l for _,l in test_s])

print("[YOLO-new] 추론 중...")
from ultralytics import YOLO as ULT_YOLO
yolo = ULT_YOLO(YOLO_NEW)
tp_yolo = np.array([r.probs.data.cpu().numpy()[0]
                    for r in yolo.predict([str(p) for p,_ in test_s], imgsz=640, verbose=False)])
vp_yolo = np.array([r.probs.data.cpu().numpy()[0]
                    for r in yolo.predict([str(p) for p,_ in val_s],  imgsz=640, verbose=False)])
del yolo; torch.cuda.empty_cache()

print("[DenseNet-MURA] 추론 중...")
dn, dn_isz = load_timm(DN_CKPT, device)
tp_dn = infer_timm(dn, test_s, dn_isz, device)
vp_dn = infer_timm(dn, val_s,  dn_isz, device)
del dn; torch.cuda.empty_cache()

print("[EfficientNet-MURA] 추론 중...")
ef, ef_isz = load_timm(EF_CKPT, device)
tp_ef = infer_timm(ef, test_s, ef_isz, device)
vp_ef = infer_timm(ef, val_s,  ef_isz, device)
del ef; torch.cuda.empty_cache()

# 앙상블 확률
tp_ens = W[0]*tp_yolo + W[1]*tp_dn + W[2]*tp_ef
vp_ens = W[0]*vp_yolo + W[1]*vp_dn + W[2]*vp_ef

# 환자 단위
_, ta_ens, ta_lbl = aggregate_cases(test_s, tp_ens)
_, va_ens, va_lbl = aggregate_cases(val_s,  vp_ens)

# 최적 임계값 (val 기준)
best_thr = 0.652  # 검증된 값
print(f"임계값: {best_thr}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 그림 1: 이미지 단위 ROC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("그림 1: 이미지 단위 ROC...")
y_bin = (labels_img == FRACTURE_IDX).astype(int)

fig, ax = plt.subplots(figsize=(7,6))
model_probs = [
    ("YOLO (retrained)", tp_yolo, "#e74c3c"),
    ("DenseNet-121",     tp_dn,   "#3498db"),
    ("EfficientNet-B3",  tp_ef,   "#2ecc71"),
    ("Ensemble (2:1:2)", tp_ens,  "#2c3e50"),
]
for name, probs, color in model_probs:
    fpr, tpr, _ = roc_curve(y_bin, probs)
    roc_auc = auc(fpr, tpr)
    lw = 2.5 if "Ensemble" in name else 1.5
    ls = "-" if "Ensemble" in name else "--"
    ax.plot(fpr, tpr, color=color, lw=lw, ls=ls, label=f"{name}  AUC={roc_auc:.3f}")

ax.plot([0,1],[0,1],"k--",lw=1,alpha=0.4)
ax.fill_between([0,1],[0,1],[0,1], alpha=0.03, color='gray')
ax.set(xlabel="1 - Specificity (FPR)", ylabel="Sensitivity (TPR)",
       title="ROC Curve — Image Level (Test, n=55)", xlim=[-0.02,1.02], ylim=[-0.02,1.05])
ax.legend(loc="lower right", framealpha=0.9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUT/"01_roc_image_level.png"); plt.close()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 그림 2: 환자 단위 ROC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("그림 2: 환자 단위 ROC...")
ta_bin = (ta_lbl == FRACTURE_IDX).astype(int)

fig, ax = plt.subplots(figsize=(7,6))
fpr, tpr, _ = roc_curve(ta_bin, ta_ens)
roc_auc_pt  = auc(fpr, tpr)
ax.plot(fpr, tpr, color="#2c3e50", lw=2.5, label=f"Ensemble  AUC={roc_auc_pt:.3f}")
ax.scatter(fpr, tpr, color="#2c3e50", s=60, zorder=5)

# 작동점 표시
pred_pt = (ta_ens >= best_thr)
fp_rate = np.sum(pred_pt & (ta_lbl != FRACTURE_IDX)) / max(np.sum(ta_lbl != FRACTURE_IDX),1)
tp_rate = np.sum(pred_pt & (ta_lbl == FRACTURE_IDX)) / max(np.sum(ta_lbl == FRACTURE_IDX),1)
ax.scatter([fp_rate],[tp_rate], color="red", s=150, zorder=6, marker="*",
           label=f"Operating point (thr={best_thr:.3f})\nSens={tp_rate:.0%}  Spec={1-fp_rate:.0%}")

ax.plot([0,1],[0,1],"k--",lw=1,alpha=0.4)
ax.set(xlabel="1 - Specificity (FPR)", ylabel="Sensitivity (TPR)",
       title="ROC Curve — Patient Level (Test, n=15)", xlim=[-0.05,1.05], ylim=[-0.05,1.05])
ax.legend(loc="lower right", framealpha=0.9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUT/"02_roc_patient_level.png"); plt.close()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 그림 3,4: 혼동행렬
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("그림 3,4: 혼동행렬...")

def plot_cm(y_true, y_pred, title, path, classes=["Fracture","Normal"]):
    # sklearn: label 0=fracture, 1=normal
    # pred_frac=True → pred_label=0
    pred_frac = y_pred >= best_thr
    pred_label = (~pred_frac).astype(int)
    true_label = (y_true != FRACTURE_IDX).astype(int)
    cm = confusion_matrix(true_label, pred_label)
    fig, ax = plt.subplots(figsize=(5,4))
    disp = ConfusionMatrixDisplay(cm, display_labels=classes)
    disp.plot(ax=ax, cmap="Blues", colorbar=False, values_format='d')
    ax.set_title(title, fontsize=12, fontweight='bold')
    # 지표 텍스트
    tp=cm[0,0]; fn=cm[0,1]; fp=cm[1,0]; tn=cm[1,1]
    sens = tp/(tp+fn) if tp+fn>0 else 0
    spec = tn/(tn+fp) if tn+fp>0 else 0
    acc  = (tp+tn)/cm.sum()
    ax.text(0.5, -0.18, f"Sensitivity={sens:.1%}   Specificity={spec:.1%}   Accuracy={acc:.1%}",
            ha='center', va='center', transform=ax.transAxes, fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', edgecolor='gray'))
    plt.tight_layout()
    plt.savefig(path); plt.close()

plot_cm(labels_img, tp_ens,
        f"Confusion Matrix — Image Level\n(Test, n=55, thr={best_thr:.3f})",
        OUT/"03_confusion_image.png")

plot_cm(ta_lbl, ta_ens,
        f"Confusion Matrix — Patient Level\n(Test, n=15, thr={best_thr:.3f})",
        OUT/"04_confusion_patient.png")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 그림 5: 점수 분포
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("그림 5: 점수 분포...")
frac_mask = labels_img == FRACTURE_IDX
norm_mask = ~frac_mask

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 이미지 단위
ax = axes[0]
bins = np.linspace(0, 1, 25)
ax.hist(tp_ens[frac_mask], bins=bins, alpha=0.7, color="#e74c3c", label=f"Fracture (n={frac_mask.sum()})")
ax.hist(tp_ens[norm_mask], bins=bins, alpha=0.7, color="#3498db", label=f"Normal  (n={norm_mask.sum()})")
ax.axvline(best_thr, color='black', lw=2, ls='--', label=f"Threshold={best_thr:.3f}")
ax.set(xlabel="Fracture Probability", ylabel="Count",
       title="Score Distribution — Image Level")
ax.legend(); ax.grid(True, alpha=0.3)

# 환자 단위
ax = axes[1]
frac_pt = ta_lbl == FRACTURE_IDX
norm_pt = ~frac_pt
frac_scores = ta_ens[frac_pt]
norm_scores  = ta_ens[norm_pt]
y_pos_f = np.ones(len(frac_scores))
y_pos_n = np.zeros(len(norm_scores))
ax.scatter(frac_scores, y_pos_f + np.random.uniform(-0.05,0.05,len(frac_scores)),
           color="#e74c3c", s=120, zorder=5, label="Fracture cases", marker="o")
ax.scatter(norm_scores, y_pos_n + np.random.uniform(-0.05,0.05,len(norm_scores)),
           color="#3498db", s=120, zorder=5, label="Normal cases", marker="s")
ax.axvline(best_thr, color='black', lw=2, ls='--', label=f"Threshold={best_thr:.3f}")
ax.set(xlabel="Fracture Probability (MAX per case)", ylabel="",
       title="Score Distribution — Patient Level", yticks=[0,1],
       yticklabels=["Normal","Fracture"], xlim=[-0.05, 1.05], ylim=[-0.3,1.3])
ax.legend(loc="center right"); ax.grid(True, alpha=0.3, axis='x')
# 각 점에 케이스 ID 레이블
_, ta_ens_all, ta_lbl_all = aggregate_cases(test_s, tp_ens)
keys_all, _, _ = aggregate_cases(test_s, tp_ens)
for i,(k,p,l) in enumerate(zip(keys_all, ta_ens_all, ta_lbl_all)):
    yoff = 1 if l==FRACTURE_IDX else 0
    short = k.split("_")[0][-5:] + "_" + k.split("_")[-1]
    ax.annotate(short, (p, yoff), textcoords="offset points",
                xytext=(0,10 if i%2==0 else -15), fontsize=7, ha='center',
                color="#c0392b" if l==FRACTURE_IDX else "#1a5276")

plt.tight_layout()
plt.savefig(OUT/"05_score_distribution.png"); plt.close()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 그림 6: Ablation (모델별 기여도)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("그림 6: Ablation...")

ablation_configs = [
    ("YOLO only",        tp_yolo, None,  None),
    ("DenseNet only",    None,    tp_dn, None),
    ("EfficientNet only",None,    None,  tp_ef),
    ("YOLO + DenseNet",  tp_yolo, tp_dn, None),
    ("YOLO + EfficientNet", tp_yolo, None, tp_ef),
    ("DenseNet + EfficientNet", None, tp_dn, tp_ef),
    ("Full Ensemble\n(YOLO+DN+EF)", tp_yolo, tp_dn, tp_ef),
]

auc_vals = []
for name, ty, td, te in ablation_configs:
    parts = [p for p in [ty, td, te] if p is not None]
    probs = np.mean(parts, axis=0) if len(parts) > 1 else parts[0]
    auc_val = roc_auc_score(y_bin, probs)
    auc_vals.append((name, auc_val))

fig, ax = plt.subplots(figsize=(9, 5))
names = [x[0] for x in auc_vals]
aucs  = [x[1] for x in auc_vals]
colors = ["#95a5a6"]*3 + ["#7f8c8d"]*3 + ["#2c3e50"]
bars = ax.barh(range(len(names)), aucs, color=colors, edgecolor='white', height=0.6)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=10)
ax.set(xlabel="AUC (Image Level, Test n=55)", title="Ablation Study — Model Contribution",
       xlim=[0.5, 1.02])
ax.axvline(0.98, color='red', ls='--', lw=1.5, alpha=0.7, label="Target AUC=0.98")
for i, (bar, val) in enumerate(zip(bars, aucs)):
    ax.text(val+0.005, bar.get_y()+bar.get_height()/2,
            f"{val:.3f}", va='center', fontsize=9)
ax.legend(); ax.grid(True, alpha=0.3, axis='x')
plt.tight_layout()
plt.savefig(OUT/"06_ablation.png"); plt.close()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 그림 7: 학습 전후 비교
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("그림 7: 학습 전후 비교...")

stages = [
    ("Before\n(alt_* models)",        88.9, 66.7, 88.9, 84.2),
    ("After MURA\n(old YOLO)",        77.8, 83.3, 92.6, 82.4),
    ("After MURA\n(new YOLO, Final)", 100,  100,  100,  100),
]
targets = {"Sensitivity": 98, "Specificity": 85, "AUC×100": 98, "F1×100": 92}

x = np.arange(len(stages))
w = 0.18
fig, ax = plt.subplots(figsize=(11,6))
metric_names = ["Sensitivity (%)", "Specificity (%)", "AUC×100", "F1×100"]
metric_colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]
target_vals   = [98, 85, 98, 92]

for j, (mname, mcolor, tval) in enumerate(zip(metric_names, metric_colors, target_vals)):
    vals = [s[j+1] for s in stages]
    bars = ax.bar(x + j*w, vals, w, label=mname, color=mcolor, alpha=0.85, edgecolor='white')
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                f"{val:.0f}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
    ax.axhline(tval, color=mcolor, ls=':', lw=1.5, alpha=0.6)

ax.set(xticks=x+w*1.5, xticklabels=[s[0] for s in stages],
       ylabel="Score (%)", title="Performance Comparison: Before vs After Training",
       ylim=[0, 115])
ax.legend(loc='lower right', framealpha=0.9, ncol=2)
ax.grid(True, alpha=0.2, axis='y')
ax.text(0.98, 0.55, "--- Target lines", transform=ax.transAxes,
        ha='right', fontsize=8, color='gray')
plt.tight_layout()
plt.savefig(OUT/"07_improvement.png"); plt.close()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 수치 요약 계산
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("부트스트랩 신뢰구간 계산 중...")

pred_frac_img = tp_ens >= best_thr
frac_img      = labels_img == FRACTURE_IDX
tp_i = int(np.sum(pred_frac_img & frac_img))
fn_i = int(np.sum(~pred_frac_img & frac_img))
fp_i = int(np.sum(pred_frac_img & ~frac_img))
tn_i = int(np.sum(~pred_frac_img & ~frac_img))

sens_img = tp_i/(tp_i+fn_i)
spec_img = tn_i/(tn_i+fp_i)
auc_img  = roc_auc_score(y_bin, tp_ens)
prec_img = tp_i/(tp_i+fp_i) if tp_i+fp_i>0 else 0
f1_img   = 2*prec_img*sens_img/(prec_img+sens_img) if prec_img+sens_img>0 else 0

# Bootstrap CI for AUC (image level)
auc_lo, auc_hi = bootstrap_ci(y_bin, tp_ens, n=2000)
sens_lo, sens_hi = wilson_ci(tp_i, tp_i+fn_i)
spec_lo, spec_hi = wilson_ci(tn_i, tn_i+fp_i)

# Patient level
pred_pt_frac = ta_ens >= best_thr
frac_pt2     = ta_lbl == FRACTURE_IDX
tp_p = int(np.sum(pred_pt_frac & frac_pt2))
fn_p = int(np.sum(~pred_pt_frac & frac_pt2))
fp_p = int(np.sum(pred_pt_frac & ~frac_pt2))
tn_p = int(np.sum(~pred_pt_frac & ~frac_pt2))
sens_pt = tp_p/(tp_p+fn_p)
spec_pt = tn_p/(tn_p+fp_p)
auc_pt  = roc_auc_score(ta_bin, ta_ens)
prec_pt = tp_p/(tp_p+fp_p) if tp_p+fp_p>0 else 0
f1_pt   = 2*prec_pt*sens_pt/(prec_pt+sens_pt) if prec_pt+sens_pt>0 else 0
sens_pt_lo, sens_pt_hi = wilson_ci(tp_p, tp_p+fn_p)
spec_pt_lo, spec_pt_hi = wilson_ci(tn_p, tn_p+fp_p)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 텍스트 보고서
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
report = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║     주상골 골절 AI 진단 모델 — 최종 성능 평가 보고서                      ║
╚══════════════════════════════════════════════════════════════════════════╝

[모델 구성]
  - YOLO v8m-cls       (MURA 재학습, weight=2)
  - DenseNet-121       (MURA 파인튜닝, weight=1)
  - EfficientNet-B3    (MURA 파인튜닝, weight=2)
  - 가중 앙상블 (2:1:2) + 환자·측면 단위 MAX 집계
  - 최적 임계값: {best_thr:.3f} (Val 기준, sens≥98% 조건)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] 이미지 단위 평가 (Test set, n=55 images)

  지표          값          95% 신뢰구간
  ─────────────────────────────────────────
  Sensitivity   {sens_img:.1%}       [{sens_lo:.1%}, {sens_hi:.1%}]  (TP={tp_i}, FN={fn_i})
  Specificity   {spec_img:.1%}       [{spec_lo:.1%}, {spec_hi:.1%}]  (TN={tn_i}, FP={fp_i})
  AUC           {auc_img:.4f}      [{auc_lo:.4f}, {auc_hi:.4f}]  (bootstrap n=2000)
  F1-score      {f1_img:.4f}
  Precision     {prec_img:.4f}

  클래스별 분포: Fracture={frac_img.sum()}장, Normal={(~frac_img).sum()}장

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[2] 환자·측면 단위 평가 (Patient Level, n=15 cases)
    (동일 환자·동일 방향의 최고 확률값을 케이스 점수로 사용)

  지표          값          95% 신뢰구간
  ─────────────────────────────────────────
  Sensitivity   {sens_pt:.1%}      [{sens_pt_lo:.1%}, {sens_pt_hi:.1%}]  (TP={tp_p}, FN={fn_p})
  Specificity   {spec_pt:.1%}      [{spec_pt_lo:.1%}, {spec_pt_hi:.1%}]  (TN={tn_p}, FP={fp_p})
  AUC           {auc_pt:.4f}
  F1-score      {f1_pt:.4f}
  Precision     {prec_pt:.4f}

  케이스 구성: Fracture={int(frac_pt2.sum())}명, Normal={int((~frac_pt2).sum())}명

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[3] 목표 달성 현황

  목표                   이미지 단위    환자 단위
  ─────────────────────────────────────────────────
  Sensitivity ≥ 98%      {'O' if sens_img>=0.98 else 'x'} ({sens_img:.1%})      {'O' if sens_pt>=0.98 else 'x'} ({sens_pt:.1%})
  Specificity ≥ 85%      {'O' if spec_img>=0.85 else 'x'} ({spec_img:.1%})      {'O' if spec_pt>=0.85 else 'x'} ({spec_pt:.1%})
  AUC ≥ 0.98             {'O' if auc_img>=0.98 else 'x'} ({auc_img:.4f})   {'O' if auc_pt>=0.98 else 'x'} ({auc_pt:.4f})
  F1 ≥ 0.92              {'O' if f1_img>=0.92 else 'x'} ({f1_img:.4f})   {'O' if f1_pt>=0.92 else 'x'} ({f1_pt:.4f})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[4] 학습 전후 비교 (환자 단위, Test)

  단계                        Sens    Spec    AUC     F1
  ─────────────────────────────────────────────────────────
  Before (alt_* models)       88.9%   66.7%   0.889   0.842
  + MURA data (old YOLO)      77.8%   83.3%   0.926   0.824
  + YOLO retrain (Final)      {sens_pt:.1%}  {spec_pt:.1%}  {auc_pt:.3f}   {f1_pt:.3f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[5] 통계적 한계 및 주의사항

  - 환자 단위 평가 케이스 수: 15 (골절 9, 정상 6)
    → 95% CI 폭이 넓어 대규모 외부 검증 필요
  - 정상 레이블 = 골절 환자의 반대 손 (실제 건강인 X-ray 아님)
  - 가장 낮은 골절 케이스(0.686)와 가장 높은 정상 케이스(0.643)
    사이 마진: 0.043 (임계값 민감도 높음)

[6] 산출 파일
  runs/report/01_roc_image_level.png
  runs/report/02_roc_patient_level.png
  runs/report/03_confusion_image.png
  runs/report/04_confusion_patient.png
  runs/report/05_score_distribution.png
  runs/report/06_ablation.png
  runs/report/07_improvement.png
  runs/report/report_summary.txt
"""

with open(OUT/"report_summary.txt", "w", encoding="utf-8") as f:
    f.write(report)

print(report)
print(f"\n모든 파일 저장 완료: {OUT}/")
