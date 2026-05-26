/**
 * frontend/test_xray/{normal,fracture}/ 아래 이미지를 빌드 시 자동 등록합니다.
 * 새 사진 추가 후 dev 서버 재시작(또는 HMR)이 필요할 수 있습니다.
 */
const modules = import.meta.glob('../test_samples/**/*.{jpg,jpeg,png,JPG,JPEG,PNG}', {
  eager: true,
  query: '?url',
  import: 'default',
});

function fileName(path) {
  return path.split(/[/\\]/).pop();
}

function categorize(path) {
  const p = path.replace(/\\/g, '/').toLowerCase();
  if (p.includes('/normal/')) return 'normal';
  if (p.includes('/fracture/') || p.includes('/abnormal/')) return 'fracture';
  return null;
}

function buildList(category) {
  return Object.entries(modules)
    .map(([path, url]) => ({ path, url, category: categorize(path) }))
    .filter((item) => item.category === category)
    .sort((a, b) => fileName(a.path).localeCompare(fileName(b.path), 'ko'))
    .map((item, index) => ({
      id: `${category}-${index}-${fileName(item.path)}`,
      url: item.url,
      fileName: fileName(item.path),
      label: `테스트 ${index + 1}`,
      category,
    }));
}

export const TEST_SAMPLES = {
  normal: buildList('normal'),
  fracture: buildList('fracture'),
};

/** 데모에서 정상·골절 샘플을 한 화면에 나열할 때 사용 (정상 먼저, 파일명 순) */
export const ALL_TEST_SAMPLES = [...TEST_SAMPLES.normal, ...TEST_SAMPLES.fracture];