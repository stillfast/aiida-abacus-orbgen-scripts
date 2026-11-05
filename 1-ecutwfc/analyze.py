#!/usr/bin/env python
"""Stage 1 analysis -- turn the cutoff ladder into one `ecutwfc`.

Reads a CSV of `ecutwfc,energy_eV[,natoms]` (the output of a finished ladder) and
applies the neighbour-difference rule.  Also accepts a JSON produced by `launch.py` to
echo the plan back.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from utils.analysis import LadderRow, select_ecutwfc   # noqa: E402


def read_csv(path: str) -> list[LadderRow]:
    rows = []
    with open(path, newline="") as handle:
        for rec in csv.DictReader(handle):
            rows.append(LadderRow(value=float(rec["ecutwfc"]),
                                  energy=float(rec["energy_eV"]),
                                  natoms=int(rec.get("natoms", 1) or 1)))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table", help="CSV: ecutwfc,energy_eV[,natoms]")
    ap.add_argument("--tolerance", type=float, default=2.0, help="meV/atom (default 2)")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    rows = read_csv(args.table)
    result = select_ecutwfc(rows, args.tolerance)

    print(f"{'ecutwfc':>9} {'E (eV)':>18} {'E/atom (eV)':>14}")
    for r in sorted(rows, key=lambda r: r.value):
        print(f"{r.value:>9g} {r.energy:>18.6f} {r.per_atom():>14.6f}")
    print(f"\nneighbour differences (meV/atom), tolerance {args.tolerance:g}:")
    for d in result["diffs"]:
        mark = "OK" if d["abs_mev_per_atom"] <= args.tolerance else "  "
        print(f"  {d['from']:>6g} -> {d['to']:<6g} {d['delta_mev_per_atom']:>+9.2f}  {mark}")

    if result["chosen"] is None:
        print("\nno neighbouring pair inside the tolerance -- extend the ladder")
        return 2
    print(f"\nchosen ecutwfc = {result['chosen']:g} Ry   ({result['rule']})")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
