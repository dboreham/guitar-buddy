import guitarpro as gp

from guitar_buddy.gp import write_gp5
from guitar_buddy.sheet import parse_sheet

SHEET = """
title: Round Trip
artist: Tester
tempo: 90

[A]
F         133211        134211
Cmaj7     x-x-10-12-12-12   xx1333
Cm7       x3534x
"""


def _chords(song):
    return [
        measure.voices[0].beats[0].effect.chord for measure in song.tracks[0].measures
    ]


def test_written_file_reads_back(tmp_path):
    path = tmp_path / "song.gp5"
    write_gp5(parse_sheet(SHEET), str(path))
    song = gp.parse(str(path))

    assert song.title == "Round Trip"
    assert song.artist == "Tester"
    assert song.tempo == 90
    assert len(song.tracks[0].measures) == 3
    assert [s.value for s in song.tracks[0].strings] == [64, 59, 55, 50, 45, 40]
    assert song.measureHeaders[0].marker.title == "A"
    assert song.measureHeaders[1].marker is None

    f, cmaj7, cm7 = _chords(song)
    assert [c.name for c in (f, cmaj7, cm7)] == ["F", "Cmaj7", "Cm7"]

    # Guitar Pro orders strings from high e (string 1) to low E (string 6).
    assert f.strings[:6] == [1, 1, 2, 3, 3, 1]
    assert [finger.value for finger in f.fingerings[:6]] == [1, 1, 2, 4, 3, 1]
    assert [(b.fret, b.start, b.end) for b in f.barres] == [(1, 1, 6)]
    assert f.firstFret == 1

    assert cmaj7.strings[:6] == [12, 12, 12, 10, -1, -1]
    assert cmaj7.firstFret == 10
    assert [(b.fret, b.start, b.end) for b in cmaj7.barres] == [(12, 1, 3)]

    assert cm7.barres == []
    assert cm7.firstFret == 1


def test_chord_notes_are_playable(tmp_path):
    path = tmp_path / "song.gp5"
    write_gp5(parse_sheet(SHEET), str(path))
    song = gp.parse(str(path))

    beat = song.tracks[0].measures[2].voices[0].beats[0]
    assert beat.duration.value == gp.Duration.whole
    assert sorted((n.string, n.value) for n in beat.notes) == [(2, 4), (3, 3), (4, 5), (5, 3)]
