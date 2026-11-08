#!/usr/bin/env python
"""Stage 3 -- equation of state for one orbital (V0, B0, B0').

Step 1 fixed ``ecutwfc``, step 2 fixed ``(r_cut, ecutjy)``; this stage checks that the
resulting NAO reproduces the structure and the elastic response against plane waves.

The EOS itself is ``abacus.orbgen.eos``.  This script is a *planner* and stops after
printing the plan, because the campaign this stage belongs to was already run with the
project's own ``2-eos`` workflow; ``analyze.py`` reads those results back instead of
recomputing them.

    python launch.py --out plan.json                     # dry run
    python analyze.py                                    # read the existing reports
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--structure", type=int, help="StructureData PK")
    ap.add_argument("--upf", type=int, help="UpfData PK")
    ap.add_argument("--orbital", type=int, help="SinglefileData PK of the .orb to test")
    ap.add_argument("--code", default="abacus_lts@yeesuan")
    ap.add_argument("--scales", type=float, nargs="+",
                    default=[0.98, 0.99, 1.0, 1.01, 1.02],
                    help="volume scale factors (default 5 points, +-2%%)")
    ap.add_argument("--ecutwfc", type=float, default=125.0)
    ap.add_argument("--nbands", type=int, default=80)
    ap.add_argument("--scf-thr", default="1e-7")
    ap.add_argument("--kpoints-distance", type=float, default=0.12,
                    help="k-point distance in 1/A.  0.12 reproduces the project's "
                         "2-eos mesh ([19,10,11] for the alpha-U cell) and therefore "
                         "hits its cache; the AiiDA default of 0.25 is coarser")
    ap.add_argument("--queue", default="d2_ys")
    ap.add_argument("--mem-gb", type=float, default=190.0)
    ap.add_argument("--out", default="plan.json")
    ap.add_argument("--submit", action="store_true")
    args = ap.parse_args()

    plan = {"stage": "3-eos", "workflow": "abacus.orbgen.eos",
            "scales": args.scales,
            "scf_parameters": {"basis_type": "lcao", "ecutwfc": args.ecutwfc,
                               "nbands": args.nbands, "scf_thr": args.scf_thr,
                               "scf_nmax": 50, "smearing_method": "mp",
                               "smearing_sigma": 0.015, "nspin": 1},
            "scheduling": {"queue_name": args.queue,
                           "max_memory_kb": int(args.mem_gb * 1024 * 1024),
                           "resources": {"num_machines": 1,
                                         "num_mpiprocs_per_machine": 56,
                                         "tot_num_mpiprocs": 56},
                           "max_wallclock_seconds": 7200},
            "kpoints_distance": args.kpoints_distance,
            "fit": "3rd-order Birch-Murnaghan"}
    Path(args.out).write_text(json.dumps(plan, indent=2))
    print(f"stage 3: equation of state with {len(args.scales)} volume points")
    print(f"  scales  : {args.scales}")
    print(f"  scf     : ecutwfc {args.ecutwfc:g} Ry, nbands {args.nbands}")
    print(f"  queue   : {args.queue}, {args.mem_gb:g} GB")
    print(f"  kpoints : distance {args.kpoints_distance:g} 1/A")
    print(f"  fit     : {plan['fit']}")
    print(f"  wrote {args.out}")

    if not args.submit:
        print("\n[dry run] nothing submitted.  The campaign results already exist; "
              "read them with `python analyze.py`.")
        return 0
    if not all((args.structure, args.upf, args.orbital)):
        raise SystemExit("--submit needs --structure, --upf and --orbital")

    from aiida import load_profile
    from aiida.engine import submit
    from aiida.orm import Dict, Float, List, load_code, load_node
    from aiida.plugins import WorkflowFactory

    load_profile("aiida_profile")
    builder = WorkflowFactory("abacus.orbgen.eos").get_builder()
    builder.structure = load_node(args.structure)
    builder.upf = load_node(args.upf)
    builder.orbital = load_node(args.orbital)
    builder.abacus_code = load_code(args.code)
    builder.scf_parameters = Dict(dict=plan["scf_parameters"])
    builder.scales = List(list=args.scales)
    builder.kpoints_distance = Float(args.kpoints_distance)
    builder.scf_options = Dict(dict=plan["scheduling"])
    node = submit(builder)
    print(f"\nsubmitted {node.pk}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
