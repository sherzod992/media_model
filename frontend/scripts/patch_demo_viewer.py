# -*- coding: utf-8 -*-
from pathlib import Path

demo_path = Path(r'd:\x_rayWeb\frontend\src\components\DemoSection.jsx')
text = demo_path.read_text(encoding='utf-8')

old_start = text.find('            <div className="viewer-panel">')
old_end = text.find('            <div className="analysis-panel">')

new_block = '''            <ImageViewer
              originalSrc={originalSrc}
              heatmapSrc={heatmapSrc}
              loading={loading}
              imageIndex={activeImageIndex}
              imageCount={images.length}
              onPrev={() => setActiveImageIndex(Math.max(0, activeImageIndex - 1))}
              onNext={() => setActiveImageIndex(Math.min(images.length - 1, activeImageIndex + 1))}
              prediction={currentResult?.prediction}
              showNoHeatmapNote={Boolean(currentResult)}
            />
            <div className="analysis-panel">'''

if old_start == -1 or old_end == -1:
    raise SystemExit('markers not found')

if 'import ImageViewer' not in text:
    text = text.replace(
        "import { useState } from 'react';",
        "import ImageViewer from './ImageViewer';",
    )
    if 'import ImageViewer' not in text:
        text = "import ImageViewer from './ImageViewer';\n" + text

text = text[:old_start] + new_block + text[old_end:]
demo_path.write_text(text, encoding='utf-8')
print('DemoSection patched')
