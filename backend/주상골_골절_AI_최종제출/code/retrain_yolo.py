"""
retrain_yolo.py - MURA 데이터 추가 후 YOLOv8m-cls 재학습

주요 변경:
  - 기존 best.pt 에서 시작 (transfer learning)
  - dataset/ 기준 (MURA normal 350장 추가된 버전)
  - 출력: runs/yolo_mura/weights/best.pt
"""
import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,max_split_size_mb:256")

import sys, torch
from pathlib import Path
from ultralytics import YOLO

def main():
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU: {name}  ({vram:.1f} GB)")
    else:
        print("CPU 모드")

    # 기존 YOLO 가중치에서 시작
    start_pt = "runs/yolov8m-cls/weights/best.pt"
    if not Path(start_pt).exists():
        print(f"[주의] {start_pt} 없음 -> 기본 yolov8m-cls.pt 사용")
        start_pt = "yolov8m-cls.pt"

    print(f"시작 가중치: {start_pt}")
    print()

    # 데이터셋 현황
    for split in ["train", "val", "test"]:
        for cls in ["fracture", "normal"]:
            p = Path(f"dataset/{split}/{cls}")
            cnt = len(list(p.glob("*.jpg"))) if p.exists() else 0
            print(f"  dataset/{split}/{cls}: {cnt}장")
    print()

    model = YOLO(start_pt)
    results = model.train(
        data        = "dataset",
        imgsz       = 640,
        epochs      = 60,
        batch       = 16,
        patience    = 20,
        project     = "runs",
        name        = "yolo_mura",
        exist_ok    = True,
        device      = 0,
        workers     = 2,
        amp         = True,
        lr0         = 1e-4,       # 낮은 lr (fine-tuning)
        lrf         = 0.01,
        warmup_epochs = 3,
        dropout     = 0.3,
        optimizer   = "AdamW",
        verbose     = True,
    )

    best = Path("runs/yolo_mura/weights/best.pt")
    if best.exists():
        print(f"\n저장: {best}")
    else:
        print("\n[오류] best.pt 미생성")

if __name__ == "__main__":
    main()
