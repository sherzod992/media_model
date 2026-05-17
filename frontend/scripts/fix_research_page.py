# -*- coding: utf-8 -*-
path = r'd:\x_rayWeb\frontend\src\components\ResearchPage.jsx'

CONTENT = r'''import { useState } from 'react';
import SensSpecChart from './SensSpecChart';
import {
  SINGLE_MODELS,
  TIMELINE_STEPS,
  ENSEMBLE_MODELS,
  PERFORMANCE_BY_UNIT,
  LIMITATIONS,
} from '../data/researchData';

export default function ResearchPage() {
  const [evalUnit, setEvalUnit] = useState('patient');
  const [showAllModels, setShowAllModels] = useState(false);
  const perf = PERFORMANCE_BY_UNIT[evalUnit];
  const displayModels = showAllModels
    ? SINGLE_MODELS
    : SINGLE_MODELS.filter((m) => m.ensemble || m.name.includes('ViT') || m.name.includes('CLAHE'));

  return (
    <>
      <section className="hero-section" id="hero">
        <motion.div className="hero-content">
          <p className="hero-eyebrow">PLACEHOLDER</p>
        </motion.div>
      </section>
    </>
  );
}
'''

# Fix placeholders - write full file properly
open(path, 'w', encoding='utf-8').write(CONTENT.replace('motion.div', 'motion.div').replace('<motion.div', '<div').replace('</motion.div>', '</div>'))
