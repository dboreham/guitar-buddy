import re

import pytest

from guitar_buddy.sheet import TUNINGS, SheetError, parse_sheet


def test_parses_headers_sections_and_chords():
    sheet = parse_sheet(
        """
        title: Test Song
        artist: Someone
        tempo: 100

        [Intro]
        Cm7   x3534x   x1324x
        # a comment
        F7    1x121x
        """
    )
    assert sheet.title == "Test Song"
    assert sheet.artist == "Someone"
    assert sheet.tempo == 100
    assert sheet.tuning == TUNINGS["standard"]
    assert [v.name for v in sheet.voicings] == ["Cm7", "F7"]

    cm7, f7 = sheet.voicings
    assert cm7.frets == [None, 3, 5, 3, 4, None]
    assert cm7.fingers == [None, 1, 3, 2, 4, None]
    assert cm7.section == "Intro"
    assert f7.fingers is None
    assert f7.section is None


def test_separated_frets_allow_two_digits():
    (voicing,) = parse_sheet("Cmaj7 x-x-10-12-12-12 xx1333").voicings
    assert voicing.frets == [None, None, 10, 12, 12, 12]


def test_sharp_in_chord_name_is_not_a_comment():
    (voicing,) = parse_sheet("C#m7 x4646x  # trailing comment").voicings
    assert voicing.name == "C#m7"


def test_thumb_and_no_finger_markers():
    (voicing,) = parse_sheet("D/F# 2x0232 Tx.132").voicings
    assert voicing.fingers == [0, None, None, 1, 3, 2]


def test_unicode_symbols_are_normalized():
    (voicing,) = parse_sheet("B♭Δ7♯11 x1321x").voicings
    assert voicing.name == "Bbmaj7#11"


def test_tuning_by_note_names_sets_string_count():
    sheet = parse_sheet("tuning: B1 E2 A2 D3 G3 B3 E4\nCmaj7 xx3545x")
    assert sheet.tuning == TUNINGS["7 string"]
    assert len(sheet.voicings[0].frets) == 7


@pytest.mark.parametrize(
    "text, message",
    [
        ("Cm7 x353x", "give 5 strings but the tuning has 6"),
        ("Cm7 x3534x x132x", "fingers 'x132x' give 5 strings"),
        ("Cm7 x3534x 13244x", "on a muted or open string"),
        ("Cm7 x3534x x1325x", "bad finger '5'"),
        ("Cm7 x-3-5-3-4-25", "bad fret '25'"),
        ("Cm7", "expected '<name> <frets> [<fingers>]'"),
        ("tempo: fast", "tempo must be a number"),
        ("tuning: weird", "unknown tuning"),
        ("Cm7 x3534x\ntuning: drop d", "tuning must come before the first chord"),
        ("[Outro]", "section [Outro] has no chords"),
        ("Cmaj7#11b9b13add9sus4omit5 x3534x", "longer than 22 characters"),
    ],
)
def test_errors_point_at_the_problem(text, message):
    with pytest.raises(SheetError, match=re.escape(message)):
        parse_sheet(text)


def test_error_reports_line_number():
    with pytest.raises(SheetError) as error:
        parse_sheet("title: x\n\nCm7 x3534x\nF7 bogus\n")
    assert error.value.line_number == 4
