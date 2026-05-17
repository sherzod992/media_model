# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(r"d:\x_rayWeb\frontend\src")

RESEARCH = r'''import { useState } from 'react';
import SensSpecChart from './SensSpecChart';
import PerfVisual from './PerfVisual';
import BackgroundSection from './BackgroundSection';
import {
  SINGLE_MODELS,
  TIMELINE_STEPS,
  ENSEMBLE_MODELS,
  PERFORMANCE_BY_UNIT,
  LIMITATIONS,
} from '../data/researchData';

export default function ResearchPage() {
  const [evalUnit, setEvalUnit] = useState('patient');
  const [showAllModels, setShowAllModels] = useState(false);
  const perf = PERFORMANCE_BY_UNIT[evalUnit];
  const displayModels = showAllModels
    ? SINGLE_MODELS
    : SINGLE_MODELS.filter((m) => m.ensemble || m.name.includes('ViT') || m.name.includes('CLAHE'));

  return (
    <>
      <section className="hero-section" id="hero">
        <motion.div className="hero-content">
          <p className="hero-eyebrow">주상골 골절 X-ray AI · 방법론 연구 소개</p>
          <h1 className="hero-title">
            단일 모델의 한계를 넘는<br />
            <span className="text-gradient">3모델 가중 앙상블</span>
          </h1>
          <p className="hero-subtitle">
            13종 단일 모델 실험, MURA 외부 데이터 보완, 환자·측면 단위 MAX 집계를 통해
            소규모 데이터(497장)에서도 임상 목표를 달성한 과정을 소개합니다.
          </p>
          <motion.div className="hero-tags">
            <span>YOLOv8m + DenseNet-121 + EfficientNet-B3</span>
            <span>가중치 2:1:2</span>
            <span>Test 환자·측면 n=15</span>
          </motion.div>
          <motion.div className="hero-actions">
            <button type="button" className="btn btn-primary btn-lg" onClick={() => document.getElementById('background')?.scrollIntoView({ behavior: 'smooth' })}>
              연구 스토리 보기
            </button>
            <button type="button" className="btn btn-secondary btn-lg" onClick={() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })}>
              추론 데모
            </button>
          </motion.div>
        </motion.div>
      </section>

      <BackgroundSection />

      <section className="research-section" id="experiments">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>단일 모델 실험 — 13종 비교</h2>
            <p className="section-desc">
              Test 세트 이미지 단위(n=55, 골절 35 / 정상 20). 소규모 의료 X-ray(~500장)에서는 8~17M CNN이 최적이며,
              Transformer·대형 모델은 과적합 또는 편향이 나타났습니다.
            </p>
          </header>
          <motion.div className="experiments-layout">
            <SensSpecChart />
            <motion.div className="table-panel">
              <motion.div className="table-toolbar">
                <span className="text-sm text-secondary">평가: 이미지 단위 · Test n=55</span>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAllModels(!showAllModels)}>
                  {showAllModels ? '핵심만 보기' : '13종 전체 보기'}
                </button>
              </motion.div>
              <motion.div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>모델</th>
                      <th>파라미터</th>
                      <th>민감도</th>
                      <th>특이도</th>
                      <th>AUC</th>
                      <th>FN</th>
                      <th>비고</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayModels.map((m) => (
                      <tr key={m.name} className={m.ensemble ? 'row-highlight' : ''}>
                        <td>{m.name}{m.ensemble && <span className="badge">앙상블</span>}</td>
                        <td>{m.params}</td>
                        <td>{m.sensitivity}%</td>
                        <td>{m.specificity}%</td>
                        <td>{m.auc.toFixed(3)}</td>
                        <td>{m.fn}</td>
                        <td className="note-cell">{m.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </motion.div>
              <p className="insight-box">
                <strong>핵심 발견:</strong> 단일 모델 중 민감도·특이도 목표(≥98%, ≥85%)를 동시에 달성한 모델은 없습니다.
                ViT-Small은 민감도 97.1%이나 특이도 10%로 편향, CLAHE 전처리는 성능을 오히려 저하시켰습니다.
              </p>
            </motion.div>
          </motion.div>
        </motion.div>
      </section>

      <section className="research-section alt-bg" id="process">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>개발 과정 — 3단계</h2>
            <p className="section-desc">환자·측면 단위 성능 변화. MURA 추가와 YOLO 재학습이 단계별로 성능을 끌어올렸습니다.</p>
          </header>
          <motion.div className="timeline">
            {TIMELINE_STEPS.map((s) => (
              <motion.div className="timeline-item" key={s.step}>
                <motion.div className="timeline-marker">{s.step}</motion.div>
                <motion.div className="timeline-body">
                  <h3>{s.title}</h3>
                  <p className="timeline-summary">{s.summary}</p>
                  <p>{s.detail}</p>
                  <p className="timeline-insight">{s.insight}</p>
                  {s.metrics && (
                    <motion.div className="timeline-metrics">
                      <span>민감도 {s.metrics.sensitivity}%</span>
                      <span>특이도 {s.metrics.specificity}%</span>
                      <span>AUC {s.metrics.auc}</span>
                    </motion.div>
                  )}
                </motion.div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      <section className="research-section" id="ensemble">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>앙상블 설계</h2>
            <p className="section-desc">
              상호 보완적 3모델을 가중 합산(2:1:2) ÷ 5 후, 환자·측면 단위 MAX 집계, 임계값 0.652 적용.
            </p>
          </header>
          <motion.div className="ensemble-diagram">
            <motion.div className="flow-node">입력 X-ray</motion.div>
            <motion.div className="flow-arrow">↓</motion.div>
            <motion.div className="flow-row">
              {ENSEMBLE_MODELS.map((m) => (
                <motion.div className="flow-model" key={m.name}>
                  <span className="flow-weight">×{m.weight}</span>
                  {m.name}
                </motion.div>
              ))}
            </motion.div>
            <motion.div className="flow-arrow">가중 합 (2:1:2) / 5 → MAX 집계 → 임계 0.652</motion.div>
            <motion.div className="flow-node result">골절 / 정상</motion.div>
          </motion.div>
          <motion.div className="ensemble-cards">
            {ENSEMBLE_MODELS.map((m) => (
              <motion.div className="ensemble-card" key={m.name}>
                <motion.div className="ensemble-card-head">
                  <h3>{m.name}</h3>
                  <span className="role-badge">{m.role}</span>
                </motion.div>
                <p className="weight-line">가중치 <strong>{m.weight}</strong></p>
                <p className="text-sm"><span className="text-success">강점</span> {m.strength}</p>
                <p className="text-sm"><span className="text-warn">약점</span> {m.weakness}</p>
                <p className="text-sm text-secondary">
                  단일: Sens {m.single.sensitivity}% / Spec {m.single.specificity}% / AUC {m.single.auc}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      <section className="research-section alt-bg" id="performance">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>임상 목표 달성 결과</h2>
            <p className="section-desc">
              절대 정확도(100%)보다 <strong>FN·FP 여부</strong>와 <strong>임상 목표 충족</strong>을 함께 보세요.
              환자·측면 단위(n=15)는 파일럿 Test이며, 이미지 단위(n=55)와 수치가 다릅니다.
            </p>
          </header>
          <motion.div className="unit-toggle">
            <button type="button" className={`toggle-btn ${evalUnit === 'patient' ? 'active' : ''}`} onClick={() => setEvalUnit('patient')}>
              환자·측면 단위 (임상 기준)
            </button>
            <button type="button" className={`toggle-btn ${evalUnit === 'image' ? 'active' : ''}`} onClick={() => setEvalUnit('image')}>
              이미지 단위
            </button>
          </motion.div>
          <p className="unit-desc">{perf.description} · {perf.n}</p>
          {perf.headline && <p className="perf-headline">{perf.headline}</p>}
          <motion.div className="goals-table-wrap">
            <table className="data-table goals-table">
              <thead>
                <tr>
                  <th>지표</th>
                  <th>목표</th>
                  <th>결과</th>
                  <th>95% CI</th>
                  <th>달성</th>
                </tr>
              </thead>
              <tbody>
                {perf.metrics.map((row) => (
                  <tr key={row.name}>
                    <td>{row.name}</td>
                    <td>{row.target}</td>
                    <td>
                      <strong>{row.resultLabel || row.value}</strong>
                      {row.valueDetail && <span className="value-detail"> ({row.valueDetail})</span>}
                    </td>
                    <td className="text-secondary">{row.ci}</td>
                    <td>{row.achieved ? <span className="achieved">✓</span> : <span className="not-achieved">✗</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>
          <PerfVisual perf={perf} evalUnit={evalUnit} />
          {perf.extra && <p className="section-footnote">{perf.extra}</p>}
        </motion.div>
      </section>

      <section className="research-section" id="limitations">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>한계 및 연구 범위</h2>
            <p className="section-desc">방법론적 파일럿 연구로서의 의미를 가지며, 임상 배포를 위해서는 다기관·대규모 외부 검증이 필요합니다.</p>
          </header>
          <ul className="limit-list">
            {LIMITATIONS.map((item) => (
              <li key={item.title}>
                <strong>{item.title}</strong>
                <p>{item.text}</p>
              </li>
            ))}
          </ul>
        </motion.div>
      </section>
    </>
  );
}
'''


def fix_tags(s):
    bad_o = '<' + 'motion.div'
    bad_c = '</' + 'motion.div>'
    return s.replace(bad_o, '<div').replace(bad_c, '</motion.div>').replace('</motion.div>', '</div>')


out = fix_tags(RESEARCH)
(ROOT / 'components' / 'ResearchPage.jsx').write_text(out, encoding='utf-8')
print('written', len(out))
