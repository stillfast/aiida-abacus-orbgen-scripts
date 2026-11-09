#!/usr/bin/env python
"""Rewrite the parameter ladders in the *same* convention as tsw_vs_pw.csv.

Every campaign in this project recorded the primitive (TSW) basis SCF energies, so the
same quantity -- |E_LCAO - E_PW| per atom -- can be extracted from all of them.  This
script does that for the three ladders and writes them out next to tsw_vs_pw.csv, which
removes the last inconsistency in data/: previously the ladders quoted the atomization
energy difference (50 meV bar) while the figure quoted the error against plane waves
(43.364 meV bar).

    python export_vs_pw.py --out 2-rcut-ecutjy/data

The r_cut, ecutjy and l_max rows are the AiiDA workchains of the earlier LCAO-only
ladders (project/u_14ve/{rcut,ecutjy,lmax}/README.md).  Reusing them is sound: the
r_cut 9-12 points reproduce this project's own scan to 0.1 meV.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

KCAL = 43.364
#: plane-wave total energies at ecutwfc 180 Ry, 35 Bohr cell
PW = {"2.10": -4951.807006023504, "2.40": -4952.064018093108, "2.80": None}

#: (label, workchain PK, r_cut au, ecutjy Ry, l_max)
LADDERS = {
    "rcut": [("8", 468364, 8, 150, 4), ("9", 468415, 9, 150, 4),
             ("10", 468457, 10, 150, 4), ("11", 468485, 11, 150, 4),
             ("12", 468557, 12, 150, 4)],
    "ecutjy": [("100", 468738, 12, 100, 4), ("125", 468769, 12, 125, 4),
               ("150", 468557, 12, 150, 4)],
    "lmax": [("3", 468814, 12, 150, 3), ("4", 468557, 12, 150, 4)],
}


def energy(calc):
    rf = calc.outputs.retrieved
    for sub in ("OUT.aiida", "OUT.ABACUS"):
        try:
            text = rf.get_object_content(f"{sub}/running_scf.log")
        except Exception:                                        # noqa: BLE001
            continue
        hits = re.findall(r"!FINAL_ETOT_IS\s+(-?[0-9.]+)", text)
        if hits:
            return float(hits[-1])
    return None


def walk(node, acc):
    """Collect every CalcJobNode energy under `node`, keyed by bond length."""
    from aiida.orm import CalcJobNode
    for child in getattr(node, "called", []):
        if isinstance(child, CalcJobNode):
            try:
                atoms = child.inputs.structure.get_ase()
                if len(atoms) == 1:
                    continue
                z = sorted(float(p[2]) for p in atoms.positions)
                key = f"{z[1] - z[0]:.2f}"
            except Exception:                                    # noqa: BLE001
                continue
            e = energy(child)
            if e is not None:
                acc.setdefault(key, []).append(e)
        else:
            walk(child, acc)


def vs_pw(acc):
    out = {}
    for bl, epw in PW.items():
        if epw is None or bl not in acc:
            continue
        out[bl] = (max(acc[bl]) - epw) / 2.0 * 1000.0     # meV per atom, 2 atoms
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="2-rcut-ecutjy/data")
    args = ap.parse_args()

    from aiida import load_profile
    from aiida.orm import load_node

    load_profile("aiida_profile")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for name, entries in LADDERS.items():
        rows = []
        for label, pk, r_cut, ecutjy, l_max in entries:
            node = load_node(pk)
            acc = {}
            walk(node, acc)
            d = vs_pw(acc)
            rows.append({"label": label, "pk": pk, "r_cut_AU": r_cut,
                         "ecutjy_Ry": ecutjy, "l_max": l_max,
                         **{f"dE_{bl}_meV_per_atom": (round(v, 1) if bl in d else "")
                            for bl, v in [(b, d.get(b)) for b in ("2.10", "2.40")]}})
            print(f"  {name} {label:>4}  pk={pk}  " +
                  "  ".join(f"{k.split('_')[1]}: {v:.1f}" for k, v in
                            [(f"dE_{b}", d[b]) for b in sorted(d)]) if d else "  (no PW pair)")

        path = out / f"{name}_ladder.csv"
        with path.open("w", newline="") as handle:
            handle.write(f"# {name} ladder in the SAME convention as tsw_vs_pw.csv:\n")
            handle.write("# |E_LCAO - E_PW| per atom, meV.  1 kcal/mol = 43.364 meV/atom.\n")
            handle.write("# PW reference at ecutwfc 180 Ry, 35 Bohr cell:\n")
            handle.write("#   2.10 A = -4951.807006023504 eV,  2.40 A = -4952.064018093108 eV\n")
            handle.write("# Only the 2.10/2.40 A geometries have a PW run, so the 2.80 A\n")
            handle.write("# column of the old tables is not reproduced here.\n")
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {path} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
