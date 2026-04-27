"""Integration test: real images -> Oemer -> music21.

Drop .png/.jpg files into tests/fixtures/sheet_music/ and they are picked
up automatically. Skipped unless the `oemer` binary is on PATH (so the
unit-test run stays fast and offline).

Run only these:
    pytest -k integration -s
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from services import analyzer, omr

FIXTURES = Path(__file__).parent / "fixtures" / "sheet_music"
SUPPORTED = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def _images() -> list[Path]:
    if not FIXTURES.exists():
        return []
    return sorted(p for p in FIXTURES.iterdir() if p.suffix.lower() in SUPPORTED)


pytestmark = pytest.mark.skipif(
    shutil.which("oemer") is None,
    reason="oemer binary not on PATH — skipping live OMR integration tests",
)


@pytest.mark.parametrize("image_path", _images() or [pytest.param(None, marks=pytest.mark.skip(reason="no fixtures"))], ids=lambda p: p.name if p else "none")
def test_omr_then_analyze_produces_annotations(image_path: Path):
    media_type = SUPPORTED[image_path.suffix.lower()]
    musicxml = omr.OemerOMR().image_to_musicxml(image_path.read_bytes(), media_type=media_type)
    assert musicxml.lstrip().startswith("<?xml") or "<score-partwise" in musicxml

    events = analyzer.analyze(musicxml)
    assert isinstance(events, list)
    if events:
        first = events[0]
        for key in ("measure", "beat", "chord", "roman", "function", "tritone", "tension"):
            assert key in first
