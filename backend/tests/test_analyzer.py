"""Unit tests for services.analyzer using hand-written MusicXML fixtures."""

from pathlib import Path

import pytest

from services import analyzer
from services.analyzer import (
    TritoneInfo,
    _function_for,
    _normalize_roman,
    _short_chord_name,
    _tritone_in_chord,
    analyze,
    analyze_key_only,
)
from music21 import chord as m21chord, key as m21key

FIX = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIX / name).read_text()


def test_normalize_roman_strips_inversions_and_quality():
    assert _normalize_roman("V7") == "V"
    assert _normalize_roman("ii°6") == "ii"
    assert _normalize_roman("V/vi") == "V"
    assert _normalize_roman("I") == "I"


def test_function_map_basic():
    assert _function_for("I") == "tonic"
    assert _function_for("vi") == "tonic"
    assert _function_for("V7") == "dominant"
    assert _function_for("IV") == "subdominant"
    assert _function_for("ii6") == "subdominant"
    # Chromatic chords collapse to their diatonic equivalent for coloring.
    assert _function_for("bVI") == "tonic"
    assert _function_for("Neapolitan") == "other"


def test_short_chord_name_major_minor_seventh():
    c_maj = m21chord.Chord(["C4", "E4", "G4"])
    assert _short_chord_name(c_maj, "") == "C"

    c_min = m21chord.Chord(["C4", "Eb4", "G4"])
    assert _short_chord_name(c_min, "") == "Cm"

    g7 = m21chord.Chord(["G3", "B3", "D4", "F4"])
    assert _short_chord_name(g7, "") == "G7"


def test_tritone_detection_present():
    g7 = m21chord.Chord(["G3", "B3", "D4", "F4"])
    info = _tritone_in_chord(g7)
    assert info.present is True
    assert sorted(info.notes) == ["B3", "F4"]
    assert "tritone" in info.label.lower()


def test_tritone_detection_absent_in_triad():
    c = m21chord.Chord(["C4", "E4", "G4"])
    info = _tritone_in_chord(c)
    assert info.present is False
    assert info.notes == []


def test_analyze_key_c_major_cadence():
    # I - IV - V7 - I in C major; key analysis should land on C major.
    detected = analyze_key_only(_load("c_major_cadence.musicxml")).lower()
    assert "c major" in detected


def test_analyze_returns_event_per_measure():
    events = analyze(_load("c_major_cadence.musicxml"))
    assert len(events) == 4
    measures = [e["measure"] for e in events]
    assert measures == [1, 2, 3, 4]


def test_analyze_chords_and_roman_numerals():
    events = analyze(_load("c_major_cadence.musicxml"))
    chords = [e["chord"] for e in events]
    romans = [e["roman"] for e in events]

    assert chords[0] == "C"
    assert chords[1] == "F"
    assert chords[2] == "G7"
    assert chords[3] == "C"

    # Roman numerals should reflect tonic/subdominant/dominant motion.
    assert romans[0].upper().startswith("I")
    assert romans[1].upper().startswith("IV")
    assert "V" in romans[2].upper()
    assert romans[3].upper().startswith("I")


def test_analyze_function_labels():
    events = analyze(_load("c_major_cadence.musicxml"))
    funcs = [e["function"] for e in events]
    assert funcs[0] == "tonic"
    assert funcs[1] == "subdominant"
    assert funcs[2] == "dominant"
    assert funcs[3] == "tonic"


def test_analyze_tritone_only_on_dominant_seventh():
    events = analyze(_load("c_major_cadence.musicxml"))
    tritones = [e["tritone"]["present"] for e in events]
    # Only the G7 measure should flag a tritone.
    assert tritones == [False, False, True, False]
    g7_event = events[2]
    assert sorted(g7_event["tritone"]["notes"]) == ["B4", "F5"]


def test_analyze_tension_dominant_higher_than_tonic():
    events = analyze(_load("c_major_cadence.musicxml"))
    assert events[2]["tension"] > events[0]["tension"]
    for e in events:
        assert 0.0 <= e["tension"] <= 1.0


def test_analyze_motif_repetition_detected():
    events = analyze(_load("motif_melody.musicxml"))
    motifs = [e["motif"] for e in events if e["motif"]]
    # The C-D-E-C cell repeats in measures 1 and 3 → at least one labeled event.
    assert any(m and m.startswith("motif-") for m in motifs)


def test_analyze_event_shape():
    events = analyze(_load("c_major_cadence.musicxml"))
    e = events[0]
    for key in ("measure", "beat", "chord", "roman", "function", "tritone", "motif", "tension", "note_ids"):
        assert key in e
    assert isinstance(e["tritone"], dict)
    for k in ("present", "notes", "label"):
        assert k in e["tritone"]


def test_analyze_handles_minimal_input_gracefully():
    minimal = '<?xml version="1.0"?>\n<score-partwise version="4.0"><part-list><score-part id="P1"/></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><note><rest/><duration>4</duration><type>whole</type></note></measure></part></score-partwise>'
    events = analyze(minimal)
    # Empty-rest measure → no chord events, but should not raise.
    assert isinstance(events, list)
