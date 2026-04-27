/**
 * Best-effort: pair each annotation event to a position in the rendered SVG.
 *
 * Verovio assigns xml:ids to each <note>, but the analyzer chordifies events
 * by (measure, beat). When the analyzer can't supply note IDs we fall back
 * to: find the first note in the matching measure whose anchor x is closest
 * to (beat-1) / beats-per-measure across the measure's width.
 */
export function anchorEvents(events, noteMap) {
  const noteEntries = Object.entries(noteMap);
  const byMeasure = noteEntries.reduce((acc, [id, info]) => {
    const m = info.measure;
    (acc[m] = acc[m] || []).push({ id, ...info });
    return acc;
  }, {});

  return events.map((ev) => {
    if (ev.note_ids?.length) {
      const target = noteMap[ev.note_ids[0]];
      if (target) return { ...ev, x: target.x, y: target.y };
    }
    const inMeasure = byMeasure[ev.measure];
    if (!inMeasure?.length) return { ...ev, x: null, y: null };
    const sorted = [...inMeasure].sort((a, b) => a.x - b.x);
    const idx = Math.min(sorted.length - 1, Math.max(0, Math.floor(ev.beat - 1)));
    const pick = sorted[idx];
    return { ...ev, x: pick.x, y: pick.y };
  });
}
