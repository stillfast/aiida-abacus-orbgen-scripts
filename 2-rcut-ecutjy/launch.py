#!/usr/bin/env python
"""Stage 2 -- choose (r_cut, ecutjy) jointly, with l_max fixed.

The two parameters are scanned together because they are not independent: a small
`r_cut` cannot be rescued by a large `ecutjy` (the basis is truncated in space, and no
number of Bessel functions recovers what lies beyond the cutoff).  Scanning them jointly
also exposes the trap that a *neighbour-difference* criterion hides -- see the README.

Planner by default; `--submit` is an explicit opt-in.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from utils.params import RcutEcutjyGrid, load_json   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grid", help="JSON with the grid definition (overrides defaults)")
    ap.add_argument("--l-max", type=int, default=None, help="fixed l_max (default 4)")
    ap.add_argument("--code", default="abacus_lts@yeesuan")
    ap.add_argument("--tolerance", type=float, default=None,
                    help="meV/atom vs PW (default 1 kcal/mol = 43.364)")
    ap.add_argument("--out", default="grid.json")
    ap.add_argument("--submit", action="store_true",
                    help="actually submit (default: print the plan only)")
    args = ap.parse_args()

    grid = RcutEcutjyGrid()
    if args.grid:
        raw = load_json(args.grid)
        grid = RcutEcutjyGrid(
            r_cuts=raw["r_cuts"], ecutjys=raw["ecutjys"],
            l_max=raw.get("l_max", 4),
            tolerance_mev_per_atom=raw.get("tolerance_mev_per_atom", 43.364),
            cost_exponent=raw.get("cost_exponent", 1.0),
            r_cut_reference=raw.get("r_cut_reference", 10.0),
            structures=raw.get("structures", {}),
        )
    if args.l_max is not None:
        grid.l_max = args.l_max
    if args.tolerance is not None:
        grid.tolerance_mev_per_atom = args.tolerance

    points = grid.points()
    plan = {
        "stage": "2-rcut-ecutjy",
        "code": args.code,
        "l_max": grid.l_max,
        "criterion": f"|dE| vs plane waves <= {grid.tolerance_mev_per_atom:.3f} meV/atom, "
                     f"then cheapest",
        "workflow": "abacus.orbgen.converge",
        "points": points,
        "tolerance_mev_per_atom": grid.tolerance_mev_per_atom,
    }
    Path(args.out).write_text(json.dumps(plan, indent=2))

    print(f"stage 2: (r_cut, ecutjy) grid at l_max = {grid.l_max}")
    print(f"  r_cut  : {grid.r_cuts} a.u.")
    print(f"  ecutjy : {grid.ecutjys} Ry")
    print(f"  points : {len(points)}  (one abacus.orbgen.converge run, plus the PW reference)")
    print(f"  criterion: {plan['criterion']}")
    print(f"  wrote {args.out}")
    if not args.submit:
        print("\n[dry run] nothing submitted.  Re-run with --submit to launch.")
        return 0

    # --- the only place that touches AiiDA --------------------------------------
    print("\nsubmitting abacus.orbgen.converge ...")
    raise SystemExit(
        "refusing to submit from the planner: build the builder explicitly so the "
        "structures / pseudopotential / code are visible in the script that submits"
    )


if __name__ == "__main__":
    raise SystemExit(main())
