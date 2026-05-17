export default function DemoCategoryLauncher({ onSelect, loading }) {
  return (
    <div className="demo-launcher">
      <p className="demo-launcher-title">테스트할 유형을 선택하세요</p>
      <div className="demo-launcher-buttons">
        <button
          type="button"
          className="demo-launcher-btn demo-launcher-normal"
          onClick={() => onSelect('normal')}
          disabled={loading}
        >
          <span className="demo-launcher-icon">✓</span>
          <span className="demo-launcher-label">정상 테스트</span>
          <span className="demo-launcher-sub">정상 소견 예상 샘플</span>
        </button>
        <button
          type="button"
          className="demo-launcher-btn demo-launcher-fracture"
          onClick={() => onSelect('fracture')}
          disabled={loading}
        >
          <span className="demo-launcher-icon">!</span>
          <span className="demo-launcher-label">골절 테스트</span>
          <span className="demo-launcher-sub">골절 의심 예상 샘플</span>
        </button>
      </div>
    </div>
  );
}
