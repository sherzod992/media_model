# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(r'd:\x_rayWeb\frontend\src\components\ResearchPage.jsx')
t = p.read_text(encoding='utf-8', errors='replace')

marker = 'className="stats-container perf-summary"'
start = t.find(marker)
if start == -1:
    raise SystemExit('marker not found')
start = t.rfind('\n', 0, start) + 1

end = t.find('{perf.extra &&', start)
if end == -1:
    raise SystemExit('end not found')

replacement = '          <PerfVisual perf={perf} evalUnit={evalUnit} />\n'
t = t[:start] + replacement + t[end:]
p.write_text(t, encoding='utf-8')
print('patched')
