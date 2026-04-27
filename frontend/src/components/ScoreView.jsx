import { useEffect, useMemo, useRef, useState } from 'react';
import { useVerovio } from '../hooks/useVerovio.js';
import { anchorEvents } from './overlays/anchorEvents.js';
import {
  ChordSymbolsLayer,
  RomanNumeralsLayer,
  HarmonicFunctionLayer,
  TritoneLayer,
  MotifLayer,
  TensionLayer,
} from './overlays/Overlays.jsx';
import Tooltip from './Tooltip.jsx';

export default function ScoreView({ musicxml, annotations, layers }) {
  const { svg, noteMap, error } = useVerovio(musicxml);
  const [pick, setPick] = useState(null);
  const containerRef = useRef(null);
  const [viewBox, setViewBox] = useState(null);

  useEffect(() => {
    if (!containerRef.current || !svg) return;
    const svgEl = containerRef.current.querySelector('svg');
    if (svgEl) {
      const vb = svgEl.getAttribute('viewBox');
      if (vb) {
        const [x, y, w, h] = vb.split(/\s+/).map(Number);
        setViewBox({ x, y, width: w, height: h });
      }
    }
  }, [svg]);

  const events = useMemo(
    () => anchorEvents(annotations || [], noteMap),
    [annotations, noteMap]
  );

  const byId = (id) => layers.find((l) => l.id === id);

  if (error) {
    return <div className="p-6 text-red-600">Verovio error: {error}</div>;
  }

  if (!musicxml) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        Upload a sheet-music image to begin.
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col">
      <div ref={containerRef} className="score-svg relative flex-1 overflow-auto p-6">
        {/* Verovio SVG (the score itself) */}
        <div dangerouslySetInnerHTML={{ __html: svg }} />

        {/* Overlays layered as a sibling SVG with the same viewBox */}
        {viewBox && (
          <svg
            className="pointer-events-none absolute left-6 top-6"
            style={{ width: 'calc(100% - 3rem)' }}
            viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
          >
            <g style={{ pointerEvents: 'auto' }}>
              <HarmonicFunctionLayer events={events} layer={byId('function')} onPick={setPick} />
              <ChordSymbolsLayer events={events} layer={byId('chords')} onPick={setPick} />
              <RomanNumeralsLayer events={events} layer={byId('roman')} onPick={setPick} />
              <TritoneLayer events={events} layer={byId('tritone')} onPick={setPick} />
              <MotifLayer events={events} layer={byId('motif')} onPick={setPick} />
              <TensionLayer events={events} layer={byId('tension')} viewBox={viewBox} />
            </g>
          </svg>
        )}
      </div>
      <Tooltip pick={pick} onClose={() => setPick(null)} />
    </div>
  );
}
