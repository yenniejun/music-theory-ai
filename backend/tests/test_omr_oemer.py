"""Unit tests for OemerOMR. Subprocess is mocked so no model download or GPU needed."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from services.omr import OemerOMR, _StreamResult


SAMPLE_XML = '<?xml version="1.0"?><score-partwise version="4.0"></score-partwise>'


def _fake_streamer(write_to: str, returncode: int = 0, output: str = ""):
    def runner(cmd, timeout):
        out_idx = cmd.index("-o") + 1
        out_dir = Path(cmd[out_idx])
        if write_to is not None:
            (out_dir / "score.musicxml").write_text(write_to)
        return _StreamResult(returncode, output)

    return runner


def test_oemer_happy_path(monkeypatch, tmp_path):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    with patch("services.omr._run_streaming", side_effect=_fake_streamer(SAMPLE_XML)):
        out = OemerOMR(max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(b"fake-png-bytes", media_type="image/png")
    assert out == SAMPLE_XML


def test_oemer_missing_binary_raises(monkeypatch, tmp_path):
    monkeypatch.setattr("services.omr._find_executable", lambda name: None)
    with pytest.raises(RuntimeError, match="oemer binary"):
        OemerOMR(max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(b"x")


def test_oemer_pdf_is_converted_to_png(monkeypatch, tmp_path):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    monkeypatch.setattr("services.omr._pdf_to_png_bytes", lambda b, **kw: b"PNG-BYTES")

    captured = {}

    def runner(cmd, timeout):
        out_idx = cmd.index("-o") + 1
        out_dir = Path(cmd[out_idx])
        img_path = Path(cmd[1])
        captured["ext"] = img_path.suffix
        captured["bytes"] = img_path.read_bytes()
        (out_dir / "score.musicxml").write_text(SAMPLE_XML)
        return _StreamResult(0, "")

    with patch("services.omr._run_streaming", side_effect=runner):
        OemerOMR(max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(b"PDF-BYTES", media_type="application/pdf")

    assert captured["ext"] == ".png"
    assert captured["bytes"] == b"PNG-BYTES"


def test_oemer_propagates_nonzero_exit(monkeypatch, tmp_path):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    with patch("services.omr._run_streaming", side_effect=_fake_streamer(None, returncode=1, output="bad image")):
        with pytest.raises(RuntimeError, match="bad image"):
            OemerOMR(max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(b"x", media_type="image/png")


def test_oemer_handles_no_output_file(monkeypatch, tmp_path):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")

    def empty(cmd, timeout):
        return _StreamResult(0, "")

    with patch("services.omr._run_streaming", side_effect=empty):
        with pytest.raises(RuntimeError, match="no MusicXML"):
            OemerOMR(max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(b"x", media_type="image/png")


def test_oemer_timeout_wraps_subprocess_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")

    def slow(cmd, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout=1)

    with patch("services.omr._run_streaming", side_effect=slow):
        with pytest.raises(RuntimeError, match="timed out"):
            OemerOMR(timeout_seconds=1, max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(b"x", media_type="image/png")


def test_oemer_cache_hit_skips_oemer(monkeypatch, tmp_path):
    """If the cached MusicXML for this content hash already exists, oemer is not invoked."""
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    import hashlib
    digest = hashlib.sha256(b"fake-png-bytes").hexdigest()[:16]
    (tmp_path / f"{digest}.musicxml").write_text(SAMPLE_XML)

    called = {"count": 0}

    def should_not_run(cmd, timeout):
        called["count"] += 1
        return _StreamResult(0, "")

    with patch("services.omr._run_streaming", side_effect=should_not_run):
        out = OemerOMR(max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(
            b"fake-png-bytes", media_type="image/png"
        )
    assert out == SAMPLE_XML
    assert called["count"] == 0  # oemer was never invoked


def test_oemer_writes_cache_after_run(monkeypatch, tmp_path):
    """A successful run persists the MusicXML by content hash for next time."""
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    with patch("services.omr._run_streaming", side_effect=_fake_streamer(SAMPLE_XML)):
        OemerOMR(max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(
            b"fake-png-bytes", media_type="image/png"
        )

    import hashlib
    digest = hashlib.sha256(b"fake-png-bytes").hexdigest()[:16]
    cached = tmp_path / f"{digest}.musicxml"
    assert cached.exists()
    assert cached.read_text() == SAMPLE_XML


def test_stage_progress_maps_known_markers():
    from services.omr import _stage_progress
    assert _stage_progress("2026-01-01 Extracting staffline and symbols") == 0
    assert _stage_progress("Extracting layers of different symbols") == 50
    assert _stage_progress("Extracting noteheads") == 90
    assert _stage_progress("Build MusicXML") == 98
    assert _stage_progress("random unrelated line") is None


def test_oemer_passes_save_cache_flag(monkeypatch, tmp_path):
    """The --save-cache flag is passed to oemer so its inference pickles persist."""
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    captured = {}

    def runner(cmd, timeout):
        captured["cmd"] = cmd
        out_idx = cmd.index("-o") + 1
        Path(cmd[out_idx], "score.musicxml").write_text(SAMPLE_XML)
        return _StreamResult(0, "")

    with patch("services.omr._run_streaming", side_effect=runner):
        OemerOMR(max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(
            b"fake-png-bytes", media_type="image/png"
        )

    assert "--save-cache" in captured["cmd"]


def test_downscale_resizes_when_above_max_dim():
    """A 4000x3000 image should be downscaled below max_dim."""
    from io import BytesIO
    from PIL import Image
    from services.omr import _downscale_png

    big = Image.new("RGB", (4000, 3000), color="white")
    buf = BytesIO()
    big.save(buf, format="PNG")
    out = _downscale_png(buf.getvalue(), max_dim=2000)

    result = Image.open(BytesIO(out))
    assert max(result.size) == 2000
    assert result.size == (2000, 1500)


def test_downscale_passthrough_when_below_max_dim():
    from io import BytesIO
    from PIL import Image
    from services.omr import _downscale_png

    small = Image.new("RGB", (1000, 800), color="white")
    buf = BytesIO()
    small.save(buf, format="PNG")
    raw = buf.getvalue()
    out = _downscale_png(raw, max_dim=2000)
    assert out is raw  # no resize, original bytes returned


def test_oemer_passes_without_deskew_flag(monkeypatch, tmp_path):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    captured_cmd = {}

    def runner(cmd, timeout):
        captured_cmd["cmd"] = cmd
        out_idx = cmd.index("-o") + 1
        Path(cmd[out_idx], "score.musicxml").write_text(SAMPLE_XML)
        return _StreamResult(0, "")

    with patch("services.omr._run_streaming", side_effect=runner):
        OemerOMR(without_deskew=True, max_dim=0, cache_dir=str(tmp_path)).image_to_musicxml(b"x", media_type="image/png")

    assert "-d" in captured_cmd["cmd"]
