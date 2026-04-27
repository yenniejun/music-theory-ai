const COPY = {
  chord: (e) => ({
    title: e.chord || 'Chord',
    body: `Measure ${e.measure}, beat ${e.beat}. The vertical sonority at this onset.`,
  }),
  roman: (e) => ({
    title: `${e.roman} (Roman numeral)`,
    body: `Function: ${e.function}. Roman numerals describe a chord's role in the key, independent of the chord's literal name.`,
  }),
  function: (e) => ({
    title: `${e.function[0].toUpperCase()}${e.function.slice(1)} function`,
    body: {
      tonic: 'Tonic — the home chord, sense of rest and resolution.',
      dominant: 'Dominant — pulls strongly toward tonic. The "tension" in tension-and-release.',
      subdominant: 'Subdominant — moves us away from tonic; sets up the dominant.',
    }[e.function] || 'Other harmonic function.',
  }),
  tritone: (e) => ({
    title: 'Tritone — diabolus in musica',
    body: `Notes ${e.tritone.notes.join(' & ')}. The augmented 4th / diminished 5th, historically the most dissonant interval — it begs to resolve inward by half-step.`,
  }),
  motif: (e) => ({
    title: `Motif: ${e.motif}`,
    body: 'A short melodic/rhythmic cell that recurs across the score. Spotting motifs reveals a composer\'s thematic argument.',
  }),
};

export default function Tooltip({ pick, onClose }) {
  if (!pick) return null;
  const { kind, event } = pick;
  const { title, body } = COPY[kind](event);
  return (
    <div className="absolute right-6 top-6 z-10 max-w-sm rounded-lg border border-slate-200 bg-white p-4 shadow-lg">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700">×</button>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-slate-600">{body}</p>
      <p className="mt-3 text-xs text-slate-400">
        m. {event.measure} · beat {event.beat} · tension {event.tension?.toFixed(2)}
      </p>
    </div>
  );
}
