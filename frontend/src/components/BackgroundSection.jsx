import { useState } from 'react';
import { BACKGROUND } from '../data/backgroundContent';

function DetailBlock({ block }) {
  return (
    <div className="background-detail-block">
      <h4>{block.title}</h4>
      <ul>
        {block.items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function BackgroundSection() {
  const [expanded, setExpanded] = useState(false);
  const { title, summary, cards, details } = BACKGROUND;

  return (
    <section className="research-section alt-bg" id="background">
      <div className="section-inner">
        <header className="section-header left">
          <h2>{title}</h2>
          <p className="section-desc">{summary}</p>
        </header>

        <div className="compare-cards">
          <div className="compare-card problem">
            <h3>{cards.problem.title}</h3>
            <p>{cards.problem.lead}</p>
            <p className="text-sm">{cards.problem.sub}</p>
          </div>
          <div className="compare-card solution">
            <h3>{cards.solution.title}</h3>
            <p>{cards.solution.lead}</p>
            <p className="text-sm">{cards.solution.sub}</p>
          </div>
        </div>

        <div className="background-more-wrap">
          <button
            type="button"
            className="btn btn-secondary background-more-btn"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
          >
            {expanded ? '접기' : '더보기 — 임상·데이터·방법론 상세'}
          </button>

          {expanded && (
            <div className="background-details">
              <DetailBlock block={details.clinical} />
              <DetailBlock block={details.technical} />
              <DetailBlock block={details.data} />
              <DetailBlock block={details.approach} />
              <p className="background-ref text-sm text-secondary">
                참고: 모델설명.md, 단일모델_vs_앙상블.md, 개발보고서(주상골_골절_AI_최종제출)
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
