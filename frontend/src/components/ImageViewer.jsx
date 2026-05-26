import { useState, useRef, useCallback, useEffect } from 'react';

function ViewerPane({ label, src, caption, heat, placeholder, regions, showRegions }) {
  const imgRef = useRef(null);
  const [boxStyle, setBoxStyle] = useState(null);

  // object-fit:contain 레터박스 오프셋을 계산해 박스 컨테이너를 실제 이미지 위에 정렬
  const computeBoxStyle = useCallback(() => {
    const img = imgRef.current;
    if (!img || !img.complete || !img.naturalWidth) return;
    const iw = img.offsetWidth;
    const ih = img.offsetHeight;
    const nw = img.naturalWidth;
    const nh = img.naturalHeight;
    if (!iw || !ih) return;
    const scale = Math.min(iw / nw, ih / nh);
    const rw = nw * scale;
    const rh = nh * scale;
    // viewer-pane-image 는 inset:12px 이므로 +12 보정
    setBoxStyle({
      left: (iw - rw) / 2 + 12,
      top: (ih - rh) / 2 + 12,
      width: rw,
      height: rh,
    });
  }, []);

  // 창 크기 변경 시 재계산
  useEffect(() => {
    window.addEventListener('resize', computeBoxStyle);
    return () => window.removeEventListener('resize', computeBoxStyle);
  }, [computeBoxStyle]);

  return (
    <div className="viewer-pane">
      <p className="viewer-pane-label">{label}</p>
      <div className={`viewer-pane-body ${heat ? 'viewer-pane-body-heat' : ''} ${placeholder ? 'viewer-pane-muted' : ''}`}>
        {src ? (
          <>
            <img
              ref={imgRef}
              src={src}
              alt={label}
              className="viewer-pane-image"
              onLoadStart={() => setBoxStyle(null)}
              onLoad={computeBoxStyle}
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
  /** 골절 의심이고 서버에서 영역 좌표가 오면 표시 (알람 임계값과 표시 로직 불일치 방지) */
  const showBoxes = isFracture && (attentionRegions?.length ?? 0) > 0;

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
            regions={attentionRegions}
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
          {showBoxes && ` 골절 확률 ${Math.round((patientScore ?? 0) * 100)}% — 원본 위 네모는 주의가 높은 구간의 추정 범위입니다.`}
          {!showBoxes && isFracture && ' 원본에 관심 영역(네모) 좌표가 없습니다.'}
        </p>
      )}
    </div>
  );
}
