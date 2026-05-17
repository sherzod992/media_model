# 주상골 골절 AI 진단 웹 애플리케이션 (MediAI-FX Clone)

크레스콤(Crescom)의 "MediAI-FX" 웹사이트와 유사한 다크 모드 프리미엄 UI가 적용된 X-ray 진단 웹 애플리케이션입니다.
프로젝트는 관리가 용이하도록 프론트엔드와 백엔드로 완전히 분리된 구조를 가집니다.

## 폴더 구조

```text
d:\x_rayWeb\
├── backend/                  # AI 추론 API 서버 (FastAPI)
│   ├── main.py               # FastAPI 메인 서버 (포트 9090)
│   ├── final_inference.py    # AI 모델 추론 코어 로직
│   ├── requirements.txt      # 파이썬 패키지 의존성
│   └── models/               # AI 모델 가중치 폴더 (.pt, .pth)
│
├── frontend/                 # 사용자 인터페이스 (React + Vite)
│   ├── index.html            # 웹 진입점 및 SEO 태그
│   ├── package.json          # NPM 패키지 설정
│   └── src/
│       ├── App.jsx           # 메인 UI 레이아웃 및 업로드 로직
│       ├── main.jsx          # React 엔트리
│       └── index.css         # 다크모드 전용 프리미엄 디자인 CSS
└── README.md                 # 프로젝트 가이드
```

## 실행 방법

웹 애플리케이션을 구동하기 위해서는 **백엔드(AI 서버)**와 **프론트엔드(웹 서버)**를 각각 실행해야 합니다.

### 1. 백엔드(AI 서버) 실행

파이썬 환경(가상환경 등)이 활성화된 상태에서 패키지를 설치하고 서버를 실행합니다.

```bash
cd backend
pip install -r requirements.txt
python main.py
```
*백엔드 API 서버는 `http://localhost:9090` 에서 동작합니다.*

### 2. 프론트엔드(웹 UI) 실행

새로운 터미널을 열고 프론트엔드 폴더로 이동하여 웹 서버를 엽니다. Node.js가 설치되어 있어야 합니다.

```bash
cd frontend
npm install
npm run dev
```
*실행 후 터미널에 표시되는 로컬 주소 (예: `http://localhost:5173`)를 브라우저에서 열어 사용하세요.*

## 주요 기능 및 특징
1. **프리미엄 UI/UX**: 크레스콤 레퍼런스 스타일을 반영하여 어두운 테마(Dark Mode)의 유리질감(Glassmorphism)과 반응형 컴포넌트 적용
2. **환자별 결과 병합**: 여러 장의 사진을 업로드 시 `patient_id`를 기준으로 가장 확률이 높은 결과 도출
3. **결과 시각화**: 골절 확률을 퍼센테이지 형태의 바(Bar)차트로 직관적으로 표시하며, 정상 여부에 따라 색상 동적 변경
