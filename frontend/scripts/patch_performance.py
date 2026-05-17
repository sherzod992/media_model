# -*- coding: utf-8 -*-
from pathlib import Path

path = Path(r'd:\x_rayWeb\frontend\src\components\ResearchPage.jsx')
text = path.read_text(encoding='utf-8')

old = """      <section className="research-section alt-bg" id="performance">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>최종 성능</h2>
            <p className="section-desc">평가 단위에 따라 수치가 달라집니다. 임상 판단과 일치하는 환자·측면 단위를 기준으로 보세요.</p>
          </header>"""

new = """      <section className="research-section alt-bg" id="performance">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>임상 목표 달성 결과</h2>
            <p className="section-desc">
              절대 정확도(100%)보다 <strong>FN·FP 여부</strong>와 <strong>임상 목표 충족</strong>을 함께 보세요.
              환자·측면 단위(n=15)는 파일럿 Test이며, 이미지 단위(n=55)와 수치가 다릅니다.
            </p>
          </header>"""

old = old.replace('<motion.div', '<div').replace('</motion.div>', '</div>')
new = new.replace('<motion.div', '<motion.div').replace('</motion.div>', '</motion.div>')
# fix new
new = new.replace('<motion.div', '<div').replace('</motion.div>', '</div>')

old2 = """          <p className="unit-desc">{perf.description} · {perf.n}</p>
          <motion.div className="goals-table-wrap">"""
old2 = old2.replace('<motion.div', '<div')
new2 = """          <p className="unit-desc">{perf.description} · {perf.n}</p>
          {perf.headline && <p className="perf-headline">{perf.headline}</p>}
          <motion.div className="goals-table-wrap">"""
new2 = new2.replace('<motion.div', '<div')

old3 = """                    <td><strong>{row.value}</strong></td>"""

new3 = """                    <td>
                      <strong>{row.resultLabel || row.value}</strong>
                      {row.valueDetail && <span className="value-detail"> ({row.valueDetail})</span>}
                    </td>"""

old4 = """          <motion.div className="stats-container">
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.sensitivity}<span className="stat-unit">%</span></motion.div>
              <motion.div className="stat-label">민감도</motion.div>
            </motion.div>
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.specificity}<span className="stat-unit">%</span></motion.div>
              <motion.div className="stat-label">특이도</motion.div>
            </motion.div>
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.auc}</motion.div>
              <motion.div className="stat-label">AUC</motion.div>
            </motion.div>
            <motion.div className="stat-box highlight-box">
              <motion.div className="stat-value">{perf.cards.f1}</motion.div>
              <motion.div className="stat-label">F1-score</motion.div>
            </motion.div>
          </motion.div>"""

new4 = """          <motion.div className="stats-container perf-summary">
            {perf.summaryCards.map((card) => (
              <motion.div
                key={card.label}
                className={`stat-box ${card.highlight ? 'highlight-box' : ''} ${card.warn ? 'warn-box' : ''}`}
              >
                <motion.div className="stat-value">
                  {card.value}
                  {card.unit && <span className="stat-unit">{card.unit}</span>}
                </motion.div>
                <motion.div className="stat-label">{card.label}</motion.div>
                {card.sub && <p className="stat-sub">{card.sub}</p>}
              </motion.div>
            ))}
          </motion.div>"""

for o, n in [(old, new), (old2, new2)]:
    o = o.replace('<motion.div', '<motion.div').replace('</motion.div>', '</motion.div>')
    n = n.replace('<motion.div', '<motion.div').replace('</motion.div>', '</motion.div>')

def fix(s):
    return s.replace('<'+'motion.div', '<div').replace('</'+'motion.div>', '</div>')

old = fix("""      <section className="research-section alt-bg" id="performance">
        <div className="section-inner">
          <header className="section-header left">
            <h2>최종 성능</h2>
            <p className="section-desc">평가 단위에 따라 수치가 달라집니다. 임상 판단과 일치하는 환자·측면 단위를 기준으로 보세요.</p>
          </header>""")

new = fix("""      <section className="research-section alt-bg" id="performance">
        <motion.div className="section-inner">
          <header className="section-header left">
            <h2>임상 목표 달성 결과</h2>
            <p className="section-desc">
              절대 정확도(100%)보다 <strong>FN·FP 여부</strong>와 <strong>임상 목표 충족</strong>을 함께 보세요.
              환자·측면 단위(n=15)는 파일럿 Test이며, 이미지 단위(n=55)와 수치가 다릅니다.
            </p>
          </header>""")

new = new.replace('<motion.div', '<div').replace('</motion.div>', '</motion.div>'.replace('motion.',''))

text = text.replace(old, new)

text = text.replace(
    fix("""          <p className="unit-desc">{perf.description} · {perf.n}</p>
          <motion.div className="goals-table-wrap">""").replace('<motion.div className="goals','<div className="goals'),
    fix("""          <p className="unit-desc">{perf.description} · {perf.n}</p>
          {perf.headline && <p className="perf-headline">{perf.headline}</p>}
          <motion.div className="goals-table-wrap">""").replace('<motion.div className="goals','<motion.div className="goals').replace('<motion.div className="goals','<div className="goals')
)

# simpler replacements one by one
text = path.read_text(encoding='utf-8')
text = text.replace('<h2>최종 성능</h2>', '<h2>임상 목표 달성 결과</h2>')
text = text.replace(
    '<p className="section-desc">평가 단위에 따라 수치가 달라집니다. 임상 판단과 일치하는 환자·측면 단위를 기준으로 보세요.</p>',
    '''<p className="section-desc">
              절대 정확도(100%)보다 <strong>FN·FP 여부</strong>와 <strong>임상 목표 충족</strong>을 함께 보세요.
              환자·측면 단위(n=15)는 파일럿 Test이며, 이미지 단위(n=55)와 수치가 다릅니다.
            </p>'''
)
text = text.replace(
    '<p className="unit-desc">{perf.description} · {perf.n}</p>\n          <div className="goals-table-wrap">',
    '<p className="unit-desc">{perf.description} · {perf.n}</p>\n          {perf.headline && <p className="perf-headline">{perf.headline}</p>}\n          <div className="goals-table-wrap">'
)
text = text.replace(
    '<td><strong>{row.value}</strong></td>',
    '''<td>
                      <strong>{row.resultLabel || row.value}</strong>
                      {row.valueDetail && <span className="value-detail"> ({row.valueDetail})</span>}
                    </td>'''
)

stats_old = '''          <motion.div className="stats-container">
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.sensitivity}<span className="stat-unit">%</span></motion.div>
              <motion.div className="stat-label">민감도</motion.div>
            </motion.div>
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.specificity}<span className="stat-unit">%</span></motion.div>
              <motion.div className="stat-label">특이도</motion.div>
            </motion.div>
            <motion.div className="stat-box">
              <motion.div className="stat-value">{perf.cards.auc}</motion.div>
              <motion.div className="stat-label">AUC</motion.div>
            </motion.div>
            <motion.div className="stat-box highlight-box">
              <motion.div className="stat-value">{perf.cards.f1}</motion.div>
              <motion.div className="stat-label">F1-score</motion.div>
            </motion.div>
          </motion.div>'''

stats_old = stats_old.replace('<'+'motion.div', '<div').replace('</'+'motion.div>', '</motion.div>'.replace('motion.',''))

stats_new = '''          <motion.div className="stats-container perf-summary">
            {perf.summaryCards.map((card) => (
              <motion.div
                key={card.label}
                className={`stat-box ${card.highlight ? 'highlight-box' : ''} ${card.warn ? 'warn-box' : ''}`}
              >
                <motion.div className="stat-value">
                  {card.value}
                  {card.unit && <span className="stat-unit">{card.unit}</span>}
                </motion.div>
                <motion.div className="stat-label">{card.label}</motion.div>
                {card.sub && <p className="stat-sub">{card.sub}</p>}
              </motion.div>
            ))}
          </motion.div>'''

stats_new = stats_new.replace('<'+'motion.div', '<div').replace('</'+'motion.div>', '</div>')

text = text.replace(stats_old, stats_new)
path.write_text(text, encoding='utf-8')
print('patched ok')
