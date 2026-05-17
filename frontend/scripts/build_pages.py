# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(r"d:\x_rayWeb\frontend\src")

RESEARCH = r'''import { useState } from 'react';
import SensSpecChart from './SensSpecChart';
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
        <div className="hero-content">
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

      <section className="research-section alt-bg" id="background">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>배경 — 왜 어려운가</h2>
            <p className="section-desc">
              주상골 골절은 X-ray에서 골절선이 미세해 초기 진단을 놓치기 쉽습니다.
              치료가 늦어지면 무혈성 괴사로 이어질 수 있어, FN(골절을 정상으로 오판)을 최소화하는 것이 최우선입니다.
            </p>
          </header>
          <motion.div className="compare-cards">
            <motion.div className="compare-card problem">
              <h3>데이터 구조적 한계</h3>
              <p>정상 훈련 레이블 = <strong>골절 환자의 반대손</strong></p>
              <p className="text-sm">실제 건강인 손목 X-ray 학습 경험이 없어, 단일 모델은 정상·골절을 동시에 맞추기 어렵습니다.</p>
            </motion.div>
            <motion.div className="compare-card solution">
              <h3>해결 방향</h3>
              <p>Stanford <strong>MURA v1.1</strong> 정상 손목 350장 추가</p>
              <p className="text-sm">YOLO 정상 평균 골절 확률 0.503 → 0.122 (재학습 후). 이후 3모델 앙상블로 상호 보완.</p>
            </motion.div>
          </motion.div>
        </motion.div>
      </section>

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
            <h2>최종 성능</h2>
            <p className="section-desc">평가 단위에 따라 수치가 달라집니다. 임상 판단과 일치하는 환자·측면 단위를 기준으로 보세요.</p>
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
                    <td><strong>{row.value}</strong></td>
                    <td className="text-secondary">{row.ci}</td>
                    <td>{row.achieved ? <span className="achieved">✓</span> : <span className="not-achieved">✗</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>
          <motion.div className="stats-container">
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.sensitivity}<span className="stat-unit">%</span></motion.div>
              <motion.div className="stat-label">민감도</motion.div>
            </motion.div>
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.specificity}<span className="stat-unit">%</span></motion.div>
              <motion.div className="stat-label">특이도</motion.div>
            </motion.div>
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.auc}</motion.div>
              <motion.div className="stat-label">AUC</motion.div>
            </motion.div>
            <motion.div className="stat-box highlight-box">
              <motion.div className="stat-value">{perf.cards.f1}</motion.div>
              <motion.div className="stat-label">F1-score</motion.div>
            </motion.div>
          </motion.div>
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
    return s.replace(bad_o, '<div').replace(bad_c, '</div>')

(ROOT / 'components' / 'ResearchPage.jsx').write_text(fix_tags(RESEARCH), encoding='utf-8')

DEMO = open(__file__, encoding='utf-8').read().split('DEMO_START')[1].split('DEMO_END')[0] if False else None

# DemoSection + App written inline below
DEMO = r'''
import { useState, useRef } from 'react';

export default function DemoSection({
  fileInputRef, images, results, loading, activeImageIndex, setActiveImageIndex,
  showHeatmap, setShowHeatmap, patientResults, resultsSectionRef, onUploadClick,
}) {
  const hasContent = images.length > 0 || loading;
  return (
    <section className="demo-section" id="demo">
      <motion.div className="section-inner">
        <header className="section-header left">
          <span className="demo-badge">부록</span>
          <h2>연구용 추론 데모</h2>
          <p className="section-desc">
            3모델 앙상블(2:1:2) 추론 파이프라인 체험. <strong>임상 판정 대체 불가</strong>, 주상골 전용.
            백엔드(localhost:9090) 필요.
          </p>
          <p className="pipeline-hint">이미지별 확률 → 환자·측면 MAX 집계 → 임계값 0.652</p>
        </header>
        {!hasContent ? (
          <motion.div className="demo-empty">
            <p>JPEG/PNG X-Ray를 업로드하세요.</p>
            <button type="button" className="btn btn-primary" onClick={onUploadClick}>모델 테스트</button>
          </motion.div>
        ) : (
          <motion.div className="dashboard-section demo-dashboard" ref={resultsSectionRef}>
            <motion.div className="viewer-panel">
              {loading && <motion.div className="loading-overlay"><motion.div className="spinner" /><div>앙상블 분석 중...</motion.div></motion.div>}
              <motion.div className="viewer-toolbar">
                {images.length > 1 && (
                  <>
                    <button type="button" className="tool-btn" disabled={activeImageIndex === 0} onClick={() => setActiveImageIndex(activeImageIndex - 1)}>‹</button>
                    <span className="text-sm">{activeImageIndex + 1}/{images.length}</span>
                    <button type="button" className="tool-btn" disabled={activeImageIndex >= images.length - 1} onClick={() => setActiveImageIndex(activeImageIndex + 1)}>›</button>
                  </>
                )}
                {results[activeImageIndex]?.heatmap_base64 && (
                  <button type="button" className={`tool-btn ${showHeatmap ? 'active-heat' : ''}`} onClick={() => setShowHeatmap(!showHeatmap)}>H</button>
                )}
              </motion.div>
              <motion.div className="viewer-content">
                {(() => {
                  const r = results[activeImageIndex];
                  const src = r ? (showHeatmap && r.heatmap_base64 ? r.heatmap_base64 : r.original_base64) : images[activeImageIndex];
                  return src ? <img src={src} alt="X-Ray" className="uploaded-image" /> : null;
                })()}
              </motion.div>
            </motion.div>
            <motion.div className="analysis-panel">
              <motion.div className="panel-header"><h3>케이스별 결과 (MAX)</h3></motion.div>
              <motion.div className="panel-content">
                {Object.values(patientResults).map((res, idx) => {
                  const frac = res.prediction === 'fracture';
                  const pct = (res.patient_score * 100).toFixed(1);
                  return (
                    <motion.div className="result-card" key={idx}>
                      <motion.div className="result-header">
                        <span>환자 {res.patient_id}</span>
                        <span className={`status-badge ${frac ? 'status-fracture' : 'status-normal'}`}>{frac ? '골절 의심' : '정상'}</span>
                      </motion.div>
                      <motion.div className="prob-container">
                        <motion.div className="prob-label"><span>골절 확률</span><span>{pct}%</span></motion.div>
                        <motion.div className="prob-bar-bg"><motion.div className="prob-bar-fill" style={{ width: pct + '%' }} /></motion.div>
                      </motion.div>
                    </motion.div>
                  );
                })}
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </motion.div>
    </section>
  );
}
'''

APP = r'''
import { useState, useRef } from 'react';
import ResearchPage from './components/ResearchPage';
import DemoSection from './components/DemoSection';
import './index.css';

export default function App() {
  const [images, setImages] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const fileInputRef = useRef(null);
  const resultsSectionRef = useRef(null);

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = async (e) => {
    if (!e.target.files?.length) return;
    const files = Array.from(e.target.files);
    setImages(files.map((f) => URL.createObjectURL(f)));
    setActiveImageIndex(0);
    setResults([]);
    setLoading(true);
    setTimeout(() => resultsSectionRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    try {
      const res = await fetch('http://localhost:9090/api/analyze', { method: 'POST', body: fd });
      const data = await res.json();
      setResults(data.results);
    } catch {
      alert('분석 실패. 백엔드(localhost:9090)를 확인하세요.');
    } finally {
      setLoading(false);
    }
  };

  const patientResults = results.reduce((acc, c) => {
    if (!acc[c.patient_id] || c.patient_score > acc[c.patient_id].patient_score) acc[c.patient_id] = c;
    return acc;
  }, {});

  return (
    <motion.div className="app-container">
      <header className="top-nav">
        <motion.div className="nav-brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} role="button" tabIndex={0}>
          Tri-<span>Scaphoid</span>
        </motion.div>
        <nav className="nav-links">
          <a href="#background">배경</a>
          <a href="#experiments">실험</a>
          <a href="#process">과정</a>
          <a href="#ensemble">앙상블</a>
          <a href="#performance">성능</a>
          <a href="#limitations">한계</a>
          <a href="#demo">데모</a>
        </nav>
        <motion.div className="nav-actions">
          <input ref={fileInputRef} type="file" multiple accept="image/jpeg,image/png" className="hidden-input" onChange={handleFileChange} />
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })}>데모</button>
          <button type="button" className="btn btn-primary" onClick={handleUploadClick}>모델 테스트</button>
        </motion.div>
      </header>
      <main className="landing-container view-enter">
        <ResearchPage />
        <DemoSection
          fileInputRef={fileInputRef}
          images={images}
          results={results}
          loading={loading}
          activeImageIndex={activeImageIndex}
          setActiveImageIndex={setActiveImageIndex}
          showHeatmap={showHeatmap}
          setShowHeatmap={setShowHeatmap}
          patientResults={patientResults}
          resultsSectionRef={resultsSectionRef}
          onUploadClick={handleUploadClick}
        />
        <footer className="footer">
          <motion.div className="footer-content">
            <span className="footer-brand">Tri-Scaphoid · 주상골 골절 X-ray AI 연구</span>
            <span className="text-secondary text-sm">© 2026</span>
          </motion.div>
        </footer>
      </main>
    </motion.div>
  );
}
'''

(ROOT / 'components' / 'DemoSection.jsx').write_text(fix_tags(DEMO), encoding='utf-8')
(ROOT / 'App.jsx').write_text(fix_tags(APP), encoding='utf-8')
print('All pages written')
