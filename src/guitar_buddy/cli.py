"""Command line entry point: ``guitar-buddy song.chords [-o song.gp5]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .gp import write_gp5
from .sheet import SheetError, parse_sheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="guitar-buddy",
        description="Turn a plain-text chord sheet into a Guitar Pro 5 file with chord diagrams.",
    )
    parser.add_argument("sheet", type=Path, help="chord sheet to read")
    parser.add_argument(
        "-o", "--output", type=Path, help="file to write (default: the sheet's name with .gp5)"
    )
    args = parser.parse_args(argv)

    output = args.output or args.sheet.with_suffix(".gp5")
    try:
        sheet = parse_sheet(args.sheet.read_text(encoding="utf-8"))
    except OSError as error:
        print(f"guitar-buddy: {error}", file=sys.stderr)
        return 1
    except SheetError as error:
        print(f"guitar-buddy: {args.sheet}: {error}", file=sys.stderr)
        return 1

    if not sheet.voicings:
        print(f"guitar-buddy: {args.sheet}: no chords found", file=sys.stderr)
        return 1

    write_gp5(sheet, str(output))
    print(f"Wrote {len(sheet.voicings)} chords to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
