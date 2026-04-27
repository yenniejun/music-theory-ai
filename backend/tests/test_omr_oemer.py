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


def test_oemer_happy_path(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    with patch("services.omr._run_streaming", side_effect=_fake_streamer(SAMPLE_XML)):
        out = OemerOMR().image_to_musicxml(b"fake-png-bytes", media_type="image/png")
    assert out == SAMPLE_XML


def test_oemer_missing_binary_raises(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: None)
    with pytest.raises(RuntimeError, match="oemer binary"):
        OemerOMR().image_to_musicxml(b"x")


def test_oemer_pdf_is_converted_to_png(monkeypatch):
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
        OemerOMR().image_to_musicxml(b"PDF-BYTES", media_type="application/pdf")

    assert captured["ext"] == ".png"
    assert captured["bytes"] == b"PNG-BYTES"


def test_oemer_propagates_nonzero_exit(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    with patch("services.omr._run_streaming", side_effect=_fake_streamer(None, returncode=1, output="bad image")):
        with pytest.raises(RuntimeError, match="bad image"):
            OemerOMR().image_to_musicxml(b"x", media_type="image/png")


def test_oemer_handles_no_output_file(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")

    def empty(cmd, timeout):
        return _StreamResult(0, "")

    with patch("services.omr._run_streaming", side_effect=empty):
        with pytest.raises(RuntimeError, match="no MusicXML"):
            OemerOMR().image_to_musicxml(b"x", media_type="image/png")


def test_oemer_timeout_wraps_subprocess_timeout(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")

    def slow(cmd, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout=1)

    with patch("services.omr._run_streaming", side_effect=slow):
        with pytest.raises(RuntimeError, match="timed out"):
            OemerOMR(timeout_seconds=1).image_to_musicxml(b"x", media_type="image/png")


def test_oemer_passes_without_deskew_flag(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    captured_cmd = {}

    def runner(cmd, timeout):
        captured_cmd["cmd"] = cmd
        out_idx = cmd.index("-o") + 1
        Path(cmd[out_idx], "score.musicxml").write_text(SAMPLE_XML)
        return _StreamResult(0, "")

    with patch("services.omr._run_streaming", side_effect=runner):
        OemerOMR(without_deskew=True).image_to_musicxml(b"x", media_type="image/png")

    assert "-d" in captured_cmd["cmd"]
