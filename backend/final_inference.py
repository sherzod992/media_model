"""
final_inference.py
최종 앙상블 추론: yolov8m(0.5) + densenet121(2.0) + efficientnet_b3(1.5)
임계값 0.515, 민감도 100%, 특이도 66.7%, AUC 0.9630
"""
import argparse, json, re
from pathlib import Path
from collections import defaultdict

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
import timm
from ultralytics import YOLO

CLASSES      = ["fracture", "normal"]
FRACTURE_IDX = 0
MEAN = [0.485, 0.456, 0.406]
STD  = [0.229, 0.224, 0.225]
TTA  = [(False,0),(True,0),(False,10),(True,10),(False,-10),(True,-10),(False,20),(True,-20)]

WEIGHTS   = np.array([2.0, 1.0, 2.0]); WEIGHTS /= WEIGHTS.sum()
THRESHOLD = 0.515

MODEL_CFGS = [
    ("yolov8m", "주상골_골절_AI_최종제출/weights/yolo_mura_best.pt", "yolo", None, None),
    ("densenet", "주상골_골절_AI_최종제출/weights/densenet121_mura_best.pth", "timm", "densenet121", 224),
    ("effnet",  "주상골_골절_AI_최종제출/weights/efficientnet_b3_mura_best.pth",  "timm", "efficientnet_b3", 300),
]


def pid(path):
    m = re.match(r"(\d{8})", Path(path).name)
    return m.group(1) if m else Path(path).name


@torch.no_grad()
def infer_timm(model, paths, imgsz, device):
    acc = np.zeros(len(paths))
    for hflip, angle in TTA:
        ops = [transforms.Resize((imgsz, imgsz))]
        if hflip:  ops.append(transforms.RandomHorizontalFlip(1.0))
        if angle:  ops.append(transforms.RandomRotation((angle, angle)))
        ops += [transforms.ToTensor(), transforms.Normalize(MEAN, STD)]
        tfm = transforms.Compose(ops)
        for i, p in enumerate(paths):
            img = Image.open(p).convert("RGB")
            acc[i] += torch.softmax(
                model(tfm(img).unsqueeze(0).to(device)), 1
            )[0, FRACTURE_IDX].item()
    return acc / len(TTA)


def infer_yolo(ckpt, paths):
    yolo = YOLO(ckpt)
    probs = np.array([
        r.probs.data.cpu().numpy()[FRACTURE_IDX]
        for r in yolo.predict([str(p) for p in paths], imgsz=640, verbose=False)
    ])
    del yolo
    return probs


def patient_score(paths, probs):
    pat = defaultdict(list)
    for p, prob in zip(paths, probs):
        pat[pid(p)].append(prob)
    return {k: max(v) for k, v in pat.items()}


def extract_attention_regions(cam, img_w, img_h, max_regions=3, percentile=85):
    """Grad-CAM 활성도에서 정규화(0~1) 바운딩 박스 추출."""
    import cv2

    cam_norm = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    thresh_val = float(np.percentile(cam_norm, percentile))
    mask = (cam_norm >= thresh_val).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = img_w * img_h * 0.002
    regions = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        pad = int(max(w, h) * 0.08)
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(img_w - x, w + pad * 2)
        h = min(img_h - y, h + pad * 2)
        score = float(cam_norm[y : y + h, x : x + w].max())
        regions.append({
            "x": round(x / img_w, 4),
            "y": round(y / img_h, 4),
            "w": round(w / img_w, 4),
            "h": round(h / img_h, 4),
            "score": round(score, 3),
        })

    regions.sort(key=lambda r: r["score"], reverse=True)
    return regions[:max_regions]


def generate_gradcam(model, paths, imgsz, device):
    try:
        from pytorch_grad_cam import GradCAM
        from pytorch_grad_cam.utils.image import show_cam_on_image
        from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
        import cv2
    except ImportError:
        print("Grad-CAM packages not installed.")
        return {}

    # 모델에 따라 마지막 컨볼루션 레이어 선택
    if hasattr(model, 'conv_head'):
        target_layers = [model.conv_head]
    elif hasattr(model, 'features'):
        target_layers = [model.features[-1]]
    else:
        return {}
    
    cam = GradCAM(model=model, target_layers=target_layers)
    targets = [ClassifierOutputTarget(FRACTURE_IDX)]
    
    heatmap_data = {}

    for p in paths:
        try:
            img_origin = cv2.imread(str(p))
            if img_origin is None:
                continue
                
            rgb_img = cv2.cvtColor(img_origin, cv2.COLOR_BGR2RGB)
            rgb_img_float = np.float32(rgb_img) / 255
            
            img_resized = cv2.resize(rgb_img, (imgsz, imgsz))
            tfm = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(MEAN, STD)
            ])
            img_tensor = tfm(img_resized).unsqueeze(0).to(device)
            
            grayscale_cam = cam(input_tensor=img_tensor, targets=targets)[0, :]
            
            h, w = img_origin.shape[:2]
            grayscale_cam_resized = cv2.resize(grayscale_cam, (w, h))
            regions = extract_attention_regions(grayscale_cam_resized, w, h)
            visualization = show_cam_on_image(rgb_img_float, grayscale_cam_resized, use_rgb=True)

            heatmap_path = str(p) + "_heatmap.jpg"
            cv2.imwrite(heatmap_path, cv2.cvtColor(visualization, cv2.COLOR_RGB2BGR))
            heatmap_data[str(p)] = {"path": heatmap_path, "regions": regions}
        except Exception as e:
            print(f"Grad-CAM Error on {p}: {e}")

    return heatmap_data


def run(image_paths):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    paths  = [Path(p) for p in image_paths]
    model_probs = []
    heatmap_dict = {}

    for name, ckpt, mtype, timm_name, imgsz in MODEL_CFGS:
        print(f"  [{name}] 추론 중...")
        if mtype == "yolo":
            p = infer_yolo(ckpt, paths)
        else:
            m = timm.create_model(timm_name, pretrained=False,
                                  num_classes=2,
                                  drop_rate=0.4).to(device)
            m.load_state_dict(torch.load(ckpt, map_location=device, weights_only=True))
            m.eval()
            p = infer_timm(m, paths, imgsz, device)
            
            hmaps = generate_gradcam(m, paths, imgsz, device)
            heatmap_dict.update(hmaps)
            
            del m; torch.cuda.empty_cache()
        model_probs.append(p)

    ensemble = sum(WEIGHTS[i] * model_probs[i] for i in range(len(MODEL_CFGS)))
    pat_scores = patient_score(paths, ensemble)

    results = []
    for p, score in zip(paths, ensemble):
        patient_id = pid(p)
        patient_score_val = pat_scores[patient_id]
        pred = "fracture" if patient_score_val >= THRESHOLD else "normal"
        
        res = {
            "file": str(p),
            "patient_id": patient_id,
            "image_score": float(score),
            "patient_score": float(patient_score_val),
            "prediction": pred,
            "threshold": THRESHOLD,
        }
        if str(p) in heatmap_dict:
            hdata = heatmap_dict[str(p)]
            res["heatmap_path"] = hdata["path"]
            if hdata.get("regions"):
                res["attention_regions"] = hdata["regions"]
            
        results.append(res)

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+", help="X-ray JPG 파일 경로(들)")
    ap.add_argument("--out", default=None, help="결과 JSON 저장 경로")
    args = ap.parse_args()

    print(f"\n=== 주상골 골절 검출 (앙상블) ===")
    print(f"임계값: {THRESHOLD}  |  가중치: YOLO={WEIGHTS[0]:.3f}, DenseNet={WEIGHTS[1]:.3f}, EfficientNet={WEIGHTS[2]:.3f}\n")

    results = run(args.images)

    print(f"\n{'파일':<40}  {'환자ID':<10}  {'점수':>6}  {'결과'}")
    print("-" * 70)
    for r in results:
        fname = Path(r["file"]).name
        print(f"{fname:<40}  {r['patient_id']:<10}  {r['patient_score']:.4f}  {r['prediction'].upper()}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n저장: {args.out}")


if __name__ == "__main__":
    main()
