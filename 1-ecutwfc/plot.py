#!/usr/bin/env python
"""Plot the stage-1 cutoff ladder: energy vs ecutwfc.

Two views, because the raw total energies are ~-4951 eV and the whole convergence is a
few meV/atom:

  left   E(ecutwfc) - E(ecutwfc_max), i.e. the distance to the highest cutoff, in
         meV/atom on a log axis, with the convergence threshold drawn in;
  right  the neighbour differences |E(i) - E(i-1)| that the selection rule actually
         uses, as bars.

Every CSV is one reference geometry; the rule has to hold for all of them.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from utils.analysis import LadderRow, adjacent_differences   # noqa: E402

COLORS = ["#2471a3", "#c0392b", "#1e8449", "#8e44ad"]


def read_csv(path: Path) -> list[LadderRow]:
    rows = []
    with open(path, newline="") as handle:
        for rec in csv.DictReader(handle):
            rows.append(LadderRow(value=float(rec["ecutwfc"]),
                                  energy=float(rec["energy_eV"]),
                                  natoms=int(rec.get("natoms", 1) or 1)))
    return sorted(rows, key=lambda r: r.value)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tables", nargs="+", help="CSV files: ecutwfc,energy_eV[,natoms]")
    ap.add_argument("--tolerance", type=float, default=2.0, help="meV/atom")
    ap.add_argument("--out", default="ecutwfc_convergence.png")
    args = ap.parse_args()

    ladders = [(Path(t).stem, read_csv(Path(t))) for t in args.tables]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2))

    for i, (label, rows) in enumerate(ladders):
        cut = [r.value for r in rows]
        ref = rows[-1].per_atom()
        dev = [(r.per_atom() - ref) * 1000.0 for r in rows]
        colour = COLORS[i % len(COLORS)]
        ax.plot(cut, [abs(d) for d in dev], "o-", color=colour, mfc="white", ms=7,
                lw=1.6, label=f"{label}  ({rows[0].natoms} atoms)")
        diffs = adjacent_differences(rows)
        xs = [d["to"] for d in diffs]
        ys = [d["abs_mev_per_atom"] for d in diffs]
        ax2.bar([x + (i - 0.5) * 6 for x in xs], ys, width=5.5, color=colour,
                alpha=0.85, edgecolor="k", lw=0.6, label=label)

    ax.axhline(args.tolerance, color="red", ls="--", lw=1.3)
    ax.text(ax.get_xlim()[0] if ax.get_xlim()[0] else 100, args.tolerance * 1.15,
            f"{args.tolerance:g} meV/atom", color="red", fontsize=9)
    ax.set_yscale("log")
    ax.set_xlabel(r"$E_{\rm cut}$ (Ry)", fontsize=12)
    ax.set_ylabel(r"$|E(E_{\rm cut}) - E(E_{\rm cut}^{\max})|$  (meV/atom)", fontsize=11)
    ax.set_title("distance to the highest cutoff", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.25, which="both")

    ax2.axhline(args.tolerance, color="red", ls="--", lw=1.3)
    ax2.set_xlabel(r"$E_{\rm cut}$ (Ry)   (bar sits at the upper end of the pair)", fontsize=11)
    ax2.set_ylabel("neighbour difference (meV/atom)", fontsize=11)
    ax2.set_title("what the selection rule measures", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.25, axis="y")

    fig.suptitle("ABACUS plane-wave cutoff convergence, U2 dimers", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = HERE.parent / "demo" / args.out
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")

    print(f"\n{'E_cut':>7}" + "".join(f"{lbl+' dev':>16}" for lbl, _ in ladders))
    for k, cut in enumerate([r.value for r in ladders[0][1]]):
        line = f"{cut:>7g}"
        for _, rows in ladders:
            if k < len(rows):
                ref = rows[-1].per_atom()
                line += f"{(rows[k].per_atom() - ref) * 1000:>16.2f}"
        print(line)
    print("\n(deviation from the highest cutoff, meV/atom)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
