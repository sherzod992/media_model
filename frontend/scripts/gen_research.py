# -*- coding: utf-8 -*-
from pathlib import Path

o, c = "<div", "</motion.div>".replace("motion.", "")  # </motion.div>
o, c = "<motion.div", "</motion.div>".replace("motion.div", "div")  # still wrong

o = "<" + "div"
c = "</" + "div>"

def w(*parts):
    return "".join(parts)

path = Path(r"d:\x_rayWeb\frontend\src\components\ResearchPage.jsx")

body = f'''import {{ useState }} from 'react';
import SensSpecChart from './SensSpecChart';
import {{
  SINGLE_MODELS,
  TIMELINE_STEPS,
  ENSEMBLE_MODELS,
  PERFORMANCE_BY_UNIT,
  LIMITATIONS,
}} from '../data/researchData';

export default function ResearchPage() {{
  const [evalUnit, setEvalUnit] = useState('patient');
  const [showAllModels, setShowAllModels] = useState(false);
  const perf = PERFORMANCE_BY_UNIT[evalUnit];
  const displayModels = showAllModels
    ? SINGLE_MODELS
    : SINGLE_MODELS.filter((m) => m.ensemble || m.name.includes('ViT') || m.name.includes('CLAHE'));

  return (
    <>
      <section className="hero-section" id="hero">
        {o} className="hero-content">
          <p className="hero-eyebrow">주상골 골절 X-ray AI · 방법론 연구 소개</p>
          <h1 className="hero-title">
            단일 모델의 한계를 넘는<br />
            <span className="text-gradient">3모델 가중 앙상블</span>
          </h1>
          <p className="hero-subtitle">
            13종 단일 모델 실험, MURA 외부 데이터 보완, 환자·측면 단위 MAX 집계를 통해
            소규모 데이터(497장)에서도 임상 목표를 달성한 과정을 소개합니다.
          </p>
          {o} className="hero-tags">
            <span>YOLOv8m + DenseNet-121 + EfficientNet-B3</span>
            <span>가중치 2:1:2</span>
            <span>Test 환자·측면 n=15</span>
          {c}
          {o} className="hero-actions">
            <button type="button" className="btn btn-primary btn-lg" onClick={{() => document.getElementById('background')?.scrollIntoView({{ behavior: 'smooth' }})}}>
              연구 스토리 보기
            </button>
            <button type="button" className="btn btn-secondary btn-lg" onClick={{() => document.getElementById('demo')?.scrollIntoView({{ behavior: 'smooth' }})}}>
              추론 데모
            </button>
          {c}
        {c}
      </section>
    </>
  );
}}
'''

path.write_text(body, encoding="utf-8")
print("ok", path)
