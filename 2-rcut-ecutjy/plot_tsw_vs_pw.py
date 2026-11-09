#!/usr/bin/env python
"""TSW (NSW primitive) basis vs plane waves: total-energy error against r_cut.

x = r_cut (a.u.), y = |E_TSW - E_PW| in meV/atom on a **linear** axis, one curve per
ecutjy.  Both axes are per atom, matching the paper's Table II convention
("总能量, eV/atom") and its chemical-accuracy bar of 1 kcal/mol = 43.364 meV/atom.

Note the convention: the project's older `rcut_lmax` tables quoted the error per
**dimer**, and 1 kcal/mol there is 43.364 meV per dimer = 21.68 meV/atom, i.e. twice as
strict.  Mixing the two shifts every verdict by a factor of two, so the figure states
the per-atom value and the code keeps the conversion explicit.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator

KCAL_MEV = 43.364


def energy_of(node):
    rf = node.outputs.retrieved
    for sub in ("OUT.aiida", "OUT.ABACUS"):
        try:
            txt = rf.get_object_content(f"{sub}/running_scf.log")
        except Exception:                                        # noqa: BLE001
            continue
        hits = re.findall(r"!FINAL_ETOT_IS\s+(-?[0-9.]+)", txt)
        if hits:
            return float(hits[-1])
    return None


def collect(pw_refs: dict[str, float]) -> list[dict]:
    from aiida import load_profile
    from aiida.orm import Group

    load_profile("aiida_profile")
    rows, seen = [], set()
    # the large-memory points live in their own group, so scan every campaign group
    for label in ("orbgen-rcut-ecutjy", "orbgen-rcut-ecutjy-d2",
                  "orbgen-control-r10-j150"):
        try:
            group = Group.collection.get(label=label)
        except Exception:                                        # noqa: BLE001
            continue
        for node in group.nodes:
            if type(node).__name__ != "WorkChainNode":
                continue
            if node.process_state.value != "finished" or node.exit_status != 0:
                continue
            s = node.inputs.settings.get_dict()
            key = (s["ecutjy"], s["r_cut"])
            if key in seen:
                continue
            energies = {}
            for child in node.called:
                if type(child).__name__ != "CalcJobNode":
                    continue
                m = re.search(r"dimer_(\d)_(\d+)_", child.label or "")
                if m:
                    energies[f"{m.group(1)}.{m.group(2)}"] = energy_of(child)
            deltas = [(energies[b] - e) / 2 * 1000.0 for b, e in pw_refs.items()
                      if energies.get(b) is not None]
            if not deltas:
                continue
            seen.add(key)
            rows.append({"ecutjy": s["ecutjy"], "r_cut": s["r_cut"],
                         "dE": sum(deltas) / len(deltas), "pk": node.pk})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tsw_vs_pw.png")
    ap.add_argument("--from-csv", default=None,
                    help="plot from a saved CSV instead of querying AiiDA, so the "
                         "figure is reproducible without the database")
    ap.add_argument("--csv-out", default=None,
                    help="also write the collected points to this CSV")
    args = ap.parse_args()

    pw = {"2.10": -4951.807006023504, "2.40": -4952.064018093108}   # ecutwfc 180
    if args.from_csv:
        import csv
        rows = []
        with Path(args.from_csv).open() as handle:
            for row in csv.DictReader(r for r in handle if not r.startswith("#")):
                rows.append({"ecutjy": float(row["ecutjy_Ry"]),
                             "r_cut": float(row["r_cut_AU"]),
                             "dE": float(row["dE_meV_per_atom"]),
                             "pk": row.get("pk", "")})
        print(f"read {len(rows)} points from {args.from_csv}")
    else:
        rows = collect(pw)
    if not rows:
        print("no finished points")
        return 2

    if args.csv_out:
        import csv
        out_csv = Path(args.csv_out)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="") as handle:
            # comments are written as plain text, not through csv.writer, so that a
            # reader can simply skip every line that starts with '#'
            handle.write("# TSW (primitive NSW basis) vs plane waves, ecutwfc 180 Ry.\n")
            handle.write("# dE is per atom; the 1 kcal/mol bar is 43.364 meV/atom.\n")
            handle.write("# PW reference: 2.10 A = -4951.807006023504 eV, "
                         "2.40 A = -4952.064018093108 eV\n")
            handle.write("# pk = the abacus.orbgen.base workchain.\n")
            writer = csv.writer(handle)
            writer.writerow(["ecutjy_Ry", "r_cut_AU",
                             "dE_meV_per_atom", "dE_kcal_per_atom", "pk"])
            for r in sorted(rows, key=lambda x: (x["ecutjy"], x["r_cut"])):
                writer.writerow([f"{r['ecutjy']:g}", f"{r['r_cut']:g}",
                                 f"{r['dE']:.2f}", f"{r['dE']/KCAL_MEV:.3f}", r["pk"]])
        print(f"wrote {out_csv}")

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11,
        "axes.linewidth": 1.1, "xtick.direction": "in", "ytick.direction": "in",
        "xtick.top": True, "ytick.right": True, "xtick.major.size": 5,
        "ytick.major.size": 5, "xtick.minor.size": 2.6, "ytick.minor.size": 2.6,
        "xtick.minor.visible": True, "ytick.minor.visible": True,
        "legend.frameon": False, "savefig.dpi": 300, "savefig.bbox": "tight",
    })

    style = {100.0: ("#c0392b", "s"), 125.0: ("#2471a3", "o"), 150.0: ("#1e8449", "^")}
    fig, ax = plt.subplots(figsize=(5.2, 4.0))

    for e in sorted({r["ecutjy"] for r in rows}):
        sel = sorted([r for r in rows if r["ecutjy"] == e], key=lambda r: r["r_cut"])
        colour, marker = style.get(e, ("k", "o"))
        ax.plot([r["r_cut"] for r in sel], [r["dE"] for r in sel], "-",
                color=colour, lw=1.5, zorder=2)
        ax.plot([r["r_cut"] for r in sel], [r["dE"] for r in sel], marker,
                color=colour, ms=7, mfc="white", mew=1.5, zorder=3,
                label=rf"$E_{{\rm cut}}^{{\rm jY}}$ = {e:g} Ry")

    ax.axhline(KCAL_MEV, color="0.25", ls="--", lw=1.1, zorder=1)
    ax.annotate(r"1 kcal/mol = 43.4 meV/atom", xy=(9.0, KCAL_MEV),
                xytext=(0, 5), textcoords="offset points",
                fontsize=9.5, color="0.15", va="bottom")

    ax.set_xlabel(r"$r_{\rm cut}$  (a.u.)")
    ax.set_ylabel(r"$|E_{\rm TSW} - E_{\rm PW}|$  (meV/atom)")
    ax.set_xlim(8.6, 12.4)
    ax.set_ylim(0, 600)
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))
    ax.legend(loc="upper right", handlelength=1.6, borderaxespad=0.4)
    fig.tight_layout()

    out = Path(__file__).resolve().parent / args.out
    fig.savefig(out)
    print(f"wrote {out}")

    print(f"\n{'ecutjy':>7}{'r_cut':>7}{'dE meV/at':>12}{'kcal/mol/atom':>15}"
          f"{'kcal/mol/dimer':>16}")
    for r in sorted(rows, key=lambda x: (x["ecutjy"], x["r_cut"])):
        print(f"{r['ecutjy']:>7g}{r['r_cut']:>7g}{r['dE']:>12.1f}"
              f"{r['dE']/KCAL_MEV:>15.2f}{r['dE']*2/KCAL_MEV:>16.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
