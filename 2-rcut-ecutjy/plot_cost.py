#!/usr/bin/env python
"""What the parameter choice costs: wall time against accuracy.

Left  -- total time of the four primitive-basis SCFs, versus r_cut, one curve per ecutjy.
Right -- the same points as error against cost, which is where the choice is actually
         made: the useful parameter sets are those on the lower-left frontier.

Reads only `data/timings.csv` and `data/tsw_vs_pw.csv`, so it needs no database.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
KCAL = 43.364
STYLE = {100.0: ("#c0392b", "s"), 125.0: ("#2471a3", "o"), 150.0: ("#1e8449", "^")}


def read(name: str) -> list[dict]:
    with (DATA / name).open() as handle:
        return list(csv.DictReader(l for l in handle if not l.startswith("#")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="tsw_cost.png")
    args = ap.parse_args()

    timing = read("timings.csv")
    energy = {(float(r["ecutjy_Ry"]), float(r["r_cut_AU"])): float(r["dE_meV_per_atom"])
              for r in read("tsw_vs_pw.csv")}

    cost = {}
    for r in timing:
        cost.setdefault((float(r["ecutjy_Ry"]), float(r["r_cut_AU"])), 0.0)
        cost[(float(r["ecutjy_Ry"]), float(r["r_cut_AU"]))] += float(r["wall_s"]) / 60.0

    plt.rcParams.update({"font.size": 11, "axes.linewidth": 1.1,
                         "xtick.direction": "in", "ytick.direction": "in",
                         "xtick.top": True, "ytick.right": True,
                         "legend.frameon": False, "savefig.dpi": 300,
                         "savefig.bbox": "tight"})
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.0))

    ax = axes[0]
    for e in sorted({k[0] for k in cost}):
        pts = sorted([(k[1], v) for k, v in cost.items() if k[0] == e])
        colour, marker = STYLE.get(e, ("k", "o"))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=colour, lw=1.5)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker, color=colour, ms=7,
                mfc="white", mew=1.5, label=rf"$E_{{\rm cut}}^{{\rm jY}}$ = {e:g} Ry")
    ax.set_xlabel(r"$r_{\rm cut}$  (a.u.)")
    ax.set_ylabel("wall time of the 4 SCFs  (min)")
    ax.set_title("cost", fontsize=11)
    ax.legend(loc="upper left", fontsize=9.5)
    ax.grid(alpha=0.25)
    ax.set_xticks([9, 10, 11, 12])

    ax = axes[1]
    for e in sorted({k[0] for k in cost}):
        pts = [(cost[k], energy[k]) for k in sorted(cost) if k[0] == e and k in energy]
        colour, marker = STYLE.get(e, ("k", "o"))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=colour, lw=1.2,
                alpha=0.7)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker, color=colour, ms=7,
                mfc="white", mew=1.5)
        for (c, d), rc in zip(pts, [k[1] for k in sorted(cost) if k[0] == e and k in energy]):
            ax.annotate(f"{rc:g}", (c, d), textcoords="offset points", xytext=(6, -3),
                        fontsize=7.5, color=colour)
    ax.axhline(KCAL, color="0.25", ls="--", lw=1.1)
    ax.annotate(r"1 kcal/mol = 43.4 meV/atom", xy=(ax.get_xlim()[0] if ax.get_xlim()[0] else 20, KCAL),
                xytext=(0, 5), textcoords="offset points", fontsize=9, color="0.15")
    ax.set_yscale("log")
    ax.set_xlabel("wall time of the 4 SCFs  (min)")
    ax.set_ylabel(r"$|E_{\rm TSW}-E_{\rm PW}|$  (meV/atom)")
    ax.set_title("error against cost  (labels: $r_{\\rm cut}$)", fontsize=11)
    ax.grid(alpha=0.25, which="both")

    fig.tight_layout()
    out = HERE / args.out
    fig.savefig(out)
    print(f"wrote {out}")
    print(f"\n{'ecutjy':>7}{'r_cut':>7}{'min':>9}{'dE meV/at':>12}{'kcal/at':>9}")
    for (e, rc) in sorted(cost):
        d = energy.get((e, rc))
        print(f"{e:>7g}{rc:>7g}{cost[(e, rc)]:>9.1f}"
              f"{(d if d else float('nan')):>12.1f}{(d/KCAL if d else float('nan')):>9.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
