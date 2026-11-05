#!/usr/bin/env python
"""Stage 1 -- choose `ecutwfc` with plane waves only.

No orbital is involved: this is a PW cutoff convergence for the pseudopotential, so the
criterion is that two neighbouring cutoffs agree to within `tolerance_mev_per_atom`.

The script is a *planner* by default.  It prints exactly what would be submitted and
touches neither the database nor the queue; pass `--submit` to actually launch the
`abacus.abacus` CalcJobs (that is deliberately an explicit opt-in).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from utils.params import EcutwfcLadder, load_json   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ladder", help="JSON with the ladder definition (overrides defaults)")
    ap.add_argument("--code", default="abacus_lts@yeesuan", help="ABACUS code label")
    ap.add_argument("--out", default="ladder.json", help="where to write the plan")
    ap.add_argument("--submit", action="store_true",
                    help="actually submit (default: print the plan only)")
    args = ap.parse_args()

    ladder = EcutwfcLadder()
    if args.ladder:
        raw = load_json(args.ladder)
        ladder = EcutwfcLadder(
            values=raw["values"],
            tolerance_mev_per_atom=raw.get("tolerance_mev_per_atom", 2.0),
            structures=raw.get("structures", {}),
        )

    plan = {
        "stage": "1-ecutwfc",
        "code": args.code,
        "criterion": f"neighbouring cutoffs agree to < {ladder.tolerance_mev_per_atom} meV/atom",
        "jobs": [{"ecutwfc": v, "basis_type": "pw", "structure": name}
                 for v in ladder.values for name in (ladder.structures or {"default": None})],
    }
    Path(args.out).write_text(json.dumps(plan, indent=2))

    print(f"stage 1: ecutwfc ladder for {len(ladder.structures) or 1} structure(s)")
    print(f"  cutoffs: {ladder.values}")
    print(f"  criterion: {plan['criterion']}")
    print(f"  code: {args.code}")
    print(f"  jobs: {len(plan['jobs'])}  ->  wrote {args.out}")
    if not args.submit:
        print("\n[dry run] nothing submitted.  Re-run with --submit to launch.")
        return 0

    # --- the only place that touches AiiDA --------------------------------------
    from aiida.orm import Dict, load_code
    from aiida.engine import submit
    from aiida.plugins import CalculationFactory

    AbacusCalculation = CalculationFactory("abacus.abacus")
    code = load_code(args.code)
    for job in plan["jobs"]:
        inputs = {
            "code": code,
            "parameters": Dict(dict={"input": {"basis_type": "pw", "ecutwfc": job["ecutwfc"],
                                               "ks_solver": "dav"}}),
            # structure / pseudos are supplied by the caller's structure registry
            "metadata": {"label": f"ecutwfc-{job['ecutwfc']:g}"},
        }
        print(f"  submitting ecutwfc={job['ecutwfc']:g} ...", end=" ")
        node = submit(AbacusCalculation, **inputs)
        print(node.pk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
