import { useState } from 'react';
import Uploader from './components/Uploader.jsx';
import LayerPanel from './components/LayerPanel.jsx';
import ScoreView from './components/ScoreView.jsx';

const DEFAULT_LAYERS = [
  { id: 'chords',   label: 'Chord symbols',     visible: true,  color: '#0f172a', opacity: 1.0 },
  { id: 'roman',    label: 'Roman numerals',    visible: true,  color: '#7c3aed', opacity: 1.0 },
  { id: 'function', label: 'Harmonic function', visible: false, color: '#3b82f6', opacity: 0.6 },
  { id: 'tritone',  label: 'Tritones',          visible: true,  color: '#f97316', opacity: 1.0 },
  { id: 'motif',    label: 'Motif brackets',    visible: false, color: '#0ea5e9', opacity: 0.9 },
  { id: 'tension',  label: 'Tension curve',     visible: false, color: '#ef4444', opacity: 0.6 },
];

export default function App() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null); // { musicxml, annotations }
  const [layers, setLayers] = useState(DEFAULT_LAYERS);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-tight">ScoreLayer</h1>
          <span className="text-xs text-slate-400">photo → annotated score</span>
        </div>
        <Uploader
          busy={busy}
          setBusy={setBusy}
          onResult={(d) => { setError(null); setData(d); }}
          onError={(msg) => setError(msg)}
        />
      </header>

      {error && (
        <div className="border-b border-red-200 bg-red-50 px-6 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <LayerPanel layers={layers} setLayers={setLayers} />
        <main className="relative flex-1 overflow-auto bg-slate-50">
          <ScoreView
            musicxml={data?.musicxml}
            annotations={data?.annotations}
            layers={layers}
          />
        </main>
      </div>
    </div>
  );
}
