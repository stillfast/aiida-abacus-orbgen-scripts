#!/usr/bin/env python
"""One entry point for the whole campaign: submit -> wait -> analyse -> plot.

Stages
------
1  ecutwfc     plane-wave cutoff ladder          (PW only)
2  rcut-ecutjy (r_cut, ecutjy) grid at l_max=4    (NSW + SCF + spillage fit per point)
3  eos         V0 / B0 of the chosen orbital      (abacus.orbgen.eos)
   eta         band-structure error at V0          (orbgen.eta)

Every stage is a thin wrapper around the scripts that already exist and are individually
tested, so nothing is re-implemented here -- this file only decides the order and passes
the parameters along:

    1-ecutwfc/{launch,analyze,plot}.py
    2-rcut-ecutjy/{submit,compare_orbs,plot_tsw_vs_pw}.py
    3-eos/{launch,analyze,eta}.py

Usage
-----
    python run_campaign.py --plan                 # print what each stage would do
    python run_campaign.py --stage 1 --submit     # run the cutoff ladder
    python run_campaign.py --stage 2 --submit     # sweep (r_cut, ecutjy)
    python run_campaign.py --stage analyze        # every figure, from AiiDA, no jobs
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
KCAL = 43.364

#: the parameter grid the campaign uses for uranium
RCUTS = [9.0, 10.0, 11.0, 12.0]
ECUTJYS = [100.0, 125.0, 150.0]
L_MAX = 4
ECUTWFC = 180.0
ORBGEN_JSON = HERE.parent / "new_nao" / "orb_gen_siab" / "orbgen.json"
CONTROL_JSON = HERE.parent / "project" / "u_14ve" / "2-nao_gen" / "orbgen.json"
TEMPLATE = 463407
EOS_REPORTS = HERE.parent.parent / "bcc_uranium" / "aiida-uranium-alpha" / "2-eos" / "reports"


def run(description: str, cmd: list[str], dry: bool) -> int:
    print(f"\n\033[1m{description}\033[0m")
    print("   " + " ".join(str(c) for c in cmd))
    if dry:
        return 0
    result = subprocess.run(cmd, cwd=HERE)
    if result.returncode != 0:
        print(f"   !! exited {result.returncode}")
    return result.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=["1", "2", "3", "analyze", "all"], default="analyze")
    ap.add_argument("--submit", action="store_true",
                    help="really submit; without it every stage is a dry run")
    ap.add_argument("--plan", action="store_true", help="print the plan and stop")
    ap.add_argument("--ecutwfc", type=float, default=ECUTWFC)
    ap.add_argument("--rcuts", type=float, nargs="+", default=RCUTS)
    ap.add_argument("--ecutjys", type=float, nargs="+", default=ECUTJYS)
    ap.add_argument("--l-max", type=int, default=L_MAX)
    ap.add_argument("--mem-gb", type=float, default=190.0)
    ap.add_argument("--queue", default="q_ysuan")
    args = ap.parse_args()

    dry = not args.submit
    stages = ["1", "2", "3", "analyze"] if args.stage == "all" else [args.stage]

    print("=" * 78)
    print("ABACUS NAO parameter campaign")
    print(f"  ecutwfc        : {args.ecutwfc:g} Ry")
    print(f"  r_cut x ecutjy : {args.rcuts} x {args.ecutjys}  (l_max = {args.l_max})")
    print(f"  orbgen config  : {ORBGEN_JSON}")
    print(f"  mode           : {'DRY RUN' if dry else 'SUBMITTING'}")
    print("=" * 78)

    codes = []
    if "1" in stages:
        run("stage 1  ecutwfc ladder (PW only)",
            [PY, "1-ecutwfc/launch.py", "--out", "1-ecutwfc/plan.json"] +
            (["--submit"] if args.submit else []), dry)

    if "2" in stages:
        for r in args.rcuts:
            for e in args.ecutjys:
                run(f"stage 2  r_cut={r:g} ecutjy={e:g}",
                    [PY, "2-rcut-ecutjy/submit.py", "--orbgen-json", str(ORBGEN_JSON),
                     "--template", str(TEMPLATE), "--r-cut", str(r),
                     "--ecutjy", str(e), "--l-max", str(args.l_max),
                     "--queue", args.queue, "--mem-gb", str(args.mem_gb)] +
                    ([] if args.submit else ["--dry-run"]), dry)
        run("stage 2  control point r_cut=10 ecutjy=150 (project config)",
            [PY, "2-rcut-ecutjy/submit.py", "--orbgen-json", str(CONTROL_JSON),
             "--template", str(TEMPLATE), "--r-cut", "10", "--ecutjy", "150",
             "--l-max", str(args.l_max), "--group", "orbgen-control-r10-j150"] +
            ([] if args.submit else ["--dry-run"]), dry)

    if "3" in stages:
        run("stage 3  equation of state (one orbital)",
            [PY, "3-eos/launch.py", "--ecutwfc", str(args.ecutwfc),
             "--queue", "d2_ys", "--mem-gb", "1500"] +
            (["--submit"] if args.submit else []), dry)
        run("stage 3  eta at the equilibrium point",
            [PY, "3-eos/eta.py", "--help"], dry)

    if "analyze" in stages:
        run("analyse  cutoff convergence figure",
            [PY, "1-ecutwfc/plot.py", "demo/ecutwfc_ladder_s463371.csv",
             "demo/ecutwfc_ladder_s463378.csv"], dry)
        run("analyse  TSW vs PW: energy error against r_cut",
            [PY, "2-rcut-ecutjy/plot_tsw_vs_pw.py"], dry)
        run("analyse  eta / V0 / B0 selection figure",
            [PY, "3-eos/analyze.py", "--report-dir", str(EOS_REPORTS)], dry)

    print("\n" + "=" * 78)
    if dry:
        print("Dry run: nothing was submitted.  Add --submit to launch stages 1-3.")
    else:
        print("Submitted.  Track with:  verdi process list -a -p 1")
        print("Figures appear under 1-ecutwfc/, 2-rcut-ecutjy/ and 3-eos/.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
