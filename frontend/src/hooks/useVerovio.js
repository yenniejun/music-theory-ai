import { useEffect, useRef, useState } from 'react';

let toolkitPromise = null;

function loadToolkit() {
  if (!toolkitPromise) {
    toolkitPromise = import('verovio/wasm').then(async ({ default: createVerovioModule }) => {
      const VerovioToolkit = (await import('verovio/esm')).VerovioToolkit;
      const VerovioModule = await createVerovioModule();
      return new VerovioToolkit(VerovioModule);
    });
  }
  return toolkitPromise;
}

/**
 * Renders MusicXML via Verovio. Returns SVG markup plus per-note metadata
 * keyed by note xml:id (which the overlays use to anchor annotations).
 */
export function useVerovio(musicxml) {
  const [svg, setSvg] = useState('');
  const [noteMap, setNoteMap] = useState({});
  const [error, setError] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    if (!musicxml) {
      setSvg('');
      setNoteMap({});
      return;
    }

    (async () => {
      try {
        const tk = await loadToolkit();
        tk.setOptions({
          pageWidth: 2000,
          pageHeight: 60000,
          scale: 40,
          adjustPageHeight: true,
          breaks: 'auto',
          svgViewBox: true,
          svgAdditionalAttribute: ['note@pname', 'note@oct'],
        });
        tk.loadData(musicxml);
        const out = tk.renderToSVG(1);
        if (cancelled) return;
        setSvg(out);
        setNoteMap(buildNoteMap(out));
      } catch (e) {
        console.error(e);
        if (!cancelled) setError(e.message || String(e));
      }
    })();

    return () => { cancelled = true; };
  }, [musicxml]);

  return { svg, noteMap, error, containerRef };
}

/**
 * Parse the rendered SVG to build a map of note id -> {x, y, width, measure}.
 * Verovio assigns xml:ids to <g class="note"> elements; we read their bbox
 * positions so overlays can anchor in score coordinates.
 */
function buildNoteMap(svgString) {
  const map = {};
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgString, 'image/svg+xml');

  const notes = doc.querySelectorAll('g.note');
  notes.forEach((g) => {
    const id = g.getAttribute('id');
    if (!id) return;
    const head = g.querySelector('.notehead, use');
    const x = head ? Number(head.getAttribute('x') ?? 0) : 0;
    const y = head ? Number(head.getAttribute('y') ?? 0) : 0;
    const measureEl = g.closest('g.measure');
    const measureN = measureEl ? Number(measureEl.getAttribute('data-n') || measureEl.getAttribute('id')) : null;
    map[id] = { x, y, measure: measureN };
  });

  return map;
}
