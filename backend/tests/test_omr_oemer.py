"""Unit tests for OemerOMR. Subprocess is mocked so no model download or GPU needed."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from services.omr import OemerOMR


SAMPLE_XML = '<?xml version="1.0"?><score-partwise version="4.0"></score-partwise>'


def _fake_oemer_run(write_to: str):
    """Returns a fake subprocess.run that creates a .musicxml in the -o directory."""

    def runner(cmd, *args, **kwargs):
        out_idx = cmd.index("-o") + 1
        out_dir = Path(cmd[out_idx])
        (out_dir / "score.musicxml").write_text(write_to)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="ok", stderr="")

    return runner


def test_oemer_happy_path(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    with patch("services.omr.subprocess.run", side_effect=_fake_oemer_run(SAMPLE_XML)):
        out = OemerOMR().image_to_musicxml(b"fake-png-bytes", media_type="image/png")
    assert out == SAMPLE_XML


def test_oemer_missing_binary_raises(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: None)
    with pytest.raises(RuntimeError, match="oemer binary"):
        OemerOMR().image_to_musicxml(b"x")


def test_oemer_rejects_pdf(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")
    with pytest.raises(RuntimeError, match="PDF"):
        OemerOMR().image_to_musicxml(b"x", media_type="application/pdf")


def test_oemer_propagates_nonzero_exit(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")

    def fail(cmd, *a, **kw):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="bad image")

    with patch("services.omr.subprocess.run", side_effect=fail):
        with pytest.raises(RuntimeError, match="bad image"):
            OemerOMR().image_to_musicxml(b"x", media_type="image/png")


def test_oemer_handles_no_output_file(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")

    def empty(cmd, *a, **kw):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    with patch("services.omr.subprocess.run", side_effect=empty):
        with pytest.raises(RuntimeError, match="no MusicXML"):
            OemerOMR().image_to_musicxml(b"x", media_type="image/png")


def test_oemer_timeout_wraps_subprocess_timeout(monkeypatch):
    monkeypatch.setattr("services.omr._find_executable", lambda name: "/usr/local/bin/oemer")

    def slow(cmd, *a, **kw):
        raise subprocess.TimeoutExpired(cmd, timeout=1)

    with patch("services.omr.subprocess.run", side_effect=slow):
        with pytest.raises(RuntimeError, match="timed out"):
            OemerOMR(timeout_seconds=1).image_to_musicxml(b"x", media_type="image/png")
