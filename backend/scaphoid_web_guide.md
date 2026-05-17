# 주상골 골절 AI 진단 모델 — 웹 배포 가이드

## 모델 개요

손목 X-ray 이미지에서 주상골(Scaphoid) 골절 여부를 자동으로 분류하는 딥러닝 앙상블 모델입니다.

| 지표 | 결과 |
|------|------|
| 민감도 | **100%** (FN=0) |
| 특이도 | **66.7%** |
| AUC | **0.926** |
| 임상 벤치마크 대비 | 민감도 +13%p, AUC +0.118 |

**앙상블 구조:** YOLOv8m (가중치 0.5) + EfficientNet-B3 (가중치 2.0)  
**임계값:** 0.690

---

## 파일 구조

```
scaphoid_web/
├── app.py                          ← Streamlit 웹앱 (아래 코드 참고)
├── final_inference.py              ← 추론 핵심 로직
├── requirements.txt
└── models/
    ├── yolov8m_best.pt
    ├── efficientnet_b3_best.pth
    └── model_info.json
```

---

## 설치

### 1. Python 환경 (3.9 이상)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

**requirements.txt**
```
streamlit>=1.32.0
torch>=2.0.0
torchvision>=0.15.0
timm>=0.9.0
ultralytics>=8.0.0
Pillow>=9.0.0
numpy>=1.24.0
```

---

## 추론 API (`final_inference.py`)

### CLI 사용

```bash
# 단일 이미지
python final_inference.py image.jpg

# 여러 이미지 (같은 환자)
python final_inference.py img_001.jpg img_002.jpg img_003.jpg

# 결과를 JSON으로 저장
python final_inference.py image.jpg --out result.json
```

### Python 함수로 직접 호출

```python
from final_inference import run

results = run(["image1.jpg", "image2.jpg"])

for r in results:
    print(r["prediction"])       # "fracture" or "normal"
    print(r["patient_score"])    # 0.0 ~ 1.0 (골절 확률)
```

### 반환값 구조

```json
[
  {
    "file": "image1.jpg",
    "patient_id": "12345678",
    "image_score": 0.823,
    "patient_score": 0.823,
    "prediction": "fracture",
    "threshold": 0.690
  }
]
```

---

## Streamlit 웹앱 (`app.py`)

아래 코드를 `app.py`로 저장하세요.

```python
import streamlit as st
import tempfile, os
from pathlib import Path
from final_inference import run

st.set_page_config(
    page_title="주상골 골절 AI 진단",
    page_icon="🦴",
    layout="centered"
)

st.title("🦴 주상골 골절 AI 진단")
st.caption("X-ray 이미지를 업로드하면 골절 여부를 자동으로 분석합니다.")

st.info("**모델 성능:** 민감도 100% · 특이도 66.7% · AUC 0.926")

uploaded = st.file_uploader(
    "X-ray 이미지 업로드 (JPG/PNG, 여러 장 가능)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded:
    st.subheader("업로드된 이미지")
    cols = st.columns(min(len(uploaded), 4))
    for i, f in enumerate(uploaded):
        cols[i % 4].image(f, caption=f.name, use_column_width=True)

    if st.button("🔍 골절 분석 시작", type="primary", use_container_width=True):
        with st.spinner("AI 분석 중..."):
            with tempfile.TemporaryDirectory() as tmpdir:
                paths = []
                for f in uploaded:
                    p = os.path.join(tmpdir, f.name)
                    with open(p, "wb") as out:
                        out.write(f.read())
                    paths.append(p)

                results = run(paths)

        st.subheader("분석 결과")

        # 환자별 대표 결과 (patient_score 기준)
        seen = {}
        for r in results:
            pid = r["patient_id"]
            if pid not in seen or r["patient_score"] > seen[pid]["patient_score"]:
                seen[pid] = r

        for r in seen.values():
            score = r["patient_score"]
            pred  = r["prediction"]

            if pred == "fracture":
                st.error(f"⚠️ **골절 의심** — 확률 {score:.1%}")
            else:
                st.success(f"✅ **정상** — 확률 {1 - score:.1%}")

            col1, col2 = st.columns(2)
            col1.metric("골절 확률", f"{score:.1%}")
            col2.metric("판정", "골절 의심" if pred == "fracture" else "정상")

            st.progress(float(score))
            st.divider()

        st.caption("⚠️ 본 결과는 AI 보조 진단이며, 최종 판단은 반드시 전문의에게 확인하세요.")
```

### 실행

```bash
streamlit run app.py
```

브라우저에서 자동으로 `http://localhost:8501` 열립니다.

---

## 모델 경로 설정

`final_inference.py` 상단의 `MODEL_CFGS`에서 가중치 경로를 맞춰주세요.

```python
MODEL_CFGS = [
    ("yolov8m", "models/yolov8m_best.pt",          "yolo"),
    ("effnet",  "models/efficientnet_b3_best.pth",  "timm"),
]

WEIGHTS   = np.array([0.5, 2.0]); WEIGHTS /= WEIGHTS.sum()
THRESHOLD = 0.690
```

---

## 클라우드 배포 (Streamlit Cloud)

1. GitHub 저장소에 코드 업로드
2. [share.streamlit.io](https://share.streamlit.io) 접속
3. 저장소 연결 → `app.py` 선택 → Deploy

> ⚠️ 모델 가중치(110MB)는 Git LFS 또는 Google Drive 링크로 관리 권장

---

## 주의사항

- 본 모델은 **주상골(Scaphoid) X-ray 전용**입니다.
- 다른 부위 X-ray에는 적용하지 마세요.
- AI 진단 결과는 보조 도구이며, 최종 진단은 전문의 판단이 필요합니다.
