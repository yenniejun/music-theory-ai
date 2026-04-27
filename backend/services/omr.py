"""OMR service: image bytes -> MusicXML string.

Provider-agnostic so we can swap the engine without touching call sites.
Currently defaults to Oemer (open-source deep-learning OMR, pip-installable).
Adapters for Claude Vision and Audiveris are kept for comparison/upgrade.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Protocol


class _StreamResult:
    __slots__ = ("returncode", "output")

    def __init__(self, returncode: int, output: str):
        self.returncode = returncode
        self.output = output


# Map of oemer stage messages -> approximate cumulative completion %.
# Stages 1 and 2 are slow model inferences (~50% of runtime each). The
# remaining stages are fast CV/heuristics on numpy arrays.
_STAGE_PROGRESS = [
    ("Extracting staffline and symbols", 0),
    ("Extracting layers of different symbols", 50),
    ("Extracting noteheads", 90),
    ("Extracting groups of note", 92),
    ("Extracting symbols", 94),
    ("Parsing rhythm", 96),
    ("Build MusicXML", 98),
]


def _stage_progress(line: str) -> int | None:
    for marker, pct in _STAGE_PROGRESS:
        if marker in line:
            return pct
    return None


def _run_streaming(cmd: list[str], timeout: int) -> _StreamResult:
    """Run a subprocess, streaming each output line to our logger as it arrives.

    Lets us see oemer's progress in real time instead of waiting for completion.
    Recognized stage strings are tagged with a cumulative %.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            stripped = line.rstrip()
            if not stripped:
                continue
            pct = _stage_progress(stripped)
            if pct is not None:
                log.info("[oemer] [~%d%%] %s", pct, stripped)
            else:
                log.info("[oemer] %s", stripped)
            lines.append(stripped)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise
    return _StreamResult(proc.returncode, "\n".join(lines))


def _find_executable(name: str) -> str | None:
    """Resolve a CLI tool that may be installed in the active venv but not on PATH."""
    found = shutil.which(name)
    if found:
        return found
    candidate = Path(sys.executable).parent / name
    if candidate.exists():
        return str(candidate)
    return None

log = logging.getLogger(__name__)


class OMRProvider(Protocol):
    def image_to_musicxml(self, image_bytes: bytes, media_type: str) -> str: ...


# ---------------------------------------------------------------------------
# Default: Oemer (https://github.com/BreezeWhite/oemer)
# ---------------------------------------------------------------------------

_MEDIA_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "application/pdf": ".pdf",
}


def _pdf_to_png_bytes(pdf_bytes: bytes, dpi: int = 300, page: int = 0) -> bytes:
    """Render the given page of a PDF to PNG bytes (first page by default)."""
    import fitz  # PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page >= doc.page_count:
        raise RuntimeError(f"PDF has {doc.page_count} pages; requested page {page}")
    pix = doc.load_page(page).get_pixmap(dpi=dpi)
    return pix.tobytes("png")


def _downscale_png(image_bytes: bytes, max_dim: int = 2000) -> bytes:
    """Downscale an image so its longest edge is at most `max_dim` pixels.

    Oemer's runtime scales with pixel count; large uploads are the #1 source
    of multi-minute waits. Downscaling to 2000px usually preserves enough
    detail for note-head segmentation while running 3-4x faster.
    """
    from io import BytesIO
    from PIL import Image

    img = Image.open(BytesIO(image_bytes))
    w, h = img.size
    longest = max(w, h)
    if longest <= max_dim:
        return image_bytes
    scale = max_dim / longest
    new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
    log.info("Downscaling input: %dx%d -> %dx%d", w, h, *new_size)
    resized = img.resize(new_size, Image.LANCZOS)
    if resized.mode != "RGB":
        resized = resized.convert("RGB")
    out = BytesIO()
    resized.save(out, format="PNG", optimize=True)
    return out.getvalue()


class OemerOMR:
    """OMR backed by the `oemer` CLI.

    Oemer takes an image path and writes a `.musicxml` file beside it
    (or into a directory specified with `-o`). We shell out, then read
    the result back.
    """

    def __init__(self, oemer_bin: str | None = None, timeout_seconds: int | None = None,
                 without_deskew: bool | None = None, max_dim: int | None = None,
                 cache_dir: str | None = None):
        self.oemer_bin = oemer_bin or os.environ.get("OEMER_BIN", "oemer")
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else int(os.environ.get("OEMER_TIMEOUT", "900"))
        )
        self.without_deskew = (
            without_deskew
            if without_deskew is not None
            else os.environ.get("OEMER_NO_DESKEW", "").lower() in ("1", "true", "yes")
        )
        self.max_dim = (
            max_dim
            if max_dim is not None
            else int(os.environ.get("OEMER_MAX_DIM", "2000"))
        )
        cache_path = cache_dir or os.environ.get("OEMER_CACHE_DIR")
        self.cache_dir = Path(cache_path) if cache_path else Path.home() / ".cache" / "scorelayer" / "oemer"

    def image_to_musicxml(self, image_bytes: bytes, media_type: str = "image/png") -> str:
        resolved = _find_executable(self.oemer_bin)
        if resolved is None:
            raise RuntimeError(
                f"oemer binary '{self.oemer_bin}' not found on PATH or next to {sys.executable}. "
                "Install with `pip install oemer` (first run will download ONNX models)."
            )

        ext = _MEDIA_EXT.get(media_type.lower(), ".png")
        if ext == ".pdf":
            log.info("Converting PDF first page to PNG for Oemer")
            image_bytes = _pdf_to_png_bytes(image_bytes)
            ext = ".png"

        if self.max_dim > 0:
            image_bytes = _downscale_png(image_bytes, max_dim=self.max_dim)
            ext = ".png"

        digest = hashlib.sha256(image_bytes).hexdigest()[:16]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cached_xml = self.cache_dir / f"{digest}.musicxml"
        if cached_xml.exists():
            log.info("Cache hit (%s) — skipping oemer", digest)
            return cached_xml.read_text(encoding="utf-8")

        # Persistent per-image directory so oemer's --save-cache pickles
        # are reused if the same image is re-uploaded.
        work_dir = self.cache_dir / digest
        work_dir.mkdir(parents=True, exist_ok=True)
        img_path = work_dir / f"score{ext}"
        img_path.write_bytes(image_bytes)

        cmd = [resolved, str(img_path), "-o", str(work_dir), "--save-cache"]
        if self.without_deskew:
            cmd.append("-d")
        log.info("Running oemer (timeout=%ss): %s", self.timeout_seconds, " ".join(cmd))
        try:
            result = _run_streaming(cmd, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"oemer timed out after {self.timeout_seconds}s. "
                "Bump OEMER_TIMEOUT or try a smaller / less dense image."
            ) from e

        if result.returncode != 0:
            raise RuntimeError(
                f"oemer exited {result.returncode}: {result.output.strip()[-500:]}"
            )

        xml_files = list(work_dir.glob("*.musicxml")) + list(work_dir.glob("*.xml"))
        if not xml_files:
            raise RuntimeError(
                f"oemer produced no MusicXML output. output={result.output!r}"
            )
        xml = xml_files[0].read_text(encoding="utf-8")
        cached_xml.write_text(xml, encoding="utf-8")
        return xml


# ---------------------------------------------------------------------------
# Alternative: Audiveris (FOSS, Java-based; needs the `audiveris` CLI on PATH
# or a Docker wrapper). Kept here as the upgrade path for higher accuracy.
# ---------------------------------------------------------------------------


class AudiverisOMR:
    def __init__(self, audiveris_bin: str | None = None, timeout_seconds: int = 600):
        self.audiveris_bin = audiveris_bin or os.environ.get("AUDIVERIS_BIN", "audiveris")
        self.timeout_seconds = timeout_seconds

    def image_to_musicxml(self, image_bytes: bytes, media_type: str = "image/png") -> str:
        resolved = _find_executable(self.audiveris_bin)
        if resolved is None:
            raise RuntimeError(
                f"audiveris binary '{self.audiveris_bin}' not found on PATH."
            )

        ext = _MEDIA_EXT.get(media_type.lower(), ".png")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            img_path = tmp / f"score{ext}"
            img_path.write_bytes(image_bytes)

            cmd = [
                resolved, "-batch", "-export",
                "-output", str(tmp), "--", str(img_path),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout_seconds, check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(f"audiveris exited {result.returncode}: {result.stderr}")

            xml_files = list(tmp.rglob("*.mxl")) + list(tmp.rglob("*.xml"))
            if not xml_files:
                raise RuntimeError("audiveris produced no MusicXML output")

            target = xml_files[0]
            if target.suffix == ".mxl":
                import zipfile
                with zipfile.ZipFile(target) as zf:
                    inner = next((n for n in zf.namelist() if n.endswith(".xml") and "META" not in n), None)
                    if inner is None:
                        raise RuntimeError("Could not find XML inside .mxl archive")
                    return zf.read(inner).decode("utf-8")
            return target.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Alternative: Claude Vision (LLM-based — kept for benchmarking).
# ---------------------------------------------------------------------------


CLAUDE_OMR_PROMPT = """You are an Optical Music Recognition (OMR) engine.

Given the attached image of sheet music, return a complete, well-formed
MusicXML 4.0 document. Output only XML — no commentary or code fences.
"""


class ClaudeVisionOMR:
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        from anthropic import Anthropic
        self.model = model
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def image_to_musicxml(self, image_bytes: bytes, media_type: str = "image/png") -> str:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": CLAUDE_OMR_PROMPT},
                ],
            }],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return _extract_musicxml(text)


def _extract_musicxml(text: str) -> str:
    """Strip code fences or stray prose, keep the XML."""
    text = text.strip()
    fence = re.match(r"^```(?:xml)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("<?xml")
    if start == -1:
        start = text.find("<score-partwise")
    if start > 0:
        text = text[start:]
    return text


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------

_PROVIDERS = {
    "oemer": OemerOMR,
    "audiveris": AudiverisOMR,
    "claude": ClaudeVisionOMR,
}

_DEFAULT_PROVIDER: OMRProvider | None = None


def get_provider() -> OMRProvider:
    global _DEFAULT_PROVIDER
    if _DEFAULT_PROVIDER is None:
        name = os.environ.get("OMR_PROVIDER", "oemer").lower()
        cls = _PROVIDERS.get(name, OemerOMR)
        _DEFAULT_PROVIDER = cls()
    return _DEFAULT_PROVIDER


def set_provider(provider: OMRProvider) -> None:
    """Override the active provider — handy for tests."""
    global _DEFAULT_PROVIDER
    _DEFAULT_PROVIDER = provider


def image_to_musicxml(image_bytes: bytes, media_type: str = "image/png") -> str:
    return get_provider().image_to_musicxml(image_bytes, media_type)
