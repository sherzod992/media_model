# -*- coding: utf-8 -*-
from pathlib import Path

path = Path(r'd:\x_rayWeb\frontend\src\components\DemoSection.jsx')
text = path.read_text(encoding='utf-8')

# Remove H toggle block
text = text.replace(
    """                {results[activeImageIndex]?.heatmap_base64 && (
                  <button
                    type="button"
                    className={`tool-btn ${showHeatmap ? 'active-heat' : ''}`}
                    onClick={() => setShowHeatmap(!showHeatmap)}
                    title="히트맵"
                  >
                    H
                  </button>
                )}
""",
    '',
)

start = text.find('              <div className="viewer-content">')
end = text.find('            <motion.div className="analysis-panel">')
if start == -1:
    start = text.find('              <motion.div className="viewer-content">')
end_div = text.find('            <div className="analysis-panel">')
if end == -1:
    end = end_div

if start == -1 or end == -1:
    raise SystemExit(f'not found start={start} end={end}')

new_block = """              <div className={`viewer-content ${heatmapSrc ? 'viewer-split' : 'viewer-single'}`}>
                <div className="viewer-pane">
                  <p className="viewer-pane-label">원본 X-ray</p>
                  <div className="viewer-pane-body">
                    {originalSrc ? (
                      <img src={originalSrc} alt="원본 X-ray" className="viewer-pane-image" />
                    ) : (
                      <p className="viewer-pane-empty">이미지 없음</p>
                    )}
                  </div>
                </div>
                {heatmapSrc ? (
                  <div className="viewer-pane">
                    <p className="viewer-pane-label">AI 주의 영역 (Grad-CAM)</p>
                    <motion.div className="viewer-pane-body viewer-pane-body-heat">
                      <img src={heatmapSrc} alt="AI 주의 영역" className="viewer-pane-image" />
                    </motion.div>
                    <p className="viewer-pane-caption">
                      진한 색 = 골절 판정에 참고한 영역. 골절 위치 확정이 아닙니다. (DenseNet/EfficientNet)
                    </p>
                  </motion.div>
                ) : (
                  !loading &&
                  currentResult && (
                    <motion.div className="viewer-pane viewer-pane-muted">
                      <p className="viewer-pane-label">AI 주의 영역</p>
                      <motion.div className="viewer-pane-body viewer-pane-placeholder">
                        <p>이 이미지는 Grad-CAM이 생성되지 않았습니다.</p>
                      </motion.div>
                    </motion.div>
                  )
                )}
              </motion.div>
              {currentResult && heatmapSrc && (
                <p className="viewer-footnote">
                  붉은/주황 영역은 AI가 골절 점수를 계산할 때 주목한 픽셀입니다. 임상 병변 위치와 일치하지 않을 수 있습니다.
                </p>
              )}
            </motion.div>
            """

new_block = new_block.replace('<'+'motion.div', '<div').replace('</'+'motion.div>', '</div>')

text = text[:start] + new_block + text[end:]
path.write_text(text, encoding='utf-8')
print('done')
