import { useState, useCallback, useEffect } from 'react';

const BOX_THRESHOLD = 0.60;

function ViewerPane({ label, src, caption, heat, placeholder, regions, showRegions }) {
  const [boxStyle, setBoxStyle] = useState(null);

  const handleLoad = useCallback((e) => {
    const img = e.currentTarget;
    const iw = img.offsetWidth;
    const ih = img.offsetHeight;
    const nw = img.naturalWidth;
    const nh = img.naturalHeight;
    if (!iw || !ih || !nw || !nh) return;
    const scale = Math.min(iw / nw, ih / nh);
    const rw = nw * scale;
    const rh = nh * scale;
    setBoxStyle({
      left: img.offsetLeft + (iw - rw) / 2,
      top: img.offsetTop + (ih - rh) / 2,
      width: rw,
      height: rh,
    });
  }, []);

  useEffect(() => {
    const onResize = () => setBoxStyle(null); // 리사이즈 시 재계산 대기
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return (
    <div className="viewer-pane">
      <p className="viewer-pane-label">{label}</p>
      <div className={`viewer-pane-body ${heat ? 'viewer-pane-body-heat' : ''} ${placeholder ? 'viewer-pane-muted' : ''}`}>
        {src ? (
          <>
            {/* key={src} 로 src 변경 시 img 재마운트 → onLoad 항상 발생 보장 */}
            <img
              key={src}
              src={src}
              alt={label}
              className="viewer-pane-image"
              onLoad={handleLoad}
            />
            {showRegions && regions?.length > 0 && boxStyle && (
              <div
                className="attention-boxes"
                style={{
                  position: 'absolute',
                  inset: 'unset',
                  left: `${boxStyle.left}px`,
                  top: `${boxStyle.top}px`,
                  width: `${boxStyle.width}px`,
                  height: `${boxStyle.height}px`,
                }}
                aria-hidden="true"
              >
                {regions.map((r, i) => (
                  <div
                    key={i}
                    className="attention-box"
                    style={{
                      left: `${r.x * 100}%`,
                      top: `${r.y * 100}%`,
                      width: `${r.w * 100}%`,
                      height: `${r.h * 100}%`,
                    }}
                    title={`AI 주의 영역 ${i + 1} (활성도 ${Math.round(r.score * 100)}%)`}
                  >
                    <span className="attention-box-label">{i + 1}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="viewer-pane-placeholder">{placeholder}</p>
        )}
      </div>
      {caption && (
        <p className="viewer-pane-caption">진한 색 = 골절 판정 참고 영역 (DenseNet/EfficientNet)</p>
      )}
      {showRegions && regions?.length > 0 && (
        <p className="viewer-pane-caption viewer-pane-caption-warn">
          네모는 Grad-CAM 기반 추정 영역이며, 골절 위치를 확정하지 않습니다.
        </p>
      )}
    </div>
  );
}

export default function ImageViewer({
  originalSrc,
  heatmapSrc,
  attentionRegions,
  loading,
  imageIndex,
  imageCount,
  onPrev,
  onNext,
  prediction,
  patientScore,
  showNoHeatmapNote,
}) {
  const hasHeatmap = Boolean(heatmapSrc);
  const isFracture = prediction === 'fracture';
  const regions = Array.isArray(attentionRegions) ? attentionRegions : [];
  const showBoxes = isFracture && (patientScore ?? 0) >= BOX_THRESHOLD && regions.length > 0;

  return (
    <div className="viewer-panel">
      {loading && (
        <div className="loading-overlay">
          <div className="spinner" />
          <div>앙상블 분석 중...</div>
        </div>
      )}

      <div className="viewer-toolbar">
        {imageCount > 1 && (
          <>
            <button type="button" className="tool-btn" disabled={imageIndex === 0} onClick={onPrev} aria-label="이전">
              ‹
            </button>
            <span className="viewer-nav-label">{imageIndex + 1} / {imageCount}</span>
            <button
              type="button"
              className="tool-btn"
              disabled={imageIndex >= imageCount - 1}
              onClick={onNext}
              aria-label="다음"
            >
              ›
            </button>
          </>
        )}
        {prediction && (
          <span className={`viewer-status-chip ${isFracture ? 'chip-warn' : 'chip-ok'}`}>
            {isFracture ? '골절 의심' : '정상 소견'}
          </span>
        )}
      </div>

      {originalSrc ? (
        <div className="viewer-content viewer-split">
          <ViewerPane
            label="원본 X-ray"
            src={originalSrc}
            regions={regions}
            showRegions={showBoxes}
          />
          {hasHeatmap ? (
            <ViewerPane label="AI 주의 영역" src={heatmapSrc} caption heat />
          ) : (
            <ViewerPane
              label="AI 주의 영역"
              placeholder={loading ? '분석 중…' : 'Grad-CAM 미생성'}
            />
          )}
        </div>
      ) : (
        !loading && <p className="viewer-stage-empty">이미지를 불러올 수 없습니다.</p>
      )}

      {showNoHeatmapNote && !hasHeatmap && originalSrc && !loading && (
        <p className="viewer-footnote viewer-no-heatmap-inline">
          AI 주의 영역(Grad-CAM)이 이 이미지에서는 생성되지 않았습니다.
        </p>
      )}

      {hasHeatmap && (
        <p className="viewer-footnote">
          AI 주의 영역은 골절 위치가 아니라, 모델이 참고한 픽셀 분포입니다.
          {showBoxes && ` 골절 확률 ${Math.round((patientScore ?? 0) * 100)}% — 원본 위 네모는 Grad-CAM 기반 의심 영역입니다.`}
          {isFracture && !showBoxes && (patientScore ?? 0) < BOX_THRESHOLD && (patientScore ?? 0) > 0 &&
            ` 골절 확률 ${Math.round((patientScore ?? 0) * 100)}% — 의심 영역 표시는 ${BOX_THRESHOLD * 100}% 이상에서 활성화됩니다.`}
        </p>
      )}
    </div>
  );
}
