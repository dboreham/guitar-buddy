"""Parse plain-text chord sheets.

A chord sheet looks like::

    title: Autumn Leaves
    artist: Joseph Kosma
    tuning: standard
    tempo: 80

    [A section]
    Cm7       x3534x    x2143x
    F7        1x122x    1x234x
    Bbmaj7    x-1-3-2-3-x
    # comments start with '#'
    Ebmaj7    x-6-8-7-8-x   x1324x

Each chord line is ``<name> <frets> [<fingers>]``, all written from the
lowest-pitched string to the highest.

Frets: one character per string (``x3534x``), or separated by ``-`` or
``,`` when any fret has two digits (``x-10-12-11-12-x``). ``x`` means the
string is muted, ``0`` open.

Fingers (optional): ``1``-``4`` for index..little, ``T`` for thumb, and
``x``, ``0``, ``-``, or ``.`` for no finger (muted or open strings).

``[Section name]`` lines become section markers on the next chord.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# MIDI note numbers, lowest-pitched string first.
TUNINGS: dict[str, list[int]] = {
    "standard": [40, 45, 50, 55, 59, 64],
    "drop d": [38, 45, 50, 55, 59, 64],
    "dadgad": [38, 45, 50, 55, 57, 62],
    "open g": [38, 43, 50, 55, 59, 62],
    "open d": [38, 45, 50, 54, 57, 62],
    "half step down": [39, 44, 49, 54, 58, 63],
    "7 string": [35, 40, 45, 50, 55, 59, 64],
}

HEADER_KEYS = ("title", "artist", "tuning", "tempo")
MAX_NAME_LENGTH = 22  # Limit of the GP4/GP5 chord diagram name field.
MAX_STRINGS = 7  # GP chord diagrams support at most 7 strings.

NOTE_NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NO_FINGER = set("x0-.")
FINGER_CHARS = {"T": 0, "1": 1, "2": 2, "3": 3, "4": 4}

# Characters outside cp1252, which Guitar Pro 5 files use for text.
NAME_SUBSTITUTIONS = {"♭": "b", "♯": "#", "Δ": "maj", "△": "maj", "⁰": "°"}


class SheetError(ValueError):
    """A problem in a chord sheet, reported with its line number."""

    def __init__(self, line_number: int, message: str):
        super().__init__(f"line {line_number}: {message}")
        self.line_number = line_number


@dataclass
class Voicing:
    name: str
    # Fret per string, lowest-pitched string first. None means muted.
    frets: list[int | None]
    # Finger per string (0 = thumb, 1-4 = index..little), None for no finger.
    fingers: list[int | None] | None = None
    section: str | None = None


@dataclass
class Sheet:
    title: str = ""
    artist: str = ""
    tuning: list[int] = field(default_factory=lambda: list(TUNINGS["standard"]))
    tempo: int = 80
    voicings: list[Voicing] = field(default_factory=list)


def parse_sheet(text: str) -> Sheet:
    sheet = Sheet()
    pending_section: str | None = None

    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw).strip()
        if not line:
            continue

        header = re.match(r"^(\w+)\s*:\s*(.*)$", line)
        if header and header.group(1).lower() in HEADER_KEYS:
            _apply_header(sheet, header.group(1).lower(), header.group(2).strip(), line_number)
            continue

        section = re.match(r"^\[(.+)\]$", line)
        if section:
            pending_section = section.group(1).strip()
            continue

        voicing = _parse_voicing(line, len(sheet.tuning), line_number)
        voicing.section = pending_section
        pending_section = None
        sheet.voicings.append(voicing)

    if pending_section is not None:
        # A trailing section with no chords would otherwise vanish silently.
        raise SheetError(len(text.splitlines()), f"section [{pending_section}] has no chords")
    return sheet


def _strip_comment(line: str) -> str:
    # '#' starts a comment at the start of a line or after whitespace, so
    # chord names such as C#m7 are left alone.
    return re.sub(r"(^|\s)#.*$", "", line)


def _apply_header(sheet: Sheet, key: str, value: str, line_number: int) -> None:
    if key == "title":
        sheet.title = value
    elif key == "artist":
        sheet.artist = value
    elif key == "tempo":
        if not value.isdigit() or not 20 <= int(value) <= 400:
            raise SheetError(line_number, f"tempo must be a number from 20 to 400, got {value!r}")
        sheet.tempo = int(value)
    elif key == "tuning":
        if sheet.voicings:
            raise SheetError(line_number, "tuning must come before the first chord")
        sheet.tuning = parse_tuning(value, line_number)


def parse_tuning(value: str, line_number: int = 0) -> list[int]:
    """Parse a preset name, or note names low to high such as ``D2 A2 D3 G3 B3 E4``."""
    preset = TUNINGS.get(value.lower())
    if preset:
        return list(preset)

    notes = value.split()
    if not 4 <= len(notes) <= MAX_STRINGS:
        raise SheetError(
            line_number,
            f"unknown tuning {value!r}; use one of {', '.join(TUNINGS)} "
            f"or 4-{MAX_STRINGS} notes with octaves, e.g. 'D2 A2 D3 G3 B3 E4'",
        )
    return [_parse_note(note, line_number) for note in notes]


def _parse_note(note: str, line_number: int) -> int:
    match = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d)", note)
    if not match:
        raise SheetError(line_number, f"bad tuning note {note!r}; expected e.g. E2, F#3, Bb1")
    letter, accidental, octave = match.groups()
    pitch = NOTE_NAMES[letter.upper()] + {"#": 1, "b": -1, "": 0}[accidental]
    return (int(octave) + 1) * 12 + pitch


def _parse_voicing(line: str, string_count: int, line_number: int) -> Voicing:
    parts = line.split()
    if len(parts) not in (2, 3):
        raise SheetError(
            line_number, f"expected '<name> <frets> [<fingers>]', got {line!r}"
        )

    name = normalize_name(parts[0], line_number)
    frets = _parse_frets(parts[1], string_count, line_number)
    fingers = _parse_fingers(parts[2], frets, line_number) if len(parts) == 3 else None
    return Voicing(name=name, frets=frets, fingers=fingers)


def normalize_name(name: str, line_number: int = 0) -> str:
    for symbol, replacement in NAME_SUBSTITUTIONS.items():
        name = name.replace(symbol, replacement)
    try:
        name.encode("cp1252")
    except UnicodeEncodeError:
        raise SheetError(line_number, f"chord name {name!r} has characters Guitar Pro can't store")
    if len(name) > MAX_NAME_LENGTH:
        raise SheetError(
            line_number, f"chord name {name!r} is longer than {MAX_NAME_LENGTH} characters"
        )
    return name


def _parse_frets(token: str, string_count: int, line_number: int) -> list[int | None]:
    cells = re.split(r"[-,]", token) if re.search(r"[-,]", token) else list(token)
    if len(cells) != string_count:
        raise SheetError(
            line_number,
            f"frets {token!r} give {len(cells)} strings but the tuning has {string_count}",
        )

    frets: list[int | None] = []
    for cell in cells:
        if cell.lower() == "x":
            frets.append(None)
        elif cell.isdigit() and int(cell) <= 24:
            frets.append(int(cell))
        else:
            raise SheetError(line_number, f"bad fret {cell!r} in {token!r}; use 0-24 or x")
    return frets


def _parse_fingers(
    token: str, frets: list[int | None], line_number: int
) -> list[int | None]:
    if len(token) != len(frets):
        raise SheetError(
            line_number,
            f"fingers {token!r} give {len(token)} strings but the frets give {len(frets)}",
        )

    fingers: list[int | None] = []
    for char, fret in zip(token, frets):
        if char.lower() in NO_FINGER:
            fingers.append(None)
        elif char.upper() in FINGER_CHARS:
            if not fret:
                raise SheetError(
                    line_number, f"finger {char!r} is on a muted or open string in {token!r}"
                )
            fingers.append(FINGER_CHARS[char.upper()])
        else:
            raise SheetError(
                line_number, f"bad finger {char!r} in {token!r}; use 1-4, T, or x/0/-/."
            )
    return fingers
