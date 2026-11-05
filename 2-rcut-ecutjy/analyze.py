#!/usr/bin/env python
"""Stage 2 analysis -- pick (r_cut, ecutjy) from a scanned grid.

Input CSV columns (extra columns are ignored)::

    r_cut,ecutjy,l_max,nbasis_per_atom,error_<geometry>,...

`error_<geometry>` is the total-energy error against the plane-wave reference in meV per
**cell**; it is divided by `--natoms` to get meV/atom.  A single `mean_error_mev` column
is also accepted.

Two rules are reported side by side on purpose:

  * ``vs PW``            -- the honest one; picks the cheapest point inside the tolerance
  * ``neighbour``        -- what a ladder-style rule would pick; kept to show why it is
                            the wrong tool for a basis-set error that has a systematic
                            offset and therefore never converges to its neighbour
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from utils.analysis import select_rcut_ecutjy   # noqa: E402


def read_csv(path: str, natoms: int) -> list[dict]:
    out = []
    with open(path, newline="") as handle:
        for rec in csv.DictReader(handle):
            errors = {k[len("error_"):]: float(v) / natoms * 1000.0
                      for k, v in rec.items()
                      if k.startswith("error_") and v not in ("", None)}
            item = {
                "r_cut": float(rec["r_cut"]),
                "ecutjy": float(rec["ecutjy"]),
                "l_max": int(rec.get("l_max", 4) or 4),
                "nbasis_per_atom": int(rec["nbasis_per_atom"]),
            }
            if errors:
                item["errors_mev"] = errors
            elif rec.get("mean_error_mev"):
                item["mean_error_mev"] = float(rec["mean_error_mev"]) / natoms
            out.append(item)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table", help="CSV as described above")
    ap.add_argument("--tolerance", type=float, default=43.364, help="meV/atom (default 1 kcal/mol)")
    ap.add_argument("--natoms", type=int, default=1, help="atoms in the reference cell")
    ap.add_argument("--cost-exponent", type=float, default=1.0)
    ap.add_argument("--r-cut-reference", type=float, default=10.0)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    candidates = read_csv(args.table, args.natoms)
    result = select_rcut_ecutjy(candidates, args.tolerance,
                                cost_exponent=args.cost_exponent,
                                r_cut_reference=args.r_cut_reference,
                                natoms=args.natoms)

    print(f"{'r_cut':>6}{'ecutjy':>8}{'l_max':>7}{'nbf/atom':>10}"
          f"{'dE (meV/at)':>13}{'dE (kcal)':>11}{'cost':>10}  verdict")
    for row in result["table"]:
        verdict = "PASS" if row["passes"] else "fail"
        print(f"{row['r_cut']:>6g}{row['ecutjy']:>8g}{row['l_max']:>7d}"
              f"{row['nbasis_per_atom']:>10d}{row['mean_error_mev']:>+13.2f}"
              f"{row['mean_error_kcal']:>+11.2f}{row['cost']:>10.0f}  {verdict}")

    best = result["best"]
    if best is None:
        print(f"\nno point within {args.tolerance:.2f} meV/atom -- widen r_cut or ecutjy")
        return 2
    print(f"\nchosen: r_cut = {best['r_cut']:g} a.u.   ecutjy = {best['ecutjy']:g} Ry   "
          f"l_max = {best['l_max']}   ({best['nbasis_per_atom']} functions/atom)")
    print(f"        dE = {best['mean_error_mev']:+.2f} meV/atom "
          f"({best['mean_error_kcal']:+.3f} kcal/mol), tolerance {args.tolerance:.2f}")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
