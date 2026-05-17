import { CLINICAL_TARGETS, SINGLE_MODELS } from '../data/researchData';

const PAD = { left: 52, right: 24, top: 24, bottom: 48 };
const W = 520;
const H = 360;

function scale(v, min, max, size) {
  return PAD.left + ((v - min) / (max - min)) * size;
}

export default function SensSpecChart() {
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const xMin = 0;
  const xMax = 100;
  const yMin = 0;
  const yMax = 100;

  const sx = (v) => scale(v, xMin, xMax, plotW);
  const sy = (v) => H - PAD.bottom - scale(v, yMin, yMax, plotH);

  const targetX = sx(CLINICAL_TARGETS.specificity);
  const targetY = sy(CLINICAL_TARGETS.sensitivity);

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="sens-spec-chart" role="img" aria-label="민감도-특이도 산점도">
        <rect x={PAD.left} y={PAD.top} width={plotW} height={plotH} fill="rgba(255,255,255,0.02)" rx="4" />
        {/* Target region */}
        <rect
          x={targetX}
          y={PAD.top}
          width={PAD.left + plotW - targetX}
          height={targetY - PAD.top}
          fill="rgba(0,200,83,0.06)"
          stroke="rgba(0,200,83,0.25)"
          strokeDasharray="4 4"
        />
        <text x={targetX + 8} y={PAD.top + 16} fill="var(--success-green)" fontSize="10">
          목표 영역 (Spec≥85%, Sens≥98%)
        </text>
        {/* Grid */}
        {[0, 25, 50, 75, 100].map((t) => (
          <g key={t}>
            <line x1={sx(t)} y1={PAD.top} x2={sx(t)} y2={H - PAD.bottom} stroke="rgba(255,255,255,0.06)" />
            <line x1={PAD.left} y1={sy(t)} x2={PAD.left + plotW} y2={sy(t)} stroke="rgba(255,255,255,0.06)" />
            <text x={sx(t)} y={H - 12} textAnchor="middle" fill="var(--text-secondary)" fontSize="10">{t}</text>
            <text x={14} y={sy(t) + 4} textAnchor="middle" fill="var(--text-secondary)" fontSize="10">{t}</text>
          </g>
        ))}
        <text x={W / 2} y={H - 4} textAnchor="middle" fill="var(--text-secondary)" fontSize="11">
          특이도 Specificity (%)
        </text>
        <text
          x={14}
          y={H / 2}
          textAnchor="middle"
          fill="var(--text-secondary)"
          fontSize="11"
          transform={`rotate(-90, 14, ${H / 2})`}
        >
          민감도 Sensitivity (%)
        </text>
        {/* Points */}
        {SINGLE_MODELS.map((m) => (
          <g key={m.name}>
            <circle
              cx={sx(m.specificity)}
              cy={sy(m.sensitivity)}
              r={m.ensemble ? 7 : 5}
              fill={m.ensemble ? 'var(--accent-cyan)' : 'rgba(148,163,184,0.5)'}
              stroke={m.ensemble ? '#fff' : 'transparent'}
              strokeWidth={m.ensemble ? 1.5 : 0}
            />
            {m.ensemble && (
              <text x={sx(m.specificity) + 10} y={sy(m.sensitivity) + 4} fill="var(--text-primary)" fontSize="9">
                {m.name.split('-')[0]}
              </text>
            )}
          </g>
        ))}
        {/* Final ensemble patient-level point */}
        <circle cx={sx(100)} cy={sy(100)} r={9} fill="var(--success-green)" stroke="#fff" strokeWidth="2" />
        <text x={sx(100) - 4} y={sy(100) - 14} textAnchor="end" fill="var(--success-green)" fontSize="10" fontWeight="600">
          앙상블(환자·측면)
        </text>
      </svg>
      <p className="chart-caption">이미지 단위 Test(n=55). 단일 모델은 목표 영역에 진입하지 못함.</p>
    </div>
  );
}
