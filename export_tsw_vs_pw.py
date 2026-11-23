#!/usr/bin/env python
"""TSW (primitive NSW) basis versus plane waves, on all four reference geometries.

The reference set is U2 at 2.10 / 2.40 / 2.80 A plus the monomer, in a 35 Bohr
(18.5212 A) cubic cell -- the same cell the NAO runs use.  Both sides are SCF total
energies with the same pseudopotential (U.pbe-n-nc.UPF, md5 shared with the NAO runs),
the same ecutwfc (180 Ry) and gamma_only, so the only difference is the basis.

    dE(geometry) = (E_TSW - E_PW) / n_atoms     meV/atom

and the headline number is the mean over the **three dimers**.  The monomer is reported
separately: it is the quantity that carries the r_cut error without cancellation
(kappa ~ 1), which is why the dimer mean alone hides part of the story.

    python export_tsw_vs_pw.py --out 2-rcut-ecutjy/data/tsw_vs_pw.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

KCAL = 43.364

#: all from AiiDA: 561552 (2.10), 561562 (2.40), 580303 (2.80), 580305 (monomer)
PW = {
    "2.10": -4951.807006023504,
    "2.40": -4952.064018093108,
    "2.80": -4950.826505580118,
    "monomer": -2473.881319189626,
}
GEOMETRIES = ("2.10", "2.40", "2.80")
GROUPS = ("orbgen-rcut-ecutjy", "orbgen-rcut-ecutjy-d2", "orbgen-control-r10-j150")


def energy(calc):
    for sub in ("OUT.aiida", "OUT.ABACUS"):
        try:
            text = calc.outputs.retrieved.get_object_content(f"{sub}/running_scf.log")
        except Exception:                                        # noqa: BLE001
            continue
        hits = re.findall(r"!FINAL_ETOT_IS\s+(-?[0-9.]+)", text)
        if hits:
            return float(hits[-1])
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="2-rcut-ecutjy/data/tsw_vs_pw.csv")
    args = ap.parse_args()

    from aiida import load_profile
    from aiida.orm import Group

    load_profile("aiida_profile")
    rows, seen = [], set()
    for label in GROUPS:
        try:
            group = Group.collection.get(label=label)
        except Exception:                                        # noqa: BLE001
            continue
        for wc in group.nodes:
            if type(wc).__name__ != "WorkChainNode":
                continue
            if wc.process_state.value != "finished" or wc.exit_status != 0:
                continue
            s = wc.inputs.settings.get_dict()
            key = (s["ecutjy"], s["r_cut"])
            if key in seen:
                continue
            seen.add(key)
            got = {}
            for child in wc.called:
                if type(child).__name__ != "CalcJobNode":
                    continue
                m = re.search(r"dimer_(\d)_(\d+)_", child.label or "")
                if m:
                    got[f"{m.group(1)}.{m.group(2)}"] = energy(child)
                elif "monomer" in (child.label or ""):
                    got["monomer"] = energy(child)
            d = {}
            for geo, epw in PW.items():
                e = got.get(geo)
                if e is None:
                    continue
                natoms = 1 if geo == "monomer" else 2
                d[geo] = (e - epw) / natoms * 1000.0
            if not all(g in d for g in GEOMETRIES):
                continue
            mean3 = sum(d[g] for g in GEOMETRIES) / len(GEOMETRIES)
            rows.append({
                "ecutjy_Ry": f"{s['ecutjy']:g}", "r_cut_AU": f"{s['r_cut']:g}",
                **{f"dE_{g}_meV_per_atom": round(d[g], 2) for g in GEOMETRIES},
                "dE_monomer_meV_per_atom": round(d["monomer"], 2) if "monomer" in d else "",
                "dE_mean3_meV_per_atom": round(mean3, 2),
                "dE_mean3_kcal_per_atom": round(mean3 / KCAL, 3),
                "workchain_pk": wc.pk,
            })
    rows.sort(key=lambda r: (float(r["ecutjy_Ry"]), float(r["r_cut_AU"])))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        handle.write("# TSW (primitive, uncontracted NSW) basis vs plane waves.\n")
        handle.write("# Same 35 Bohr (18.5212 A) cubic cell, same pseudopotential\n")
        handle.write("# (U.pbe-n-nc.UPF), ecutwfc 180 Ry, gamma_only.  Only the basis differs.\n")
        handle.write("# dE = (E_TSW - E_PW) / n_atoms, meV/atom.  The headline number is\n")
        handle.write("# dE_mean3, the mean over the three DIMERS; the monomer is separate\n")
        handle.write("# because its r_cut error does not cancel (kappa ~ 1).\n")
        handle.write("# PW (eV): 2.10 = -4951.807006023504, 2.40 = -4952.064018093108,\n")
        handle.write("#          2.80 = -4950.826505580118, monomer = -2473.881319189626\n")
        handle.write("# 1 kcal/mol = 43.364 meV/atom.\n")
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")
    print(f"\n{'ecutjy':>7}{'r_cut':>7}{'2.10':>8}{'2.40':>8}{'2.80':>8}{'mean3':>9}{'monomer':>10}{'kcal':>8}")
    for r in rows:
        print(f"{r['ecutjy_Ry']:>7}{r['r_cut_AU']:>7}"
              f"{r['dE_2.10_meV_per_atom']:>8}{r['dE_2.40_meV_per_atom']:>8}"
              f"{r['dE_2.80_meV_per_atom']:>8}{r['dE_mean3_meV_per_atom']:>9}"
              f"{r['dE_monomer_meV_per_atom']:>10}{r['dE_mean3_kcal_per_atom']:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
