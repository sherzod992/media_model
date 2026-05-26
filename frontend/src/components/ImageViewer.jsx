import { useState, useRef, useCallback, useEffect, useLayoutEffect } from 'react';

function ViewerPane({ label, src, caption, heat, placeholder, regions, showRegions }) {
  const imgRef = useRef(null);
  const [boxStyle, setBoxStyle] = useState(null);

  // object-fit:contain 기준으로 실제 그려진 비트맵 영역(레터박스 제외)에 오버레이 맞춤
  const computeBoxStyle = useCallback(() => {
    const img = imgRef.current;
    if (!img || !img.complete || !img.naturalWidth) return;
    const iw = img.clientWidth;
    const ih = img.clientHeight;
    const nw = img.naturalWidth;
    const nh = img.naturalHeight;
    if (!iw || !ih) return;
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

  // 이미지 캐시 완료·결과 지연 도착·flex 리사이즈 때 onLoad만으로는 boxStyle이 비는 경우 방지
  useLayoutEffect(() => {
    if (!showRegions || !regions?.length || !src) return;
    const img = imgRef.current;
    if (!img) return;

    const parent = img.offsetParent;
    let ro;
    if (typeof ResizeObserver !== 'undefined' && parent) {
      ro = new ResizeObserver(() => computeBoxStyle());
      ro.observe(parent);
    }

    computeBoxStyle();
    if (!img.complete) {
      const onLoad = () => computeBoxStyle();
      img.addEventListener('load', onLoad);
      return () => {
        img.removeEventListener('load', onLoad);
        ro?.disconnect();
      };
    }
    return () => ro?.disconnect();
  }, [showRegions, regions, src, computeBoxStyle]);
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
  const regions = Array.isArray(attentionRegions) ? attentionRegions : [];
  const showBoxes = isFracture && regions.length > 0;

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
          {showBoxes && ` 골절 확률 ${Math.round((patientScore ?? 0) * 100)}% — 원본 위 네모는 주의가 높은 구간의 추정 범위입니다.`}
          {!showBoxes && isFracture && ' 원본에 관심 영역(네모) 좌표가 없습니다.'}
        </p>
      )}
    </div>
  );
}
