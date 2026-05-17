"""
prepare_mura.py - MURA v1.1 negative wrist 이미지를 dataset/에 추가

전략:
  - XR_WRIST negative(정상) 만 사용
  - study 당 최대 2장 (다양성 확보)
  - 그레이스케일(L) -> RGB 변환
  - PNG -> JPG 변환
  - 최소 해상도 필터 (가로 또는 세로 < 150px 제외)
  - train: 350장, val: 60장
"""
import sys, random, shutil
sys.stdout.reconfigure(encoding='utf-8')
import argparse
from pathlib import Path
from PIL import Image

MURA_ROOT   = Path("new_data_1/MURA-v1.1")
DST_TRAIN   = Path("dataset/train/normal")
DST_VAL     = Path("dataset/val/normal")
TRAIN_ADD   = 350
VAL_ADD     = 60
MAX_PER_STUDY = 2
MIN_DIM     = 150   # 최소 가로/세로 픽셀
SEED        = 42


def collect_negative_studies(split: str):
    """MURA negative wrist study 목록 반환."""
    p = MURA_ROOT / split / "XR_WRIST"
    studies = []
    for patient in sorted(p.iterdir()):
        if not patient.is_dir():
            continue
        for study in sorted(patient.iterdir()):
            if not study.is_dir():
                continue
            if "negative" in study.name:
                studies.append(study)
    return studies


def collect_images_from_studies(studies, max_per_study, min_dim):
    """study 목록에서 이미지 경로 수집 (study당 최대 max_per_study장)."""
    pool = []
    for study in studies:
        imgs = sorted(study.glob("*.png")) + sorted(study.glob("*.jpg"))
        # 최소 해상도 필터
        valid = []
        for img in imgs:
            try:
                w, h = Image.open(img).size
                if w >= min_dim and h >= min_dim:
                    valid.append(img)
            except Exception:
                pass
        if valid:
            random.shuffle(valid)
            pool.extend(valid[:max_per_study])
    return pool


def copy_as_jpg(src: Path, dst_dir: Path, idx: int):
    """이미지를 RGB JPG로 변환해 저장."""
    img = Image.open(src).convert("RGB")
    name = f"mura_neg_{idx:04d}.jpg"
    img.save(dst_dir / name, "JPEG", quality=90)
    return name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-add", type=int, default=TRAIN_ADD)
    parser.add_argument("--val-add",   type=int, default=VAL_ADD)
    parser.add_argument("--dry-run",   action="store_true")
    args = parser.parse_args()

    random.seed(SEED)

    DST_TRAIN.mkdir(parents=True, exist_ok=True)
    DST_VAL.mkdir(parents=True, exist_ok=True)

    # 기존 MURA 파일이 있으면 제거 (재실행 시 중복 방지)
    removed = 0
    for f in list(DST_TRAIN.glob("mura_neg_*.jpg")) + list(DST_VAL.glob("mura_neg_*.jpg")):
        f.unlink()
        removed += 1
    if removed:
        print(f"기존 MURA 파일 {removed}개 제거")

    # ── Train ──────────────────────────────────────────────────
    print("\n[Train] MURA negative wrist study 수집 중...")
    train_studies = collect_negative_studies("train")
    random.shuffle(train_studies)
    train_pool = collect_images_from_studies(train_studies, MAX_PER_STUDY, MIN_DIM)
    random.shuffle(train_pool)

    print(f"  study 수: {len(train_studies)},  이미지 풀: {len(train_pool)}장")

    if len(train_pool) < args.train_add:
        print(f"  [경고] 풀({len(train_pool)}) < 요청({args.train_add}), 전체 사용")
        selected_train = train_pool
    else:
        selected_train = train_pool[:args.train_add]

    if not args.dry_run:
        for i, src in enumerate(selected_train):
            copy_as_jpg(src, DST_TRAIN, i)
        print(f"  -> dataset/train/normal 에 {len(selected_train)}장 추가 완료")
    else:
        print(f"  [dry-run] {len(selected_train)}장 추가 예정")

    # ── Val ────────────────────────────────────────────────────
    print("\n[Val] MURA negative wrist study 수집 중...")
    val_studies = collect_negative_studies("valid")
    random.shuffle(val_studies)
    val_pool = collect_images_from_studies(val_studies, 1, MIN_DIM)  # val은 study당 1장
    random.shuffle(val_pool)

    print(f"  study 수: {len(val_studies)},  이미지 풀: {len(val_pool)}장")

    if len(val_pool) < args.val_add:
        print(f"  [경고] 풀({len(val_pool)}) < 요청({args.val_add}), 전체 사용")
        selected_val = val_pool
    else:
        selected_val = val_pool[:args.val_add]

    if not args.dry_run:
        for i, src in enumerate(selected_val):
            copy_as_jpg(src, DST_VAL, i)
        print(f"  -> dataset/val/normal 에 {len(selected_val)}장 추가 완료")
    else:
        print(f"  [dry-run] {len(selected_val)}장 추가 예정")

    # ── 최종 통계 ──────────────────────────────────────────────
    print("\n=== 추가 후 dataset 구성 ===")
    for split in ["train", "val", "test"]:
        for cls in ["fracture", "normal"]:
            p = Path(f"dataset/{split}/{cls}")
            if p.exists():
                cnt = len(list(p.glob("*.jpg")))
                print(f"  dataset/{split}/{cls}: {cnt}장")


if __name__ == "__main__":
    main()
