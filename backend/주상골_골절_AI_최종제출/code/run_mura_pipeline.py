"""
run_mura_pipeline.py - MURA 데이터 추가 후 전체 학습 + 평가 파이프라인

변경점:
  - 시작 가중치: alt_densenet121 / alt_efficientnet_b3 (label 정합성 확인된 best)
  - normal_w: 1.3 (train normal 522장으로 늘었으므로 낮춤)
  - 출력: runs/mura_densenet121 / runs/mura_efficientnet_b3
  - 평가: 이미지 단위(ensemble_final) + 환자-측면 단위(ensemble_patient)

Usage:
  python run_mura_pipeline.py
  python run_mura_pipeline.py --skip-train
"""
import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,max_split_size_mb:256")

import argparse, subprocess, sys, time
from pathlib import Path
import torch


def run(cmd, desc):
    print(f"\n{'='*65}")
    print(f">>> {desc}")
    print(f"    {' '.join(str(c) for c in cmd)}")
    print(f"{'='*65}")
    t0 = time.time()
    result = subprocess.run(cmd, check=False)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"\n[경고] 종료코드 {result.returncode}. 계속 진행.")
    else:
        print(f"\n[완료] {desc}  ({elapsed/60:.1f}분)")
    return result.returncode == 0


def check_gpu():
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU: {name}  ({total:.1f} GB VRAM)")
    else:
        print("GPU 사용 불가 - CPU 모드 (느림)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--epochs",     type=int, default=100)
    parser.add_argument("--patience",   type=int, default=25)
    args = parser.parse_args()

    py = sys.executable

    print(f"\n{'='*65}")
    print("주상골 골절 진단 AI - MURA 데이터 추가 학습 파이프라인")
    print(f"{'='*65}")
    check_gpu()

    # 시작 가중치 (label 정합성이 확인된 alt_*)
    dn_start = "runs/alt_densenet121/weights/best.pth"
    ef_start = "runs/alt_efficientnet_b3/weights/best.pth"
    dn_out   = "runs/mura_densenet121/weights/best.pth"
    ef_out   = "runs/mura_efficientnet_b3/weights/best.pth"

    if not args.skip_train:

        # 데이터셋 현황 출력
        print("\n[데이터셋 현황]")
        for split in ["train", "val", "test"]:
            for cls in ["fracture", "normal"]:
                p = Path(f"dataset/{split}/{cls}")
                cnt = len(list(p.glob("*.jpg"))) if p.exists() else 0
                print(f"  dataset/{split}/{cls}: {cnt}장")

        # Step 1: DenseNet-121
        dn_cmd = [py, "train_safe.py",
                  "--model",     "densenet121",
                  "--run-name",  "mura_densenet121",
                  "--epochs",    str(args.epochs),
                  "--patience",  str(args.patience),
                  "--normal-w",  "1.3",
                  "--mixup-p",   "0.4",
                  ]
        if Path(dn_start).exists():
            dn_cmd += ["--pretrained", dn_start]
            print(f"\nDenseNet 시작 가중치: {dn_start}")
        else:
            print(f"\n[주의] {dn_start} 없음 -> ImageNet 시작")

        run(dn_cmd, "Step 1: DenseNet-121 (MURA 데이터)")

        # Step 2: EfficientNet-B3
        ef_cmd = [py, "train_safe.py",
                  "--model",     "efficientnet_b3",
                  "--run-name",  "mura_efficientnet_b3",
                  "--epochs",    str(args.epochs),
                  "--patience",  str(args.patience),
                  "--normal-w",  "1.3",
                  "--mixup-p",   "0.4",
                  ]
        if Path(ef_start).exists():
            ef_cmd += ["--pretrained", ef_start]
            print(f"\nEfficientNet 시작 가중치: {ef_start}")
        else:
            print(f"\n[주의] {ef_start} 없음 -> ImageNet 시작")

        run(ef_cmd, "Step 2: EfficientNet-B3 (MURA 데이터)")

    # 체크포인트 선택 (mura -> alt 순)
    def pick(mura, alt):
        return mura if Path(mura).exists() else alt

    dn_ckpt = pick(dn_out, dn_start)
    ef_ckpt = pick(ef_out, ef_start)
    print(f"\n체크포인트:")
    print(f"  DenseNet    : {dn_ckpt}")
    print(f"  EfficientNet: {ef_ckpt}")

    # Step 3: 이미지 단위 앙상블
    run([py, "ensemble_final.py",
         "--dn-ckpt",     dn_ckpt,
         "--ef-ckpt",     ef_ckpt,
         "--target-sens", "0.98",
         "--out-dir",     "runs/mura_ensemble_img",
         ], "Step 3: 이미지 단위 앙상블 평가")

    # Step 4: 환자-측면 단위 앙상블
    run([py, "ensemble_patient.py",
         "--dn-ckpt",     dn_ckpt,
         "--ef-ckpt",     ef_ckpt,
         "--target-sens", "0.98",
         "--out-dir",     "runs/mura_ensemble_patient",
         ], "Step 4: 환자-측면 단위 앙상블 평가")

    print(f"\n{'='*65}")
    print("파이프라인 완료!")
    print("  이미지 단위 결과: runs/mura_ensemble_img/results.json")
    print("  환자 단위 결과:   runs/mura_ensemble_patient/results.json")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
