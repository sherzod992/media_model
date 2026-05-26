export default function TestSamplePicker({
  samples,
  title,
  description,
  onClose,
  selectedId,
  onSelect,
  onFileUpload,
  loading,
}) {
  const safeSamples = samples ?? [];

  return (
    <div className="test-sample-picker">
      <div className="test-picker-toolbar">
        <button type="button" className="btn btn-secondary btn-sm" onClick={onClose} disabled={loading}>
          ← 시작 화면
        </button>
        <span className="test-picker-mode mode-all">{title}</span>
      </div>
      {description ? <p className="test-category-desc">{description}</p> : null}

      {safeSamples.length === 0 ? (
        <div className="test-samples-empty">
          <p>등록된 X-ray 샘플이 없습니다. 이미지를 직접 업로드해서 앙상블 추론을 실행하세요.</p>
          <label className={`btn btn-primary upload-label${loading ? ' disabled' : ''}`}>
            이미지 업로드 (JPG / PNG)
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.JPG,.JPEG,.PNG"
              style={{ display: 'none' }}
              disabled={loading}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onFileUpload(file);
                e.target.value = '';
              }}
            />
          </label>
        </div>
      ) : (
        <>
          <div className="test-samples-grid">
            {safeSamples.map((sample) => {
              const isSelected = selectedId === sample.id;
              const isFracture = sample.category === 'fracture';
              return (
                <button
                  key={sample.id}
                  type="button"
                  className={`test-sample-card ${isSelected ? 'selected' : ''} ${loading && isSelected ? 'loading' : ''}`}
                  onClick={() => onSelect(sample)}
                  disabled={loading}
                  title={sample.fileName}
                >
                  <div className="test-sample-thumb-wrap">
                    <img src={sample.url} alt={sample.label} className="test-sample-thumb" loading="lazy" />
                    {loading && isSelected && (
                      <div className="test-sample-loading">
                        <div className="spinner" />
                      </div>
                    )}
                  </div>
                  <span className="test-sample-label">{sample.label}</span>
                  <span className={`test-sample-tag ${isFracture ? 'tag-fracture' : 'tag-normal'}`}>
                    {isFracture ? '골절 예시' : '정상 예시'}
                  </span>
                </button>
              );
            })}
          </div>
          <div className="test-samples-upload-row">
            <label className={`btn btn-secondary btn-sm upload-label${loading ? ' disabled' : ''}`}>
              또는 이미지 업로드 (JPG / PNG)
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.JPG,.JPEG,.PNG"
                style={{ display: 'none' }}
                disabled={loading}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onFileUpload(file);
                  e.target.value = '';
                }}
              />
            </label>
          </div>
        </>
      )}

      <p className="test-samples-hint">썸네일을 누르면 해당 이미지에 대해 바로 앙상블 추론이 실행됩니다.</p>
    </div>
  );
}
