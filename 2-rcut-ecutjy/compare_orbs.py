#!/usr/bin/env python
"""Compare AiiDA-generated orbitals against a known-good reference set.

Two kinds of difference matter, and they mean different things:

  * **header / metadata** -- ``ecutjy``, ``r_cut``, ``nzeta`` (the number of radial
    functions per l), element, functional.  A mismatch here is a pipeline bug: the
    orbital does not describe the system you asked for.
  * **radial coefficients** -- the actual functions.  A mismatch here is either a
    different reference calculation (``ecutwfc``, k-mesh, geometry, bands) or a
    different fit (``spill_guess``, ``torch.lr``, ``max_steps``), i.e. a physics
    difference rather than a plumbing one.

The numbers printed let you tell them apart, and ``--reference`` is meant to be a set
produced by the *same* config through a different route (the SIAB CLI), which is the
only way to prove the AiiDA chain equivalent.

    python compare_orbs.py --aidaa-dir /tmp/generated --reference ../../project/u_14ve/2-nao_gen/naos/lmax4_rcut10
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np


def read_nao(path: Path) -> dict:
    """Read an ABACUS ``.orb`` file.

    Format (SIAB ``orbio.write_nao``): a short header with ``Element``, ``Ecut``,
    ``Rcut``, ``Nr``, ``dr``, ``Nzeta per l``, then one block per radial function:
    a line with ``l`` and the number of coefficients, followed by the values.
    """
    from SIAB.spillage.orbio import read_nao as _read

    data = _read(str(path))
    # SIAB returns {"chi": [ [nz_l0 functions], [nz_l1], ... ], "dr": ..., ...}
    return data


def describe(data: dict) -> dict:
    chi = data["chi"]
    return {
        "nzeta": [len(c) for c in chi],
        "n_r": len(chi[0][0]) if chi and chi[0] else 0,
        "dr": data.get("dr"),
        "element": data.get("element"),
        "ecut": data.get("ecut"),
        "rcut": data.get("rcut"),
    }


def compare(name: str, a: dict, b: dict) -> dict:
    da, db = describe(a), describe(b)
    out = {"name": name, "same_nzeta": da["nzeta"] == db["nzeta"],
           "nzeta_a": da["nzeta"], "nzeta_b": db["nzeta"],
           "max_rel": None, "rms_rel": None, "per_l": []}
    if not out["same_nzeta"]:
        return out
    worst = 0.0
    accum = []
    per_l = []
    for l, (la, lb) in enumerate(zip(a["chi"], b["chi"])):
        lw = 0.0
        for ya, yb in zip(la, lb):
            ya, yb = np.asarray(ya, float), np.asarray(yb, float)
            peak = max(np.abs(ya).max(), 1e-30)
            d = np.abs(ya - yb).max() / peak
            lw = max(lw, float(d))
            accum.extend(((ya - yb) / peak).tolist())
        per_l.append((l, lw))
        worst = max(worst, lw)
    out["max_rel"] = worst
    out["rms_rel"] = float(np.sqrt(np.mean(np.square(accum)))) if accum else None
    out["per_l"] = per_l
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated", required=True, help="directory of the new .orb files")
    ap.add_argument("--reference", required=True, help="directory of the known-good .orb files")
    ap.add_argument("--tolerance", type=float, default=1e-8,
                    help="treat max relative deviation below this as identical")
    args = ap.parse_args()

    gen = {p.name: p for p in Path(args.generated).glob("*.orb")}
    ref = {p.name: p for p in Path(args.reference).glob("*.orb")}
    only_gen = sorted(set(gen) - set(ref))
    only_ref = sorted(set(ref) - set(gen))
    common = sorted(set(gen) & set(ref))

    print(f"generated : {len(gen)} files in {args.generated}")
    print(f"reference : {len(ref)} files in {args.reference}")
    if only_gen:
        print(f"  only in generated: {only_gen}")
    if only_ref:
        print(f"  only in reference: {only_ref}")

    verdicts = []
    for name in common:
        a, b = read_nao(gen[name]), read_nao(ref[name])
        r = compare(name, a, b)
        da, db = describe(a), describe(b)
        same_meta = all(da[k] == db[k] for k in ("element", "ecut", "rcut"))
        if not r["same_nzeta"]:
            print(f"\n{name}: DIFFERENT nzeta {r['nzeta_a']} vs {r['nzeta_b']}  <-- pipeline bug")
            verdicts.append("nzeta")
            continue
        tag = "IDENTICAL" if r["max_rel"] <= args.tolerance else "differs"
        print(f"\n{name}")
        print(f"  metadata : element {da['element']}/{db['element']}  ecut {da['ecut']}/{db['ecut']}"
              f"  rcut {da['rcut']}/{db['rcut']}  {'same' if same_meta else 'DIFFERENT'}")
        print(f"  nzeta    : {r['nzeta_a']}  (n_r={da['n_r']}/{db['n_r']}, dr={da['dr']}/{db['dr']})")
        print(f"  radial   : max rel {r['max_rel']:.3e}   rms rel {r['rms_rel']:.3e}   -> {tag}")
        worst = sorted(r["per_l"], key=lambda t: -t[1])[:3]
        print(f"  worst l  : " + ", ".join(f"l={l} {d:.2e}" for l, d in worst))
        verdicts.append(tag)

    print("\nsummary:", {v: verdicts.count(v) for v in set(verdicts)} or "nothing comparable")
    if "differs" in verdicts:
        print("\nIf the metadata is identical but the radial part differs, the two runs used a "
              "different reference calculation.  Check, in this order: ecutwfc, k-mesh, "
              "nbands (per geometry!), geometry, spill_guess, max_steps, torch.lr.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
