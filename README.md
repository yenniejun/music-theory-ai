# ScoreLayer

Upload a photo of sheet music, get back an annotated score with toggleable
analysis layers — chord symbols, Roman numerals, harmonic-function color coding,
tritone highlights, motif brackets, and a tension curve.

```
photo  →  Oemer (OMR)  →  MusicXML  →  music21 (analysis)  →  annotations JSON
                                                                       │
              Verovio (browser-side render) ───── SVG overlays ────────┘
```

## Stack
- **Frontend:** React + Vite + Tailwind, [Verovio](https://www.verovio.org/) WASM toolkit for score rendering
- **Backend:** Python FastAPI
- **OMR:** [Oemer](https://github.com/BreezeWhite/oemer) (default). Audiveris and Claude Vision adapters live behind the same interface in `backend/services/omr.py`
- **Analysis:** [music21](https://www.music21.org/)

## Quick start

### Backend
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload   # http://127.0.0.1:8000
```

First Oemer call downloads ONNX model weights (one-time, a few hundred MB).

### Frontend
```bash
cd frontend
npm install
npm run dev                            # http://127.0.0.1:5173
```

The Vite dev server proxies `/api/*` to the backend on `:8000`, so just open
the frontend URL.

## API
| Method | Path | Body | Response |
|---|---|---|---|
| `GET`  | `/health`      | – | `{"status":"ok"}` |
| `POST` | `/analyze`     | multipart `file` (png/jpg) | `{ musicxml, annotations[] }` |
| `POST` | `/analyze-xml` | `{ musicxml }` | `{ musicxml, annotations[] }` (skips OMR — handy for tests) |

### Annotation event shape
```jsonc
{
  "measure": 3,
  "beat": 1.0,
  "chord": "G7",
  "roman": "V7",
  "function": "dominant",
  "tritone": { "present": true, "notes": ["B4", "F5"], "label": "tritone — tension wants resolution" },
  "motif": "motif-A",
  "tension": 0.62,
  "note_ids": ["m-1.1.s0.n1"]
}
```

## Layers
Each layer in the left panel has a toggle, color picker, and opacity slider:
1. **Chord symbols** — chord name above each onset (e.g. `G7`)
2. **Roman numerals** — function-relative label below the staff (e.g. `V7`)
3. **Harmonic function** — color-coded noteheads: tonic = blue, dominant = red, subdominant = green
4. **Tritones** — orange bracket connecting the two tritone notes with a `♭5` label
5. **Motif brackets** — colored bracket spanning recurring melodic/rhythmic cells
6. **Tension curve** — semi-transparent dissonance graph along the bottom of the score

Click any annotation in the score to see an explanation tooltip
(e.g. *"Tritone — diabolus in musica..."*).

## Swapping the OMR engine

Set `OMR_PROVIDER` in `backend/.env`:

| Value | Engine | Notes |
|---|---|---|
| `oemer` *(default)* | Pure-Python deep-learning OMR | `pip install oemer`. No JVM. |
| `audiveris` | Java-based FOSS OMR (gold-standard accuracy) | Needs `audiveris` on PATH (or via Docker) |
| `claude` | Claude Vision LLM | Set `ANTHROPIC_API_KEY`. Useful for benchmarking; LLMs are not great at music notation. |

All three implement the same interface in `backend/services/omr.py`:
```python
provider.image_to_musicxml(image_bytes: bytes, media_type: str) -> str
```

## Tests

```bash
cd backend
.venv/bin/pytest                    # unit tests (no network, no models)
.venv/bin/pytest -k integration -s  # full Oemer pipeline against fixture images
```

Drop sheet-music images (`.png` / `.jpg`) into
`backend/tests/fixtures/sheet_music/` and the integration test will pick them
up automatically. Integration tests are skipped unless the `oemer` binary is
on PATH.

Currently: **25 unit tests** covering analyzer logic (key detection, Roman
numerals, function classification, tritone detection, tension scoring, motif
labeling), the OMR text-cleaner, and the Oemer subprocess adapter (with a
mocked binary).

## Project layout
```
backend/
  main.py                       # FastAPI app
  services/
    omr.py                      # OMR providers (Oemer | Audiveris | Claude)
    analyzer.py                 # music21-based analysis → annotation events
  tests/
    test_analyzer.py            # unit tests for analyzer
    test_omr_extractor.py       # unit tests for OMR text cleanup
    test_omr_oemer.py           # unit tests for Oemer adapter (mocked subprocess)
    test_integration_omr.py     # live Oemer + music21 against image fixtures
    fixtures/
      c_major_cadence.musicxml  # I-IV-V7-I — used by analyzer tests
      motif_melody.musicxml     # repeated 4-note cell
      sheet_music/              # drop your own PNG/JPG here
frontend/
  src/
    App.jsx                     # split layout, layer state
    api.js                      # POST /api/analyze
    hooks/useVerovio.js         # WASM toolkit + note-id → bbox map
    components/
      Uploader.jsx
      LayerPanel.jsx            # toggle / color / opacity per layer
      ScoreView.jsx             # Verovio SVG + overlay <svg>
      Tooltip.jsx               # click-to-explain
      overlays/
        anchorEvents.js         # event → score coordinate
        Overlays.jsx            # the 6 layers as SVG components
```
