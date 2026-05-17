function parseTarget(target) {
  const m = String(target).match(/([\d.]+)/);
  return m ? parseFloat(m[1]) : 0;
}

function parseActual(valueDetail, name) {
  if (!valueDetail) return 0;
  if (valueDetail.includes('%')) {
    return parseFloat(valueDetail);
  }
  if (name === 'AUC' || name === 'F1-score') {
    return parseFloat(valueDetail) * 100;
  }
  return parseFloat(valueDetail) || 0;
}

function targetScale(target, name) {
  const t = parseTarget(target);
  if (name === 'AUC' || name === 'F1-score') return t * 100;
  return t;
}

function GoalBar({ metric }) {
  const actual = parseActual(metric.valueDetail, metric.name);
  const target = targetScale(metric.target, metric.name);
  const fill = Math.min(100, (actual / 100) * 100);
  const targetPos = Math.min(100, target);

  return (
    <div className={`perf-goal-row ${metric.achieved ? 'met' : 'miss'}`}>
      <div className="perf-goal-head">
        <span className="perf-goal-name">{metric.name}</span>
        <span className="perf-goal-values">
          <strong>{metric.valueDetail}</strong>
          <span className="perf-goal-target">목표 {metric.target}</span>
        </span>
        <span className={`perf-goal-badge ${metric.achieved ? 'ok' : 'warn'}`}>
          {metric.achieved ? '충족' : '미달'}
        </span>
      </div>
      <div className="perf-goal-track" aria-hidden="true">
        <div
          className="perf-goal-fill"
          style={{ width: `${fill}%` }}
        />
        <div className="perf-goal-marker" style={{ left: `${targetPos}%` }} title={`목표 ${metric.target}`} />
      </div>
      {metric.ci && metric.ci !== '—' && (
        <p className="perf-goal-ci">95% CI {metric.ci}</p>
      )}
    </div>
  );
}

function ErrorCard({ title, count, errorLabel, errorValue, sub, ok }) {
  return (
    <div className={`perf-error-card ${ok ? 'ok' : 'warn'}`}>
      <p className="perf-error-cohort">{title} <span>{count}건</span></p>
      <div className="perf-error-body">
        <span className="perf-error-type">{errorLabel}</span>
        <span className="perf-error-num">{errorValue}</span>
      </div>
      <p className="perf-error-sub">{sub}</p>
    </div>
  );
}

export default function PerfVisual({ perf, evalUnit }) {
  const met = perf.goalsMet ?? perf.metrics.filter((m) => m.achieved).length;
  const total = perf.goalsTotal ?? perf.metrics.length;
  const cohort = perf.cohort;
  const errors = perf.errors;

  return (
    <div className={`perf-visual${errors ? ' has-errors' : ''}`}>
      {errors && cohort?.fracture != null && (
        <div className="perf-panel perf-panel-errors">
          <h3 className="perf-panel-title">임상 오류 (케이스 단위)</h3>
          <p className="perf-panel-desc">골절 미검(FN) · 정상 오판(FP)이 임상적으로 가장 중요한 지표입니다.</p>
          <div className="perf-errors-grid">
            <ErrorCard
              title="골절 환자"
              count={cohort.fracture}
              errorLabel="FN"
              errorValue={errors.fn}
              sub={errors.fn === 0 ? '미검 없음 ✓' : '골절 누락 발생'}
              ok={errors.fn === 0}
            />
            <ErrorCard
              title="정상 케이스"
              count={cohort.normal}
              errorLabel="FP"
              errorValue={errors.fp}
              sub={errors.fp === 0 ? '오판 없음 ✓' : '불필요한 골절 판정'}
              ok={errors.fp === 0}
            />
          </div>
        </div>
      )}

      <div className="perf-panel perf-panel-goals">
        <div className="perf-panel-title-row">
          <h3 className="perf-panel-title">임상 목표 달성</h3>
          <span className={`perf-goals-count ${met === total ? 'all-met' : 'partial'}`}>
            {met}/{total}
          </span>
        </div>
        <div className="perf-goal-pills" role="list">
          {perf.metrics.map((m) => (
            <span key={m.name} className={`perf-goal-pill ${m.achieved ? 'met' : 'miss'}`} role="listitem">
              {m.achieved ? '✓' : '·'} {m.name}
            </span>
          ))}
        </div>
        <div className="perf-goal-bars">
          {perf.metrics.map((m) => (
            <GoalBar key={m.name} metric={m} />
          ))}
        </div>
      </div>

      {cohort && (
        <div className="perf-panel perf-panel-cohort">
          <p className="perf-cohort-label">평가 규모</p>
          <p className="perf-cohort-n">{cohort.total}</p>
          <p className="perf-cohort-unit">{evalUnit === 'patient' ? '케이스' : '이미지'}</p>
          {cohort.fracture != null && (
            <div className="perf-cohort-chips">
              <span className="perf-chip fracture">골절 {cohort.fracture}</span>
              <span className="perf-chip normal">정상 {cohort.normal}</span>
            </div>
          )}
          {evalUnit === 'patient' && (
            <p className="perf-cohort-note">파일럿 Test · 95% CI 넓음</p>
          )}
        </div>
      )}
    </div>
  );
}
