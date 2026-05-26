/**
 * AI 골절 분석 결과 — 참고 레이아웃(3열) 데모 UI
 */

function IconInfo() {
  return (
    <svg className="ai-fr-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" strokeLinecap="round" />
    </svg>
  );
}

function IconRefresh() {
  return (
    <svg className="ai-fr-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M3 12a9 9 0 019-9 9.75 9.75 0 016.74 2.74L21 8" strokeLinecap="round" />
      <path d="M21 3v5h-5M21 12a9 9 0 01-9 9 9.75 9.75 0 01-6.74-2.74L3 16" strokeLinecap="round" />
      <path d="M3 21v-5h5" strokeLinecap="round" />
    </svg>
  );
}

function IconDownload() {
  return (
    <svg className="ai-fr-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function WristSkeletonFallback({ accent }) {
  return (
    <svg className="ai-fr-diagram ai-fr-detail-fallback-svg" viewBox="0 0 120 140" aria-hidden="true">
      <ellipse cx="60" cy="68" rx="36" ry="24" fill="rgba(148,163,184,0.08)" stroke="rgba(148,163,184,0.35)" strokeWidth="2" />
      <path
        d="M52 132 L54 118 L53 104 L54 94 L61 92 L61 74 L71 74 L72 94 L72 104 L71 118 L72 131"
        fill="none"
        stroke="rgba(148,163,184,0.55)"
        strokeWidth="2.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {accent && (
        <circle cx="76" cy="86" r="11" fill="rgba(255,71,87,0.28)" stroke="rgba(248,113,113,0.95)" strokeWidth="2" />
      )}
    </svg>
  );
}

/** 상세 패널 우측: 업로드 영상을 고정 박스(72×84)에 맞춤 표시 */
function DetailInsetPreview({ src, fractureHighlight }) {
  if (!src) {
    return <WristSkeletonFallback accent={fractureHighlight} />;
  }
  return (
    <div
      className={`ai-fr-detail-thumb ${fractureHighlight ? 'ai-fr-detail-thumb-hot' : ''}`}
      title="업로드한 X-ray 미리보기"
    >
      <img src={src} alt="업로드 X-ray 참고 썸네일" className="ai-fr-detail-thumb-img" loading="lazy" />
    </div>
  );
}

const VIEW_SLOTS = ['정면 (AP)', '측면', '내측 사선', '외측 사선'];

/** 배포 등에서 숫자가 문자열로 올 경우 % 위치가 NaN이 되어 박스가 안 보일 수 있어 정규화 */
function normalizeAttentionRegions(raw) {
  if (!Array.isArray(raw)) return [];
  const out = [];
  for (const r of raw) {
    const x = Number(r?.x);
    const y = Number(r?.y);
    const w = Number(r?.w);
    const h = Number(r?.h);
    if ([x, y, w, h].every((n) => Number.isFinite(n))) {
      out.push({
        x: Math.min(1, Math.max(0, x)),
        y: Math.min(1, Math.max(0, y)),
        w: Math.min(1, Math.max(0, w)),
        h: Math.min(1, Math.max(0, h)),
      });
    }
  }
  return out;
}

export default function DemoAnalysisDashboard({
  loading,
  originalSrc,
  heatmapSrc,
  attentionRegions,
  prediction,
  patientScore,
  imageScore,
  patientId,
  imageCount,
  imageIndex,
  images,
  onThumbSelect,
  onNewAnalysis,
}) {
  const regions = normalizeAttentionRegions(attentionRegions);
  const isFracture = prediction === 'fracture';
  const pct = Math.min(100, Math.max(0, Math.round((patientScore ?? 0) * 100)));
  const imgPctFixed = Math.min(100, Math.max(0, (imageScore ?? 0) * 100)).toFixed(1);
  const hasHeatmap = Boolean(heatmapSrc);
  const showBoxes = isFracture && regions.length > 0;
  const shootDate = new Date().toLocaleDateString('ko-KR');

  const confidenceLabelPct = pct;

  const handleDownloadReport = () => window.print();

  const list = images ?? [];

  return (
    <div className="ai-fracture-result">
      <header className="ai-fr-head">
        <div className="ai-fr-head-left">
          <h2 className="ai-fr-title">AI 골절 분석 결과</h2>
        </div>
        <div className="ai-fr-head-right">
          <p className="ai-fr-mini-disclaimer">
            <span aria-hidden>*</span> 본 결과는 보조적 정보이며, 최종 진단은 의료진이 수행합니다.
          </p>
          <button type="button" className="ai-fr-btn-outline" onClick={onNewAnalysis} disabled={loading}>
            <IconRefresh /> 새 분석
          </button>
        </div>
      </header>

      <div className={`ai-fr-grid ${loading ? 'ai-fr-loading' : ''}`}>
        {loading && (
          <div className="ai-fr-loading-mask">
            <div className="spinner" />
            <span>분석 중…</span>
          </div>
        )}

        <section className="ai-fr-col ai-fr-upload">
          <div className="ai-fr-pane-head">
            <span className="ai-fr-pane-title">업로드한 X-ray</span>
            <span className="ai-fr-info-ico-inline" aria-hidden><IconInfo /></span>
          </div>

          <div className="ai-fr-pane-body ai-fr-pane-dark">
            {originalSrc ? (
              <div className="viewer-image-wrap ai-fr-main-img-wrap">
                <img src={originalSrc} alt="업로드 X-ray" className="ai-fr-main-img" />
                {showBoxes && (
                  <div className="attention-boxes" aria-hidden>
                    {regions.map((r, i) => (
                      <div
                        key={i}
                        className="attention-box fad-box-red"
                        style={{
                          left: `${r.x * 100}%`,
                          top: `${r.y * 100}%`,
                          width: `${r.w * 100}%`,
                          height: `${r.h * 100}%`,
                        }}
                      >
                        <span className="attention-box-label">{i + 1}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="ai-fr-placeholder">영상 없음</p>
            )}
          </div>

          <div className="ai-fr-thumb-row" role="tablist" aria-label="영상 뷰">
            {VIEW_SLOTS.map((lbl, i) => {
              const src = list[i];
              const active = imageCount > 1 ? imageIndex === i : i === 0;
              return (
                <button
                  key={lbl}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={`ai-fr-thumb ${src ? '' : 'ai-fr-thumb-empty'} ${active && src ? 'active' : ''}`}
                  disabled={!src}
                  onClick={() => src && onThumbSelect?.(i)}
                >
                  <span className="ai-fr-thumb-bar" aria-hidden />
                  <span className="ai-fr-thumb-img-wrap">
                    {src ? <img src={src} alt="" /> : null}
                  </span>
                  <span className="ai-fr-thumb-caption">{lbl}</span>
                </button>
              );
            })}
          </div>
        </section>

        <section className="ai-fr-col ai-fr-heatmap">
          <div className="ai-fr-pane-head">
            <span className="ai-fr-pane-title">AI 분석 히트맵</span>
          </div>
          <div className="ai-fr-pane-body ai-fr-pane-dark ai-fr-heatmap-row">
            {hasHeatmap ? (
              <>
                <div className="ai-fr-hm-img-wrap viewer-image-wrap">
                  <img src={heatmapSrc} alt="AI 히트맵" className="ai-fr-main-img" />
                </div>
                <div className="ai-fr-gradient-legend" aria-hidden>
                  <span>높음</span>
                  <div className="ai-fr-gradient-bar" />
                  <span>낮음</span>
                </div>
              </>
            ) : (
              <p className="ai-fr-placeholder">{loading ? '히트맵 생성 중…' : '히트맵 없음'}</p>
            )}
          </div>
          <div className="ai-fr-confidence-block">
            <p className="ai-fr-confidence-heading">AI 분석 신뢰도</p>
            <div className="ai-fr-confidence-num" style={{ color: isFracture ? '#4ade80' : '#94a3b8' }}>
              {loading ? '—' : `${confidenceLabelPct}%`}
            </div>
            <p className="ai-fr-confidence-caption">모델 기반 분석 신뢰도</p>
            <div className="ai-fr-confidence-bar-track">
              <div
                className="ai-fr-confidence-bar-fill"
                style={{
                  width: `${loading ? 0 : confidenceLabelPct}%`,
                  background: isFracture
                    ? 'linear-gradient(90deg, #22c55e, #86efac)'
                    : 'linear-gradient(90deg, #475569, #94a3b8)',
                }}
              />
            </div>
          </div>
        </section>

        <section className="ai-fr-col ai-fr-summary">
          <div className="ai-fr-pane-head">
            <span className="ai-fr-pane-title">분석 결과 요약</span>
          </div>

          <div className={`ai-fr-summary-card ${isFracture ? 'fad-danger' : 'fad-safe'}`}>
            <span className="ai-fr-badge-soft">{isFracture ? '의심 부위 1' : '종합 결과'}</span>
            <div className="ai-fr-summary-inner">
              <div>
                <h3 className="ai-fr-summary-title">{isFracture ? '골절 의심' : '정상 소견'}</h3>
                <p className="ai-fr-summary-desc">
                  {isFracture
                    ? 'AI가 골절 가능성이 높다고 판단한 영역입니다.'
                    : '골절 의심 기준 미만입니다.'}
                </p>
              </div>
              <div className="ai-fr-summary-side">
                <span className="ai-fr-muted-sm">신뢰도(확률)</span>
                <strong className="ai-fr-strong-pct">{pct}%</strong>
              </div>
            </div>
          </div>

          <div className="ai-fr-detail-panel">
            <h4 className="ai-fr-detail-title">{isFracture ? '의심 부위 상세' : '분석 영역 요약'}</h4>
            <div className="ai-fr-detail-row">
              <div className="ai-fr-detail-num">1</div>
              <div className="ai-fr-detail-copy">
                <p className="ai-fr-detail-bone">{isFracture ? '원위 요골 (Distal Radius)' : '손목 (요골·척골 포함)'}</p>

                <p className="ai-fr-mini-label">{isFracture ? '골절 의심 수준' : '현재 점수'}</p>
                <div className="ai-fr-suspicion-bar-track">
                  <div
                    className="ai-fr-suspicion-bar-fill"
                    style={{
                      width: `${loading ? 0 : Math.min(pct, 100)}%`,
                      background: isFracture ? 'linear-gradient(90deg, #f87171, #ef4444)' : 'linear-gradient(90deg, #94a3b8, #64748b)',
                    }}
                  />
                  <span className="ai-fr-bar-pct-tip">{pct}%</span>
                </div>

                <p className="ai-fr-mini-label">설명</p>
                <p className="ai-fr-detail-text">
                  {isFracture
                    ? '원위 요골 관절면 부위에 골절 가능성이 높게 분석되었습니다.'
                    : `현재 이미지에 대한 신뢰도(확률)는 ${pct}% 입니다.`}
                </p>
                <p className="ai-fr-mini-label">위치</p>
                <p className="ai-fr-detail-text">
                  {isFracture ? '원위 요골 관절면 (손목 쪽)' : `신뢰도(본 영상) ${imgPctFixed}% · 손목 X-ray`}
                </p>
              </div>
              <div className="ai-fr-diagram-wrap">
                <DetailInsetPreview src={originalSrc} fractureHighlight={isFracture && showBoxes} />
              </div>
            </div>
          </div>

          <div className="ai-fr-reference">
            <h4 className="ai-fr-detail-title">참고 안내</h4>
            <ul>
              <li>본 분석은 AI 기반 보조 진단 도구입니다.</li>
              <li>실제 진단은 반드시 전문의의 판독을 통해 이루어져야 합니다.</li>
              <li>임상 증상 및 다른 검사 결과와 함께 종합적으로 판단해 주세요.</li>
            </ul>
          </div>
        </section>
      </div>

      <footer className="ai-fr-footer">
        <div className="ai-fr-meta">
          촬영 정보
          <span className="sep">|</span>
          환자 ID : <strong>{patientId || '—'}</strong>
          <span className="sep">|</span>
          촬영일 : {shootDate}
          <span className="sep">|</span>
          부위 : 오른쪽 손목
        </div>
        <div className="ai-fr-footer-actions">
          <button type="button" className="ai-fr-btn-outline" onClick={handleDownloadReport} disabled={loading}>
            <IconDownload /> 보고서 다운로드
          </button>
        </div>
      </footer>
    </div>
  );
}
