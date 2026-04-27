"""music21-based analysis: MusicXML -> per-event annotations.

Produces one AnnotationEvent per beat/chord onset, matching the JSON shape
the frontend overlays expect.
"""

from __future__ import annotations

import io
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

from music21 import (
    chord as m21chord,
    converter,
    interval,
    note,
    pitch,
    roman,
    stream,
)


@dataclass
class TritoneInfo:
    present: bool = False
    notes: list[str] = field(default_factory=list)
    label: str = ""


@dataclass
class AnnotationEvent:
    measure: int
    beat: float
    chord: str
    roman: str
    function: str
    tritone: TritoneInfo
    motif: str | None
    tension: float
    note_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


_FUNCTION_MAP = {
    "I": "tonic", "i": "tonic", "vi": "tonic", "VI": "tonic", "iii": "tonic", "III": "tonic",
    "V": "dominant", "v": "dominant", "vii": "dominant", "VII": "dominant",
    "IV": "subdominant", "iv": "subdominant", "ii": "subdominant", "II": "subdominant",
}


def _normalize_roman(rn_figure: str) -> str:
    base = rn_figure.split("/")[0]
    for sym in ("°", "o", "ø", "+", "b", "#"):
        base = base.replace(sym, "")
    base = "".join(ch for ch in base if not ch.isdigit())
    return base or rn_figure


def _function_for(rn_figure: str) -> str:
    base = _normalize_roman(rn_figure)
    return _FUNCTION_MAP.get(base, "other")


def _tritone_in_chord(c: m21chord.Chord) -> TritoneInfo:
    pitches = list(c.pitches)
    for i, p1 in enumerate(pitches):
        for p2 in pitches[i + 1:]:
            iv = interval.Interval(p1, p2)
            simple = iv.simpleName
            if simple in ("A4", "d5"):
                return TritoneInfo(
                    present=True,
                    notes=[p1.nameWithOctave, p2.nameWithOctave],
                    label="tritone — tension wants resolution",
                )
    return TritoneInfo()


def _tension_score(c: m21chord.Chord, key_obj) -> float:
    """Rough dissonance score in [0, 1].

    Combines: chord-internal interval dissonance + non-diatonic note count.
    """
    if not c.pitches:
        return 0.0

    weights = {"m2": 1.0, "M2": 0.5, "A4": 0.9, "d5": 0.9, "m7": 0.6, "M7": 0.8}
    score = 0.0
    pairs = 0
    pitches = list(c.pitches)
    for i, p1 in enumerate(pitches):
        for p2 in pitches[i + 1:]:
            simple = interval.Interval(p1, p2).simpleName
            score += weights.get(simple, 0.1)
            pairs += 1

    interval_score = score / pairs if pairs else 0.0

    diatonic = {p.name for p in key_obj.pitches}
    non_diatonic = sum(1 for p in pitches if p.name not in diatonic)
    chromatic_score = non_diatonic / len(pitches)

    return max(0.0, min(1.0, 0.6 * interval_score + 0.4 * chromatic_score))


def _detect_motifs(score: stream.Score) -> dict[int, str]:
    """Extremely simple motif detection.

    Slides a 4-note window over the top-line melody, normalizes to relative
    pitch+rhythm, and labels the top recurring patterns.
    Returns: {note offset (rounded) -> motif label}.
    """
    parts = score.parts
    if not parts:
        return {}
    melody = parts[0].flatten().notes
    if len(melody) < 4:
        return {}

    sequences: list[tuple[tuple, list[float]]] = []
    for i in range(len(melody) - 3):
        window = list(melody[i:i + 4])
        if not all(isinstance(n, note.Note) for n in window):
            continue
        intervals = tuple(
            window[j + 1].pitch.midi - window[j].pitch.midi for j in range(3)
        )
        rhythms = tuple(round(n.quarterLength * 2) / 2 for n in window)
        offsets = [float(n.offset) for n in window]
        sequences.append(((intervals, rhythms), offsets))

    counts = Counter(sig for sig, _ in sequences)
    top = [sig for sig, c in counts.most_common(3) if c >= 2]
    if not top:
        return {}

    label_map = {sig: f"motif-{chr(ord('A') + i)}" for i, sig in enumerate(top)}
    out: dict[int, str] = {}
    for sig, offsets in sequences:
        if sig in label_map:
            for off in offsets:
                out[round(off * 4)] = label_map[sig]
    return out


def analyze(musicxml_str: str) -> list[dict[str, Any]]:
    """Parse MusicXML and emit one annotation per chord event."""
    score = converter.parse(musicxml_str, format="musicxml")

    try:
        key_obj = score.analyze("key")
    except Exception:
        from music21 import key as m21key
        key_obj = m21key.Key("C")

    motif_offsets = _detect_motifs(score)

    chordified = score.chordify()
    events: list[AnnotationEvent] = []

    for c in chordified.recurse().getElementsByClass(m21chord.Chord):
        if not c.pitches:
            continue

        measure_obj = c.getContextByClass(stream.Measure)
        measure_num = measure_obj.number if measure_obj is not None else 0
        beat_val = float(c.beat) if c.beat is not None else 1.0

        try:
            chord_symbol = c.pitchedCommonName
        except Exception:
            chord_symbol = c.commonName or ""

        try:
            rn = roman.romanNumeralFromChord(c, key_obj)
            rn_fig = rn.figure
        except Exception:
            rn_fig = ""

        tritone_info = _tritone_in_chord(c)
        tension = _tension_score(c, key_obj)

        offset_key = round(float(c.offset) * 4)
        motif_label = motif_offsets.get(offset_key)

        note_ids = []
        for p in c.pitches:
            nid = getattr(p, "id", None)
            if nid:
                note_ids.append(str(nid))

        events.append(
            AnnotationEvent(
                measure=measure_num,
                beat=beat_val,
                chord=_short_chord_name(c, chord_symbol),
                roman=rn_fig,
                function=_function_for(rn_fig) if rn_fig else "other",
                tritone=tritone_info,
                motif=motif_label,
                tension=round(tension, 3),
                note_ids=note_ids,
            )
        )

    return [e.to_dict() for e in events]


def _short_chord_name(c: m21chord.Chord, fallback: str) -> str:
    """Compact chord label like 'G7' or 'Cm' from a music21 Chord."""
    try:
        root = c.root().name.replace("-", "b")
    except Exception:
        return fallback
    quality = c.quality
    seventh = c.seventh is not None
    suffix = ""
    if quality == "minor":
        suffix = "m"
    elif quality == "diminished":
        suffix = "°"
    elif quality == "augmented":
        suffix = "+"
    if seventh:
        if quality == "major" and c.isDominantSeventh():
            suffix = "7"
        elif quality == "major":
            suffix = "maj7"
        elif quality == "minor":
            suffix = "m7"
        elif quality == "diminished":
            suffix = "°7"
    return f"{root}{suffix}"


def analyze_key_only(musicxml_str: str) -> str:
    score = converter.parse(musicxml_str, format="musicxml")
    return score.analyze("key").name
