"""Tests for the OMR text-cleaning helper (no API calls)."""

from services.omr import _extract_musicxml


def test_strips_xml_code_fence():
    raw = "```xml\n<?xml version=\"1.0\"?><score-partwise/>\n```"
    out = _extract_musicxml(raw)
    assert out.startswith("<?xml")
    assert "```" not in out


def test_strips_bare_code_fence():
    raw = "```\n<?xml version=\"1.0\"?><score-partwise/>\n```"
    out = _extract_musicxml(raw)
    assert out.startswith("<?xml")
    assert "```" not in out


def test_strips_leading_prose():
    raw = 'Here is the MusicXML you asked for:\n<?xml version="1.0"?><score-partwise/>'
    out = _extract_musicxml(raw)
    assert out.startswith("<?xml")


def test_falls_back_to_score_partwise():
    raw = "intro text <score-partwise version=\"4.0\"></score-partwise>"
    out = _extract_musicxml(raw)
    assert out.startswith("<score-partwise")


def test_passthrough_clean_xml():
    raw = '<?xml version="1.0"?><score-partwise/>'
    assert _extract_musicxml(raw) == raw
