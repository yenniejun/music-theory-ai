import { useRef, useState } from 'react';
import { analyzeImage } from '../api.js';

export default function Uploader({ onResult, onError, busy, setBusy }) {
  const inputRef = useRef(null);
  const [filename, setFilename] = useState('');

  async function handleFile(file) {
    if (!file) return;
    setFilename(file.name);
    setBusy(true);
    try {
      const data = await analyzeImage(file);
      onResult(data);
    } catch (e) {
      onError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/jpg,application/pdf"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {busy ? 'Analyzing…' : 'Upload sheet music'}
      </button>
      {filename && <span className="truncate text-sm text-slate-500">{filename}</span>}
    </div>
  );
}
