/**
 * The six toggleable overlay layers, drawn as SVG groups positioned in the
 * Verovio coordinate space (so they share the score's viewBox).
 */

const FUNCTION_FILL = {
  tonic: '#3b82f6',
  dominant: '#ef4444',
  subdominant: '#10b981',
};

export function ChordSymbolsLayer({ events, layer, onPick }) {
  if (!layer.visible) return null;
  return (
    <g opacity={layer.opacity} fill={layer.color} fontSize="320" fontWeight="600">
      {events.map((e, i) =>
        e.x != null && e.chord ? (
          <text
            key={`cs-${i}`}
            x={e.x}
            y={e.y - 600}
            textAnchor="middle"
            className="anno"
            onClick={() => onPick({ kind: 'chord', event: e })}
          >
            {e.chord}
          </text>
        ) : null
      )}
    </g>
  );
}

export function RomanNumeralsLayer({ events, layer, onPick }) {
  if (!layer.visible) return null;
  return (
    <g opacity={layer.opacity} fill={layer.color} fontSize="280" fontStyle="italic">
      {events.map((e, i) =>
        e.x != null && e.roman ? (
          <text
            key={`rn-${i}`}
            x={e.x}
            y={e.y + 1400}
            textAnchor="middle"
            className="anno"
            onClick={() => onPick({ kind: 'roman', event: e })}
          >
            {e.roman}
          </text>
        ) : null
      )}
    </g>
  );
}

export function HarmonicFunctionLayer({ events, layer, onPick }) {
  if (!layer.visible) return null;
  return (
    <g opacity={layer.opacity}>
      {events.map((e, i) => {
        if (e.x == null) return null;
        const fill = FUNCTION_FILL[e.function];
        if (!fill) return null;
        return (
          <circle
            key={`fn-${i}`}
            cx={e.x}
            cy={e.y}
            r="180"
            fill={fill}
            className="anno"
            onClick={() => onPick({ kind: 'function', event: e })}
          />
        );
      })}
    </g>
  );
}

export function TritoneLayer({ events, layer, onPick }) {
  if (!layer.visible) return null;
  return (
    <g opacity={layer.opacity} stroke={layer.color} fill={layer.color} strokeWidth="20">
      {events.map((e, i) => {
        if (!e.tritone?.present || e.x == null) return null;
        const x = e.x;
        const y = e.y - 1200;
        return (
          <g key={`tt-${i}`} className="anno" onClick={() => onPick({ kind: 'tritone', event: e })}>
            <path
              d={`M ${x - 280} ${y} L ${x - 280} ${y - 240} L ${x + 280} ${y - 240} L ${x + 280} ${y}`}
              fill="none"
            />
            <text x={x} y={y - 320} textAnchor="middle" fontSize="180" fontStyle="italic" stroke="none">
              ♭5
            </text>
          </g>
        );
      })}
    </g>
  );
}

export function MotifLayer({ events, layer, onPick }) {
  if (!layer.visible) return null;
  // Group consecutive events sharing the same motif label into one bracket.
  const groups = [];
  let current = null;
  for (const e of events) {
    if (e.motif && e.x != null) {
      if (current && current.label === e.motif) current.events.push(e);
      else {
        if (current) groups.push(current);
        current = { label: e.motif, events: [e] };
      }
    } else if (current) {
      groups.push(current);
      current = null;
    }
  }
  if (current) groups.push(current);

  return (
    <g opacity={layer.opacity} stroke={layer.color} fill={layer.color}>
      {groups.map((g, i) => {
        const xs = g.events.map((e) => e.x);
        const x1 = Math.min(...xs) - 200;
        const x2 = Math.max(...xs) + 200;
        const y = Math.min(...g.events.map((e) => e.y)) - 1800;
        return (
          <g key={`mo-${i}`} className="anno" onClick={() => onPick({ kind: 'motif', event: g.events[0] })}>
            <path d={`M ${x1} ${y + 240} L ${x1} ${y} L ${x2} ${y} L ${x2} ${y + 240}`}
                  fill="none" strokeWidth="20" />
            <text x={(x1 + x2) / 2} y={y - 80} textAnchor="middle" fontSize="200" stroke="none">
              {g.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}

export function TensionLayer({ events, layer, viewBox }) {
  if (!layer.visible) return null;
  const points = events.filter((e) => e.x != null);
  if (points.length < 2) return null;
  const yBase = viewBox?.height ? viewBox.height - 800 : 6000;
  const yScale = 1200;
  const path = points
    .map((e, i) => `${i === 0 ? 'M' : 'L'} ${e.x} ${yBase - e.tension * yScale}`)
    .join(' ');
  const fillPath =
    `M ${points[0].x} ${yBase} ` +
    points.map((e) => `L ${e.x} ${yBase - e.tension * yScale}`).join(' ') +
    ` L ${points.at(-1).x} ${yBase} Z`;
  return (
    <g opacity={layer.opacity}>
      <path d={fillPath} fill={layer.color} opacity="0.25" />
      <path d={path} fill="none" stroke={layer.color} strokeWidth="30" />
    </g>
  );
}
