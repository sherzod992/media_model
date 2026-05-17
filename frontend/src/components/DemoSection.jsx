import ImageViewer from './ImageViewer';
import DemoCategoryLauncher from './DemoCategoryLauncher';
import TestSamplePicker from './TestSamplePicker';

function fileNameFromPath(filePath) {
  if (!filePath) return '—';
  const parts = filePath.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] || filePath;
}

function caseLabel(patientId, index) {
  if (/^\d{8}$/.test(patientId)) return `케이스 ${patientId}`;
  if (/^\d{8}/.test(patientId)) return `케이스 ${patientId.slice(0, 8)}`;
  return `테스트 케이스 #${index + 1}`;
}

function groupByCase(results) {
  const map = {};
  results.forEach((r) => {
    if (!map[r.patient_id]) {
      map[r.patient_id] = {
        patient_id: r.patient_id,
        patient_score: r.patient_score,
        prediction: r.prediction,
        threshold: r.threshold,
        images: [],
      };
    }
    map[r.patient_id].images.push(r);
  });
  return Object.values(map);
}

export default function DemoSection({
  demoOpen,
  category,
  onSelectCategory,
  onBackCategory,
  selectedSample,
  onSelectSample,
  images,
  results,
  loading,
  activeImageIndex,
  setActiveImageIndex,
  resultsSectionRef,
  onOpenDemo,
}) {
  const hasResults = images.length > 0 || loading;
  const cases = groupByCase(results);
  const currentResult = results[activeImageIndex];
  const originalSrc = currentResult?.original_base64 ?? images[activeImageIndex];
  const heatmapSrc = currentResult?.heatmap_base64;
  const attentionRegions = currentResult?.attention_regions;
  const expectedFracture = category === 'fracture';

  return (
    <section className="demo-section" id="demo">
      <div className="section-inner">
        <header className="section-header left">
          <span className="demo-badge">부록</span>
          <h2>연구용 추론 데모</h2>
          <p className="section-desc">
            미리 준비한 X-ray 샘플로 3모델 앙상블(2:1:2)을 체험합니다.
            <strong> 임상 판정 대체 불가</strong>, 주상골 전용. 백엔드(localhost:9090) 필요.
          </p>
        </header>

        {!demoOpen && (
          <div className="demo-idle">
            <p>정상·골절 X-ray 샘플로 앙상블 추론을 체험할 수 있습니다.</p>
            <button type="button" className="btn btn-primary btn-lg" onClick={onOpenDemo}>
              모델 테스트
            </button>
          </div>
        )}

        {demoOpen && !category && (
          <DemoCategoryLauncher onSelect={onSelectCategory} loading={loading} />
        )}

        {demoOpen && category && (
          <TestSamplePicker
            category={category}
            onBack={onBackCategory}
            selectedId={selectedSample?.id}
            onSelect={onSelectSample}
            loading={loading}
          />
        )}

        {hasResults && (
          <div className="demo-results-block" ref={resultsSectionRef}>
            {selectedSample && (
              <p className="demo-selected-name">
                <span className="demo-selected-type">
                  {expectedFracture ? '골절 테스트' : '정상 테스트'}
                </span>
                · {selectedSample.label}
              </p>
            )}
            <div className="dashboard-section demo-dashboard">
              <div className="demo-dashboard-main">
                <ImageViewer
                  originalSrc={originalSrc}
                  heatmapSrc={heatmapSrc}
                  attentionRegions={attentionRegions}
                  loading={loading}
                  imageIndex={activeImageIndex}
                  imageCount={images.length}
                  onPrev={() => setActiveImageIndex(Math.max(0, activeImageIndex - 1))}
                  onNext={() => setActiveImageIndex(Math.min(images.length - 1, activeImageIndex + 1))}
                  prediction={currentResult?.prediction}
                  showNoHeatmapNote={Boolean(currentResult)}
                />
                <div className="analysis-panel">
                  <div className="panel-header">
                    <h3>추론 결과</h3>
                    <p className="text-sm text-secondary">이미지 1장 기준 · 환자 ID는 파일명에서 추출</p>
                  </div>
                  <div className="panel-content">
                    {loading && cases.length === 0 && (
                      <p className="text-secondary text-center">결과를 계산하는 중입니다...</p>
                    )}
                    {!loading && cases.length === 0 && (
                      <p className="text-secondary text-center">결과가 없습니다.</p>
                    )}
                    {cases.map((caseItem, idx) => {
                      const isFracture = caseItem.prediction === 'fracture';
                      const casePct = (caseItem.patient_score * 100).toFixed(1);
                      const threshPct = (caseItem.threshold * 100).toFixed(1);
                      const thresh = caseItem.threshold;
                      const displayFile = selectedSample?.fileName ?? fileNameFromPath(caseItem.images[0]?.file);
                      const mismatch = expectedFracture !== isFracture;

                      return (
                        <div className="result-card result-card-v2" key={caseItem.patient_id}>
                          <div className="result-card-top">
                            <div>
                              <div className="case-title">{caseLabel(caseItem.patient_id, idx)}</div>
                              <div className="case-filename" title={displayFile}>{displayFile}</div>
                            </div>
                            <span className={`status-badge ${isFracture ? 'status-fracture' : 'status-normal'}`}>
                              {isFracture ? '골절 의심' : '정상 소견'}
                            </span>
                          </div>

                          {mismatch && (
                            <p className="result-expect-note">
                              {expectedFracture
                                ? '골절 테스트 샘플이지만 모델은 정상 소견입니다. 반대손·특정 방향 X-ray는 정상으로 나올 수 있습니다.'
                                : '정상 테스트 샘플이지만 모델은 골절 의심입니다.'}
                            </p>
                          )}

                          <div className="result-metric-block">
                            <div className="prob-label">
                              <span>골절 확률</span>
                              <span className="font-medium">{casePct}%</span>
                            </div>
                            <div className="prob-bar-wrap">
                              <div className="prob-bar-bg">
                                <div
                                  className="prob-bar-fill"
                                  style={{
                                    width: `${casePct}%`,
                                    backgroundColor: isFracture ? 'var(--warning-amber)' : 'var(--success-green)',
                                  }}
                                />
                                <div
                                  className="threshold-marker"
                                  style={{ left: `${threshPct}%` }}
                                  title={`임계값 ${threshPct}%`}
                                />
                              </div>
                            </div>
                            <p className="threshold-hint">
                              임계값 {threshPct}%
                              {caseItem.patient_score >= thresh ? ' 이상 → 골절 의심' : ' 미만 → 정상 소견'}
                            </p>
                          </div>

                          <div className="result-meta-row">
                            <span>이 이미지 확률</span>
                            <span>{(caseItem.images[0]?.image_score * 100).toFixed(1)}%</span>
                          </div>

                          <p className="result-disclaimer">
                            연구용 추론 결과이며, 임상 최종 판정을 대체하지 않습니다.
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
