#!/usr/bin/env python
"""Why DZP: eta, B0 and V0 of every basis against plane waves, in one figure.

Reads the four EOS reports in ``reports/`` (already computed, PKs in ``output.json``) and
the occupied-band eta from ``reports/band_analysis.json``, then draws the three selection
metrics side by side:

  eta        band-structure error at the equilibrium volume   (<= 20 meV)
  |dB0|/B0   bulk modulus error vs PW                          (a few %)
  |dV0|/V0   equilibrium volume error vs PW                    (<< 1 %)

The chemical-accuracy bar used for the total energy is 1 kcal/mol = 43.4 meV/atom.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
#: where the finished EOS reports live.  Override with --report-dir to read a campaign
#: that was produced elsewhere (e.g. bcc_uranium/aiida-uranium-alpha/2-eos/reports).
REPORTS = HERE / "reports"
KCAL = 43.364
NATOMS = 4

BASES = ["pw", "sz", "dzp", "tzdp"]
LABEL = {"pw": "PW", "sz": "SZ\n2s1p1d1f", "dzp": "DZP\n4s2p2d2f1g", "tzdp": "TZDP\n6s3p3d3f2g"}
COLOUR = {"pw": "0.15", "sz": "#c0392b", "dzp": "#2471a3", "tzdp": "#1e8449"}


def read_eos() -> dict:
    out = {}
    for basis in BASES:
        files = sorted(REPORTS.glob(f"report_{basis}_*.md"))
        if not files:
            continue
        text = files[-1].read_text()
        def val(key):
            m = re.search(rf"\| {key} \| ([-\d.]+)", text)
            return float(m.group(1)) if m else None
        out[basis] = {"V0": val("volume_gs"), "V0_atom": val("volume_gs_per_atom"),
                      "B0": val("bulk_modulus"), "BP": val("bulk_deriv"),
                      "E0": val("energy_gs")}
    return out


def read_eta() -> tuple[dict, dict, bool]:
    """-> (eta, eta10, eta10_valid).

    eta comes from `band_analysis.json`; eta_10 from `eta10_analysis.json`, which also
    records whether the spectrum reaches eps_F + 10 eV.  When it does not, eta_10
    degenerates into an unweighted RMS over all bands and must not be quoted -- the flag
    is carried through to the figure.
    """
    eta, eta10, valid = {}, {}, True
    path = REPORTS / "band_analysis.json"
    if path.is_file():
        eta = {r["basis"]: r["eta_meV"] for r in json.loads(path.read_text()).get("rows", [])}
    path = REPORTS / "eta10_analysis.json"
    if path.is_file():
        data = json.loads(path.read_text())
        eta10 = {r["basis"]: r["eta10_meV"] for r in data.get("rows", [])}
        valid = bool(data.get("valid", True))
    return eta, eta10, valid


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report-dir", default=None,
                    help="directory holding report_<basis>_*.md and band_analysis.json")
    args = ap.parse_args()
    global REPORTS
    if args.report_dir:
        REPORTS = Path(args.report_dir).resolve()

    eos, (eta, eta10, eta10_ok) = read_eos(), read_eta()
    if "pw" not in eos:
        print("no PW EOS report")
        return 2
    pw = eos["pw"]

    print(f"{'basis':<6}{'V0/atom':>10}{'dV0 (%)':>10}{'B0 (GPa)':>11}{'dB0 (%)':>10}"
          f"{'BP':>7}{'E0/atom':>12}{'dE (meV)':>10}{'eta (meV)':>11}{'eta10 (meV)':>13}")
    for b in BASES:
        if b not in eos:
            continue
        e = eos[b]
        dV = 100 * (e["V0_atom"] / pw["V0_atom"] - 1)
        dB = 100 * (e["B0"] / pw["B0"] - 1)
        e0 = e["E0"] / NATOMS
        dE = (e["E0"] - pw["E0"]) / NATOMS * 1000
        print(f"{b:<6}{e['V0_atom']:>10.4f}{dV:>+10.3f}{e['B0']:>11.2f}{dB:>+10.2f}"
              f"{e['BP']:>7.2f}{e0:>12.4f}{dE:>10.1f}{eta.get(b, float('nan')):>11.2f}"
              f"{eta10.get(b, float('nan')):>13.2f}")

    plt.rcParams.update({"font.size": 10, "axes.linewidth": 1.0,
                         "xtick.direction": "in", "ytick.direction": "in",
                         "xtick.top": True, "ytick.right": True,
                         "legend.frameon": False, "savefig.dpi": 300,
                         "savefig.bbox": "tight"})
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 3.5))
    shown = [b for b in BASES if b in eos]
    x = np.arange(len(shown))

    ax = axes[0]
    v_eta = [eta.get(b, np.nan) for b in shown]
    v_10 = [eta10.get(b, np.nan) for b in shown]
    ax.bar(x - 0.19, v_eta, width=0.36, color=[COLOUR[b] for b in shown],
           edgecolor="k", lw=0.6, label=r"$\eta$")
    ax.bar(x + 0.19, v_10, width=0.36, color=[COLOUR[b] for b in shown],
           alpha=0.45, hatch="///", edgecolor="k", lw=0.6,
           label=r"$\eta_{10}$" + ("" if eta10_ok else " (invalid)"))
    ax.axhline(20, color="red", ls="--", lw=1.1)
    ax.text(-0.45, 22, "20 meV", color="red", fontsize=8.5)
    ax.set_ylabel(r"$\eta$  (meV)")
    ax.set_title(r"occupied bands ($\eta$) and $\varepsilon_F$+10 eV ($\eta_{10}$)",
                 fontsize=9.5)
    ax.legend(fontsize=7.5, loc="upper right")

    ax = axes[1]
    vals = [100 * (eos[b]["V0_atom"] / pw["V0_atom"] - 1) for b in shown]
    ax.bar(x, vals, color=[COLOUR[b] for b in shown], edgecolor="k", lw=0.6, width=0.62)
    ax.axhline(0, color="k", lw=0.8)
    for xi, v in zip(x, vals):
        ax.annotate(f"{v:+.2f}", (xi, v), textcoords="offset points",
                    xytext=(0, 4 if v >= 0 else -12), ha="center", fontsize=8)
    ax.set_ylabel(r"$\Delta V_0 / V_0$  (%)")
    ax.set_title("equilibrium volume", fontsize=10)

    ax = axes[2]
    vals = [100 * (eos[b]["B0"] / pw["B0"] - 1) for b in shown]
    ax.bar(x, vals, color=[COLOUR[b] for b in shown], edgecolor="k", lw=0.6, width=0.62)
    ax.axhline(0, color="k", lw=0.8)
    for xi, v in zip(x, vals):
        ax.annotate(f"{v:+.2f}", (xi, v), textcoords="offset points",
                    xytext=(0, 4 if v >= 0 else -12), ha="center", fontsize=8)
    ax.set_ylabel(r"$\Delta B_0 / B_0$  (%)")
    ax.set_title("bulk modulus", fontsize=10)

    for ax in axes:
        ax.set_xticks(x, [LABEL[b] for b in shown], fontsize=8.5)
        ax.grid(alpha=0.2, axis="y")
    fig.suptitle(r"basis selection for $\alpha$-U: $\eta$ / $\eta_{10}$, $V_0$, $B_0$ "
                 r"against plane waves", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = HERE / "basis_selection.png"
    fig.savefig(out)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
