export async function analyzeImage(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/api/analyze', { method: 'POST', body: fd });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}
