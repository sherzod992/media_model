import { useState, useRef, useCallback } from 'react';
import ResearchPage from './components/ResearchPage';
import DemoSection from './components/DemoSection';
import './index.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:9090';

export default function App() {
  const [demoOpen, setDemoOpen] = useState(false);
  const [category, setCategory] = useState(null);
  const [selectedSample, setSelectedSample] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const resultsSectionRef = useRef(null);

  const openDemo = () => {
    setDemoOpen(true);
    setCategory(null);
    setSelectedSample(null);
    setPreviewUrl(null);
    setResults([]);
    setActiveImageIndex(0);
    setTimeout(() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' }), 50);
  };

  const handleSelectCategory = (cat) => {
    setCategory(cat);
    setSelectedSample(null);
    setPreviewUrl(null);
    setResults([]);
    setActiveImageIndex(0);
  };

  const handleBackCategory = () => {
    setCategory(null);
    setSelectedSample(null);
    setPreviewUrl(null);
    setResults([]);
    setActiveImageIndex(0);
  };

  const sendToApi = useCallback(async (formData) => {
    const apiRes = await fetch(`${API_BASE}/api/analyze`, { method: 'POST', body: formData });
    if (!apiRes.ok) throw new Error('analyze failed');
    const data = await apiRes.json();
    setResults(data.results ?? []);
  }, []);

  const runAnalysis = useCallback(async (sample) => {
    if (!sample || loading) return;

    setSelectedSample(sample);
    setPreviewUrl(sample.url);
    setActiveImageIndex(0);
    setResults([]);
    setLoading(true);

    setTimeout(() => resultsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 120);

    try {
      const res = await fetch(sample.url);
      const blob = await res.blob();
      const file = new File([blob], sample.fileName, { type: blob.type || 'image/jpeg' });
      const fd = new FormData();
      fd.append('files', file);
      await sendToApi(fd);
    } catch {
      alert('분석 실패. 백엔드 서버를 확인하세요.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [loading, sendToApi]);

  const handleFileUpload = useCallback(async (file) => {
    if (!file || loading) return;

    const objectUrl = URL.createObjectURL(file);
    setSelectedSample({ id: 'upload', label: file.name, fileName: file.name, url: objectUrl });
    setPreviewUrl(objectUrl);
    setActiveImageIndex(0);
    setResults([]);
    setLoading(true);

    setTimeout(() => resultsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 120);

    try {
      const fd = new FormData();
      fd.append('files', file);
      await sendToApi(fd);
    } catch {
      alert('분석 실패. 백엔드 서버를 확인하세요.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [loading, sendToApi]);

  const previewImages = previewUrl ? [previewUrl] : [];

  return (
    <div className="app-container">
      <header className="top-nav">
        <div className="nav-brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} role="button" tabIndex={0}>
          <span>Tri-<span>Scaphoid</span></span>
        </div>
        <nav className="nav-links">
          <a href="#background">배경</a>
          <a href="#experiments">실험</a>
          <a href="#process">과정</a>
          <a href="#ensemble">앙상블</a>
          <a href="#performance">성능</a>
          <a href="#limitations">한계</a>
          <a href="#demo">데모</a>
        </nav>
        <div className="nav-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={openDemo}>
            데모
          </button>
          <button type="button" className="btn btn-primary" onClick={openDemo}>
            모델 테스트
          </button>
        </div>
      </header>
      <main className="landing-container view-enter">
        <ResearchPage />
        <DemoSection
          demoOpen={demoOpen}
          category={category}
          onSelectCategory={handleSelectCategory}
          onBackCategory={handleBackCategory}
          selectedSample={selectedSample}
          onSelectSample={runAnalysis}
          onFileUpload={handleFileUpload}
          images={previewImages}
          results={results}
          loading={loading}
          activeImageIndex={activeImageIndex}
          setActiveImageIndex={setActiveImageIndex}
          resultsSectionRef={resultsSectionRef}
          onOpenDemo={openDemo}
        />
        <footer className="footer">
          <div className="footer-content">
            <span className="footer-brand">Tri-Scaphoid · 주상골 골절 X-ray AI 연구</span>
            <span className="text-secondary text-sm">© 2026</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
