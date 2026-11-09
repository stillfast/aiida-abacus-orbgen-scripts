#!/usr/bin/env python
"""Combine cost and accuracy into one table -- the data behind tsw_cost.png.

Two existing CSVs are enough (`data/timings.csv` and `data/tsw_vs_pw.csv`), so this
needs no database.  Kept as a script rather than a hand-written file so the numbers
cannot drift from their sources.

    python export_cost.py --out 2-rcut-ecutjy/data/cost_vs_accuracy.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent / "2-rcut-ecutjy" / "data"
KCAL = 43.364
#: the bar the campaign is judged against
BAR_MEV = KCAL


def read(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(l for l in handle if not l.startswith("#")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(DATA / "cost_vs_accuracy.csv"))
    args = ap.parse_args()

    timing = read(DATA / "timings.csv")
    energy = {(float(r["ecutjy_Ry"]), float(r["r_cut_AU"])):
              (float(r["dE_meV_per_atom"]), float(r["dE_kcal_per_atom"]), r["pk"])
              for r in read(DATA / "tsw_vs_pw.csv")}

    cost, monomer, iters = {}, {}, {}
    for r in timing:
        key = (float(r["ecutjy_Ry"]), float(r["r_cut_AU"]))
        cost[key] = cost.get(key, 0.0) + float(r["wall_s"]) / 60.0
        iters[key] = iters.get(key, 0) + int(r["n_scf_iter"])
        if "monomer" in r["geometry"]:
            monomer[key] = float(r["wall_s"]) / 60.0

    rows = []
    for key in sorted(cost):
        e, rc = key
        d_mev, d_kcal, pk = energy.get(key, (None, None, ""))
        rows.append({
            "ecutjy_Ry": f"{e:g}", "r_cut_AU": f"{rc:g}",
            "n_scf": sum(1 for r in timing
                         if float(r["ecutjy_Ry"]) == e and float(r["r_cut_AU"]) == rc),
            "total_wall_min": round(cost[key], 1),
            "monomer_wall_min": round(monomer.get(key, 0.0), 1),
            "total_scf_iterations": iters[key],
            "dE_meV_per_atom": d_mev if d_mev is not None else "",
            "dE_kcal_per_atom": d_kcal if d_kcal is not None else "",
            "verdict": ("pass" if d_mev is not None and d_mev <= BAR_MEV else "fail")
                        if d_mev is not None else "",
            "workchain_pk": pk,
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        handle.write("# Cost against accuracy for the (r_cut, ecutjy) scan at l_max 4.\n")
        handle.write("# total_wall_min = sum of the four primitive-basis SCFs; the time is\n")
        handle.write("# ABACUS's own 'Total Time' line, not mtime-ctime (which is ~0 for a\n")
        handle.write("# cache hit).  dE is |E_TSW - E_PW| per atom; the bar is 1 kcal/mol\n")
        handle.write("# = 43.364 meV/atom.  Built by export_cost.py from timings.csv and\n")
        handle.write("# tsw_vs_pw.csv.\n")
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")
    print(f"\n{'ecutjy':>7}{'r_cut':>7}{'min':>9}{'dE meV/at':>12}{'kcal/at':>9}{'verdict':>9}")
    for r in rows:
        print(f"{r['ecutjy_Ry']:>7}{r['r_cut_AU']:>7}{r['total_wall_min']:>9.1f}"
              f"{r['dE_meV_per_atom']:>12}{r['dE_kcal_per_atom']:>9}{r['verdict']:>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
