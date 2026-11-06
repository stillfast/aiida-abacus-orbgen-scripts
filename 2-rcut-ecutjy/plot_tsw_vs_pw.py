#!/usr/bin/env python
"""TSW (NSW primitive) vs PW total-energy error vs r_cut, one curve per ecutjy.

Reads the finished ``abacus.orbgen.base`` workchains out of AiiDA: every one of them has
already run a *primitive-basis* SCF per reference geometry, so the only extra ingredient
is a plane-wave energy for the same geometry.  The PW references are taken from the
stage-1 cutoff ladder (ecutwfc 180), which uses the same 35 Bohr cell.

The criterion is the paper's eps_NSW^PW per dimer; the plot shows meV/atom with the
1 kcal/mol/dimer line drawn in.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

KCAL_MEV = 43.364


def energy_of(node):
    """`!FINAL_ETOT_IS` from the retrieved running log."""
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
    for label in ("orbgen-rcut-ecutjy", "orbgen-control-r10-j150"):
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
            deltas = [(energies[b] - e) / 2 * 1000.0             # meV/atom, 2 atoms
                      for b, e in pw_refs.items() if energies.get(b) is not None]
            if not deltas:
                continue
            seen.add(key)
            rows.append({"ecutjy": s["ecutjy"], "r_cut": s["r_cut"],
                         "dE_meV_atom": sum(deltas) / len(deltas),
                         "n": len(deltas), "pk": node.pk})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="tsw_vs_pw.png")
    args = ap.parse_args()

    # PW reference at ecutwfc 180, 35 Bohr cell (stage-1 ladder, PKs 561552 / 561562)
    pw = {"2.10": -4951.807006023504, "2.40": -4952.064018093108}

    rows = collect(pw)
    if not rows:
        print("no finished points")
        return 2

    method = {"100": "o-", "125": "s-", "150": "^-"}
    colours = {100.0: "#c0392b", 125.0: "#2471a3", 150.0: "#1e8449"}
    fig, ax = plt.subplots(figsize=(9.0, 6.0))
    for e in sorted({r["ecutjy"] for r in rows}):
        sel = sorted([r for r in rows if r["ecutjy"] == e], key=lambda r: r["r_cut"])
        ax.plot([r["r_cut"] for r in sel], [r["dE_meV_atom"] for r in sel],
                method.get(f"{e:g}", "o-"), color=colours.get(e, "k"), ms=8,
                mfc="white", mew=1.6, lw=1.8, label=f"ecutjy = {e:g} Ry")
        for r in sel:
            ax.annotate(f"{r['dE_meV_atom']/KCAL_MEV*2:.2f}",
                        (r["r_cut"], r["dE_meV_atom"]), textcoords="offset points",
                        xytext=(0, 9), fontsize=7.5, ha="center", color=colours.get(e, "k"))

    bar = KCAL_MEV / 2.0          # 1 kcal/mol per dimer, expressed per atom
    ax.axhline(bar, color="red", ls="--", lw=1.4)
    ax.text(ax.get_xlim()[0] if ax.get_xlim()[0] else 8.5, bar * 1.06,
            "1 kcal/mol per dimer", color="red", fontsize=9)
    ax.set_yscale("log")
    ax.set_xlabel(r"$r_{\rm cut}$  (a.u.)", fontsize=12)
    ax.set_ylabel(r"$|E_{\rm TSW}-E_{\rm PW}|$  (meV/atom)", fontsize=12)
    ax.set_title("TSW (primitive) basis vs plane waves, ecutwfc = 180 Ry\n"
                 "numbers above the markers: kcal/mol per U$_2$ dimer", fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    out = Path(__file__).resolve().parent / args.out
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")
    print(f"\n{'ecutjy':>7}{'r_cut':>7}{'dE meV/at':>12}{'kcal/dimer':>12}  pk")
    for r in sorted(rows, key=lambda x: (x["ecutjy"], x["r_cut"])):
        print(f"{r['ecutjy']:>7g}{r['r_cut']:>7g}{r['dE_meV_atom']:>12.1f}"
              f"{r['dE_meV_atom']/KCAL_MEV*2:>12.2f}  {r['pk']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
