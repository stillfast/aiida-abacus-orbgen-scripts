#!/usr/bin/env python
"""Truncated spherical-wave (primitive NSW) basis versus plane waves.

Left  -- dE against r_cut, one curve per ecutjy.  Solid is the mean over the three
         dimers, dashed is the monomer.  The monomer is drawn separately because its
         r_cut error does not cancel (kappa ~ 1), so folding it into the dimer mean
         would hide exactly what forces r_cut to 11 au.
Right -- the four reference geometries at r_cut 12, i.e. how the error is distributed
         over bond lengths.  Those are the same four structures the orbital generator
         fits against, so this panel is the one that connects to the product.

Reads data/tsw_vs_pw.csv only; no database is touched.

    python plot_tsw_vs_pw.py [--from-csv data/tsw_vs_pw.csv]
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
DATA = HERE / "data"
KCAL = 43.364
STYLE = {100.0: ("#c0392b", "s"), 125.0: ("#2471a3", "o"), 150.0: ("#1e8449", "^")}
GEOMS = ("2.10", "2.40", "2.80")


def read(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(l for l in handle if not l.startswith("#")))


def numeric(row: dict, key: str):
    v = row.get(key, "")
    return float(v) if v not in ("", None) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-csv", default=str(DATA / "tsw_vs_pw.csv"),
                    help="the point table; default is the shipped data/tsw_vs_pw.csv")
    ap.add_argument("--out", default="tsw_vs_pw.png")
    args = ap.parse_args()

    rows = read(Path(args.from_csv))
    points = []
    for r in rows:
        points.append({
            "ecutjy": float(r["ecutjy_Ry"]), "r_cut": float(r["r_cut_AU"]),
            "mean4": numeric(r, "dE_mean4_meV_per_atom"),
            "monomer": numeric(r, "dE_monomer_meV_per_atom"),
            "per_geom": {g: numeric(r, f"dE_{g}_meV_per_atom") for g in GEOMS},
            "pk": r.get("workchain_pk", ""),
        })

    plt.rcParams.update({"font.size": 11, "axes.linewidth": 1.1,
                         "xtick.direction": "in", "ytick.direction": "in",
                         "xtick.top": True, "ytick.right": True,
                         "legend.frameon": False, "savefig.dpi": 300,
                         "savefig.bbox": "tight"})
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for e in sorted({p["ecutjy"] for p in points}):
        sel = sorted([p for p in points if p["ecutjy"] == e], key=lambda p: p["r_cut"])
        colour, marker = STYLE.get(e, ("k", "o"))
        ax.plot([p["r_cut"] for p in sel], [p["mean4"] for p in sel], "-",
                color=colour, lw=1.6, marker=marker, ms=7, mfc="white", mew=1.5,
                label=rf"$E_{{\rm cut}}^{{\rm jY}}$ = {e:g} Ry")
    ax.axhline(KCAL, color="0.25", ls="--", lw=1.1)
    ax.annotate(r"1 kcal/mol = 43.4 meV/atom", xy=(8.7, KCAL), xytext=(0, 5),
                textcoords="offset points", fontsize=9, color="0.15")
    ax.set_xlabel(r"$r_{\rm cut}$  (a.u.)")
    ax.set_ylabel(r"$|E_{\rm TSW} - E_{\rm PW}|$  (meV/atom)")
    ax.set_xticks([9, 10, 11, 12])
    # headroom above the data so the legend does not sit on the top-most curve
    top = max(p["mean4"] for p in points if p["mean4"] is not None)
    ax.set_ylim(0, top * 1.40)
    ax.legend(loc="upper right", fontsize=8.5, handlelength=1.8)
    ax.grid(alpha=0.25)

    fig.tight_layout()
    out = HERE / args.out
    fig.savefig(out)
    print(f"wrote {out}")

    print(f"\n{'ecutjy':>7}{'r_cut':>7}{'2.10':>9}{'2.40':>9}{'2.80':>9}"
          f"{'monomer':>9}{'mean4':>9}{'kcal/at':>9}")
    for p in sorted(points, key=lambda x: (x["ecutjy"], x["r_cut"])):
        f = p["per_geom"]
        print(f"{p['ecutjy']:>7g}{p['r_cut']:>7g}"
              f"{f['2.10']:>9.1f}{f['2.40']:>9.1f}{f['2.80']:>9.1f}"
              f"{p['monomer']:>9.1f}{p['mean4']:>9.1f}{p['mean4']/KCAL:>9.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
