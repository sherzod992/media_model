import DemoAnalysisDashboard from './DemoAnalysisDashboard';
import TestSamplePicker from './TestSamplePicker';
import { ALL_TEST_SAMPLES } from '../data/testSamples';

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
  onCloseDemo,
  selectedSample,
  onSelectSample,
  onFileUpload,
  images,
  results,
  loading,
  activeImageIndex,
  setActiveImageIndex,
  resultsSectionRef,
  onOpenDemo,
  onNewAnalysis = () => {},
}) {
  const hasResults = images.length > 0 || loading;
  const cases = groupByCase(results);
  const currentResult = results[activeImageIndex];
  const primaryCase = cases[0];

  const originalSrc = currentResult?.original_base64 ?? images[activeImageIndex];
  const heatmapSrc = currentResult?.heatmap_base64;
  const attentionRegions = currentResult?.attention_regions;
  const thumbSources = images.length > 0 ? images : originalSrc ? [originalSrc] : [];
  const imageScore = currentResult?.image_score ?? primaryCase?.images?.[0]?.image_score;

  return (
    <section className="demo-section" id="demo">
      <div className="section-inner">
        <header className="section-header left">
          <span className="demo-badge">체험</span>
          <h2>연구용 추론 데모</h2>
          <p className="section-desc">
            X-ray 이미지를 업로드해 3모델 앙상블(2:1:2)을 체험합니다.
            <strong> 임상 판정 대체 불가</strong>, 주상골 전용.
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

        {demoOpen && (
          <TestSamplePicker
            samples={ALL_TEST_SAMPLES}
            title="전체 샘플"
            description="정상 예시와 골절 예시를 한 화면에서 선택합니다."
            onClose={onCloseDemo}
            selectedId={selectedSample?.id}
            onSelect={onSelectSample}
            onFileUpload={onFileUpload}
            loading={loading}
          />
        )}

        {hasResults && (
          <div className="demo-results-block demo-results-ai-board" ref={resultsSectionRef}>
            <DemoAnalysisDashboard
              loading={loading}
              originalSrc={originalSrc}
              heatmapSrc={heatmapSrc}
              attentionRegions={attentionRegions}
              prediction={currentResult?.prediction ?? primaryCase?.prediction}
              patientScore={primaryCase?.patient_score ?? currentResult?.patient_score}
              imageScore={imageScore}
              patientId={String(currentResult?.patient_id ?? primaryCase?.patient_id ?? '—')}
              imageCount={Math.max(thumbSources.length, 1)}
              imageIndex={Math.min(activeImageIndex, Math.max(thumbSources.length - 1, 0))}
              images={thumbSources}
              onThumbSelect={setActiveImageIndex}
              onNewAnalysis={onNewAnalysis}
            />
          </div>
        )}
      </div>
    </section>
  );
}
