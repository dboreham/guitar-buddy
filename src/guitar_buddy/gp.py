"""Build a Guitar Pro 5 song from a parsed chord sheet.

Each voicing becomes one 4/4 measure holding a single whole-note chord with
its chord diagram, so Guitar Pro shows the diagram and plays the chord back.
"""

from __future__ import annotations

import guitarpro as gp

from .sheet import Sheet, Voicing

DIAGRAM_FRETS = 5  # Voicings reaching past this fret get a moved-up diagram.
STEEL_STRING_GUITAR = 25  # General MIDI program for Acoustic Guitar (steel).


def build_song(sheet: Sheet) -> gp.Song:
    song = gp.Song(title=sheet.title, artist=sheet.artist, tempo=sheet.tempo)
    song.measureHeaders = []

    track = song.tracks[0]
    track.name = "Guitar"
    track.channel.instrument = STEEL_STRING_GUITAR
    # Ask for diagrams above the staff rather than in a grid at the top.
    # Guitar Pro 8 ignores this for GP5 files and uses its stylesheet instead.
    track.settings.diagramsInScore = True
    track.settings.diagramList = False
    # Guitar Pro numbers strings from 1 = highest pitch.
    track.strings = [
        gp.GuitarString(number, value)
        for number, value in enumerate(reversed(sheet.tuning), start=1)
    ]
    track.measures = []

    for index, voicing in enumerate(sheet.voicings):
        header = gp.MeasureHeader(
            number=index + 1,
            start=gp.Duration.quarterTime * (1 + 4 * index),
        )
        if voicing.section:
            header.marker = gp.Marker(title=voicing.section)
        song.addMeasureHeader(header)

        measure = gp.Measure(track, header)
        track.measures.append(measure)
        _add_chord_beat(measure.voices[0], voicing)

    return song


def write_gp5(sheet: Sheet, path: str) -> None:
    gp.write(build_song(sheet), path, version=(5, 1, 0))


def _add_chord_beat(voice: gp.Voice, voicing: Voicing) -> None:
    beat = gp.Beat(voice, duration=gp.Duration(value=gp.Duration.whole))
    string_count = len(voicing.frets)
    for low_index, fret in enumerate(voicing.frets):
        if fret is None:
            continue
        note = gp.Note(beat, value=fret, string=string_count - low_index, type=gp.NoteType.normal)
        beat.notes.append(note)
    beat.status = gp.BeatStatus.normal if beat.notes else gp.BeatStatus.rest
    beat.effect.chord = build_chord(voicing)
    voice.beats.append(beat)


def build_chord(voicing: Voicing) -> gp.Chord:
    # Guitar Pro orders diagram strings from highest pitch to lowest.
    frets = list(reversed(voicing.frets))
    fingers = list(reversed(voicing.fingers)) if voicing.fingers else None

    chord = gp.Chord(
        length=len(frets),
        name=voicing.name,
        sharp=True,
        add=False,
        show=True,
        newFormat=True,
        firstFret=_first_fret(frets),
        strings=[-1 if fret is None else fret for fret in frets],
    )
    if fingers:
        chord.fingerings = [
            gp.Fingering.open if finger is None else gp.Fingering(finger) for finger in fingers
        ]
        chord.barres = _barres(frets, fingers)
    return chord


def _first_fret(frets: list[int | None]) -> int:
    fretted = [fret for fret in frets if fret]
    if not fretted or max(fretted) <= DIAGRAM_FRETS:
        return 1
    return min(fretted)


def _barres(frets: list[int | None], fingers: list[int | None]) -> list[gp.Barre]:
    """A finger held on several strings at one fret is a barre.

    Guitar Pro stores a barre as its fret plus a string range that always
    starts at string 1 and ends at the lowest-pitched string it covers.
    """
    strings_by_position: dict[tuple[int, int], list[int]] = {}
    for number, (fret, finger) in enumerate(zip(frets, fingers), start=1):
        if fret and finger:  # Thumb (0) never barres.
            strings_by_position.setdefault((finger, fret), []).append(number)

    barres = [
        gp.Barre(fret=fret, start=1, end=max(strings))
        for (_, fret), strings in strings_by_position.items()
        if len(strings) > 1
    ]
    return sorted(barres, key=lambda barre: barre.fret)
