export default function LayerPanel({ layers, setLayers }) {
  function update(id, patch) {
    setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, ...patch } : l)));
  }

  return (
    <aside className="flex h-full w-72 flex-col gap-3 border-r border-slate-200 bg-white p-4">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Layers</h2>
      <ul className="flex flex-col gap-2">
        {layers.map((layer) => (
          <li key={layer.id} className="rounded-md border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
                <input
                  type="checkbox"
                  checked={layer.visible}
                  onChange={(e) => update(layer.id, { visible: e.target.checked })}
                />
                {layer.label}
              </label>
              <input
                type="color"
                value={layer.color}
                onChange={(e) => update(layer.id, { color: e.target.value })}
                className="h-6 w-8 cursor-pointer border-0 bg-transparent p-0"
                title="Layer color"
              />
            </div>
            <div className="mt-2 flex items-center gap-2">
              <span className="w-12 text-xs text-slate-500">Opacity</span>
              <input
                type="range" min="0" max="1" step="0.05"
                value={layer.opacity}
                onChange={(e) => update(layer.id, { opacity: Number(e.target.value) })}
                className="flex-1"
              />
              <span className="w-8 text-right text-xs tabular-nums text-slate-500">
                {Math.round(layer.opacity * 100)}%
              </span>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
