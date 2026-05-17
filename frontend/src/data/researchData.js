/** 문서 기반 정적 연구 데이터 (모델설명.md, 단일모델_vs_앙상블.md, 개발보고서.md) */

export const SINGLE_MODELS = [
  { name: 'YOLOv8s-cls', params: '6M', input: '640px', sensitivity: 77.1, specificity: 75.0, auc: 0.851, fn: 8, note: '—', ensemble: false },
  { name: 'YOLOv8m-cls', params: '17M', input: '640px', sensitivity: 85.7, specificity: 75.0, auc: 0.867, fn: 5, note: 'YOLO 최고 · 앙상블 채택', ensemble: true },
  { name: 'YOLOv8l-cls', params: '37M', input: '640px', sensitivity: 42.9, specificity: 80.0, auc: 0.596, fn: 20, note: '과적합', ensemble: false },
  { name: 'YOLOv8x-cls', params: '57M', input: '640px', sensitivity: 71.4, specificity: 65.0, auc: 0.711, fn: 10, note: '과적합', ensemble: false },
  { name: 'YOLOv8m+CLAHE', params: '17M', input: '800px', sensitivity: 62.9, specificity: 70.0, auc: 0.660, fn: 13, note: 'CLAHE 역효과', ensemble: false },
  { name: 'YOLO11m-cls', params: '21M', input: '640px', sensitivity: 60.0, specificity: 50.0, auc: 0.637, fn: 14, note: '학습 실패', ensemble: false },
  { name: 'EfficientNet-B3', params: '12M', input: '300px', sensitivity: 88.6, specificity: 70.0, auc: 0.850, fn: 4, note: '균형 최고 · 앙상블 채택', ensemble: true },
  { name: 'DenseNet-121', params: '8M', input: '224px', sensitivity: 94.3, specificity: 55.0, auc: 0.731, fn: 2, note: '민감도 최고 · 앙상블 채택', ensemble: true },
  { name: 'ConvNeXt-Tiny', params: '28M', input: '640px', sensitivity: 85.7, specificity: 55.0, auc: 0.737, fn: 5, note: '파라미터 과다', ensemble: false },
  { name: 'Swin-Tiny', params: '28M', input: '224px', sensitivity: 77.1, specificity: 60.0, auc: 0.713, fn: 8, note: '해상도 손실', ensemble: false },
  { name: 'ResNet-50', params: '25M', input: '640px', sensitivity: 71.4, specificity: 70.0, auc: 0.704, fn: 10, note: '과적합', ensemble: false },
  { name: 'ViT-Small', params: '22M', input: '224px', sensitivity: 97.1, specificity: 10.0, auc: 0.749, fn: 1, note: '편향(전부 골절 예측)', ensemble: false },
  { name: 'MobileNetV3-Large', params: '5.5M', input: '640px', sensitivity: 74.3, specificity: 75.0, auc: 0.771, fn: 6, note: '경량화 후보', ensemble: false },
];

export const TIMELINE_STEPS = [
  {
    step: 1,
    title: '13종 단일 모델 실험',
    summary: 'YOLOv8 계열 6종 + timm CNN/Transformer 7종',
    detail: '단일 모델 최대 민감도 94.3%, 특이도 55~75% — 임상 목표(민감도≥98%, 특이도≥85%) 동시 미달.',
    insight: '근본 원인: 정상 훈련 데이터가 모두 골절 환자 반대손 → 실제 정상 손목 X-ray 학습 경험 없음',
    metrics: null,
  },
  {
    step: 2,
    title: 'MURA v1.1 외부 데이터 활용',
    summary: 'Stanford 공개 정상 손목 X-ray 350장 추가 (train)',
    detail: 'YOLO 정상 이미지 평균 골절 확률 0.503 → 0.122 (재학습 후)',
    insight: '특이도 66.7% → 83.3% (+16.6%p) — 실제 건강인 손목 데이터가 정상 판별의 결정적 개선',
    metrics: { sensitivity: 77.8, specificity: 83.3, auc: 0.926 },
  },
  {
    step: 3,
    title: '3모델 앙상블 + 환자 단위 집계',
    summary: '가중 앙상블(2:1:2) + MAX 집계 + 임계값 0.652',
    detail: 'YOLO 재학습으로 정상 오탐 병목 제거 → 최종 성능 달성',
    insight: '민감도 77.8% → 100%, 특이도 83.3% → 100%',
    metrics: { sensitivity: 100.0, specificity: 100.0, auc: 1.000 },
  },
];

export const ENSEMBLE_MODELS = [
  {
    name: 'YOLOv8m-cls',
    weight: 2,
    role: '정상 판별',
    strength: '특이도 75% (YOLO 최고)',
    weakness: '민감도 85.7%',
    single: { sensitivity: 85.7, specificity: 75.0, auc: 0.867 },
  },
  {
    name: 'DenseNet-121',
    weight: 1,
    role: '골절 탐지',
    strength: '민감도 94.3% (전체 최고)',
    weakness: '특이도 55%',
    single: { sensitivity: 94.3, specificity: 55.0, auc: 0.731 },
  },
  {
    name: 'EfficientNet-B3',
    weight: 2,
    role: '균형·안정화',
    strength: '민감도 88.6% / 특이도 70%',
    weakness: '어느 쪽도 단일 최고는 아님',
    single: { sensitivity: 88.6, specificity: 70.0, auc: 0.850 },
  },
];

export const PERFORMANCE_BY_UNIT = {
  image: {
    label: '이미지 단위',
    n: 'n=55장',
    cohort: { total: 55 },
    goalsMet: 1,
    goalsTotal: 4,
    description: '개별 X-ray 1장 기준. Lateral 등 일부 방향에서 골절선이 불명확해 민감도가 낮게 나올 수 있음.',
    headline: '이미지 단위에서는 임상 목표 4개 중 1개만 충족(특이도) — 환자·측면 MAX 집계가 필요한 이유를 보여줍니다.',
    summaryCards: [
      { value: '1/4', label: '임상 목표 달성', sub: '민감도·AUC·F1 미달', warn: true },
      { value: '80.0', unit: '%', label: '민감도', sub: '목표 ≥98% 미달', warn: true },
      { value: '0.919', label: 'AUC', sub: '목표 ≥0.98 미달', warn: true },
      { value: '55', label: '평가 이미지', sub: 'Test 세트' },
    ],
    metrics: [
      { name: '민감도', target: '≥98%', resultLabel: '미달', valueDetail: '80.0%', achieved: false, ci: '[64.1%, 90.0%]' },
      { name: '특이도', target: '≥85%', resultLabel: '충족', valueDetail: '100.0%', achieved: true, ci: '[83.9%, 100.0%]' },
      { name: 'AUC', target: '≥0.98', resultLabel: '미달', valueDetail: '0.919', achieved: false, ci: '[0.826, 0.989]' },
      { name: 'F1-score', target: '≥0.92', resultLabel: '미달', valueDetail: '0.889', achieved: false, ci: '—' },
    ],
  },
  patient: {
    label: '환자·측면 단위',
    n: 'n=15 케이스',
    cohort: { total: 15, fracture: 9, normal: 6 },
    errors: { fn: 0, fp: 0 },
    goalsMet: 4,
    goalsTotal: 4,
    description: '동일 환자·동일 방향 이미지 중 MAX 확률로 케이스 판정 — 실제 임상 판단 흐름과 동일.',
    headline: '단일 기관 파일럿 Test(n=15)에서 임상 목표를 모두 충족했으며, 골절·정상 케이스 모두 오분류가 없었습니다.',
    summaryCards: [
      { value: '0', label: 'False Negative (FN)', sub: '골절 9케이스 — 미검 0건', highlight: true },
      { value: '0', label: 'False Positive (FP)', sub: '정상 6케이스 — 오판 0건', highlight: true },
      { value: '4/4', label: '임상 목표 달성', sub: '민감도·특이도·AUC·F1', highlight: true },
      { value: '15', label: '평가 케이스', sub: '95% CI 넓음 · 외부 검증 전' },
    ],
    metrics: [
      { name: '민감도', target: '≥98%', resultLabel: '충족', valueDetail: '100.0%', achieved: true, ci: '[70.1%, 100.0%]' },
      { name: '특이도', target: '≥85%', resultLabel: '충족', valueDetail: '100.0%', achieved: true, ci: '[61.0%, 100.0%]' },
      { name: 'AUC', target: '≥0.98', resultLabel: '충족', valueDetail: '1.000', achieved: true, ci: '—' },
      { name: 'F1-score', target: '≥0.92', resultLabel: '충족', valueDetail: '1.000', achieved: true, ci: '—' },
    ],
    extra: '측정값 100%는 소규모 Test(n=15)에서의 결과입니다. 임계값 0.652, 골절·정상 점수 마진 0.043. 다기관 외부 검증이 필요합니다.',
  },
};

export const LIMITATIONS = [
  { title: '소규모 평가', text: '환자 단위 n=15 → 95% CI 폭이 넓음 (민감도 [70.1%, 100%], 특이도 [61.0%, 100%])' },
  { title: '정상 레이블', text: '골절 환자 반대손 기준 (실제 건강인 X-ray 아님)' },
  { title: '임계값 마진', text: '최저 골절(0.686) − 최고 정상(0.643) = 0.043 — 새 케이스에 민감할 수 있음' },
  { title: '검증 범위', text: '단일 기관 데이터 — 외부 기관·장비 일반화 미검증' },
  { title: '탐지 대상', text: '주상골 골절 전용 — 요골·척골 등 다른 손목 이상은 대상 아님' },
];

export const CLINICAL_TARGETS = { sensitivity: 98, specificity: 85 };
