# guitar-buddy

Turn a plain-text list of chord voicings into a Guitar Pro file with chord
diagrams, including which finger goes where. Handy for capturing unusual
voicings from lessons and videos without drawing diagrams by hand.

Each chord becomes one measure with a whole-note strum and its diagram, so you
can see the shape, read the notes in standard notation and tab, and hear it
played back. The output is Guitar Pro 5 (`.gp5`), which Guitar Pro 6–8,
TuxGuitar and others open.

## Installation

With [uv](https://docs.astral.sh/uv/), install the `guitar-buddy` command
straight from GitHub:

```sh
uv tool install git+https://github.com/dboreham/guitar-buddy
```

To upgrade to the latest version later:

```sh
uv tool upgrade guitar-buddy
```

## Usage

```sh
guitar-buddy my-song.chords                        # writes my-song.gp5
guitar-buddy my-song.chords -o ~/tabs/my-song.gp5
```

## Chord sheet format

```
title: Autumn Leaves
artist: Joseph Kosma
tuning: standard
tempo: 80

[A section]
Cm7       x3534x            x1324x
F7        1x121x            1x121x
Cmaj7     x-x-10-12-12-12   xx1333
# comments start with '#'
```

- **Chord lines** are `<name> <frets> [<fingers>]`, written from the lowest
  string to the highest.
- **Frets:** one character per string (`x3534x`), or separated by `-` or `,`
  when a fret has two digits (`x-x-10-12-12-12`). `x` is muted, `0` is open.
- **Fingers** (optional): `1`–`4` for index to little finger, `T` for thumb,
  and `x`, `0`, `-` or `.` for no finger. A finger held on several strings at
  the same fret is drawn as a barre.
- **Names** can be anything up to 22 characters. `♭`, `♯` and `Δ` are
  converted to `b`, `#` and `maj`.
- **`[Section]`** lines add a section marker at the next chord.
- **Headers** (all optional): `title`, `artist`, `tempo`, and `tuning`, which
  takes a preset (`standard`, `drop d`, `dadgad`, `open g`, `open d`,
  `half step down`, `7 string`) or note names from low to high, e.g.
  `tuning: D2 A2 D3 G3 B3 E4`. Seven-string tunings are supported.

## Chord diagrams above the staff

Guitar Pro 8 decides where chord diagrams go from its stylesheet, not from the
file, and defaults to a grid at the top of the page. To show them above the
staff, change the chord diagram setting in the stylesheet.

## Development

From a clone of the repository:

```sh
uv sync
uv run guitar-buddy examples/autumn-leaves.chords   # writes examples/autumn-leaves.gp5
uv run pytest
```
