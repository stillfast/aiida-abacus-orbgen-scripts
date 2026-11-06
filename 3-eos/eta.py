#!/usr/bin/env python
"""Stage 3 (part b) -- eta between an LCAO run and its plane-wave reference.

The EOS scan gives V0 / B0; this gives the band-structure error at the equilibrium
volume, so the two halves of the acceptance test live in the same stage:

    python eta.py --lcao 559664 --pw 559797            # by CalcJobNode PK
    python eta.py --group eos-r125 --lcao dzp --pw pw  # by label inside a group

The arithmetic lives in ``aiida_abacus_orbgen.utils_eta`` (the same code the
``orbgen.eta`` calculation uses), so the number is identical whether it comes from this
script or from an AiiDA node.
"""
from __future__ import annotations

import argparse
import re
import sys


def energy_of(node) -> float | None:
    if "retrieved" not in node.outputs:
        return None
    for sub in ("OUT.aiida", "OUT.ABACUS"):
        try:
            text = node.outputs.retrieved.get_object_content(f"{sub}/running_scf.log")
        except Exception:                                        # noqa: BLE001
            continue
        hits = re.findall(r"!FINAL_ETOT_IS\s+(-?[0-9.]+)", text)
        if hits:
            return float(hits[-1])
    return None


def find_istate(node):
    if "retrieved" not in node.outputs:
        return None
    folder = node.outputs.retrieved
    for sub in ("OUT.aiida", "OUT.ABACUS"):
        name = f"{sub}/istate.info"
        try:
            return folder.get_object_content(name)
        except Exception:                                        # noqa: BLE001
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lcao", help="CalcJobNode PK of the LCAO run")
    ap.add_argument("--pw", help="CalcJobNode PK of the PW reference")
    ap.add_argument("--group", help="instead of PKs: a Group holding both runs")
    ap.add_argument("--lcao-label-match", default=None)
    ap.add_argument("--pw-label-match", default=None)
    ap.add_argument("--eps-f", type=float, default=None,
                    help="Fermi level in eV, needed for eta_10")
    ap.add_argument("--lift", type=float, default=10.0)
    ap.add_argument("--sigma-ev", type=float, default=0.2041)
    args = ap.parse_args()

    from aiida import load_profile
    from aiida.orm import Group, load_node

    from aiida_abacus_orbgen.utils_eta import (band_span_above_fermi, eta,
                                               eta10_is_valid, model_occupation,
                                               parse_istate_info)

    load_profile("aiida_profile")

    if args.group:
        members = list(Group.collection.get(label=args.group).nodes)
        def pick(pattern):
            hits = [n for n in members if pattern and re.search(pattern, n.label or "")]
            return hits[0] if hits else None
        lcao, pw = pick(args.lcao_label_match), pick(args.pw_label_match)
        if lcao is None or pw is None:
            raise SystemExit(f"cannot find both runs in group {args.group!r}; "
                             f"members: {[n.label for n in members][:8]}")
    else:
        lcao, pw = load_node(int(args.lcao)), load_node(int(args.pw))

    text_a, text_b = find_istate(lcao), find_istate(pw)
    if text_a is None or text_b is None:
        raise SystemExit("one of the runs has no retrieved istate.info -- check that "
                         "settings.additional_retrieve_list included it")
    E_a, O_a, _ = parse_istate_info(text_a)
    E_b, O_b, _ = parse_istate_info(text_b)

    value, w, _ = eta(E_a, O_a, E_b, O_b)
    print(f"LCAO {lcao.pk} ({lcao.label})   PW {pw.pk} ({pw.label})")
    print(f"  bands {E_a.shape[1]} x {E_a.shape[0]} k-points")
    print(f"  eta        = {value * 1000:8.3f} meV   ({'PASS' if value * 1000 <= 20 else 'fail'} vs 20 meV)")
    print(f"  shift w    = {w * 1000:8.3f} meV")
    if args.eps_f is not None:
        f_a = model_occupation(E_a, args.eps_f + args.lift, args.sigma_ev)
        f_b = model_occupation(E_b, args.eps_f + args.lift, args.sigma_ev)
        value10, _, _ = eta(E_a, f_a, E_b, f_b)
        valid = eta10_is_valid(E_b, args.eps_f, args.lift, args.sigma_ev)
        span = band_span_above_fermi(E_b, args.eps_f)
        print(f"  eta_10     = {value10 * 1000:8.3f} meV   "
              f"({'valid' if valid else f'INVALID: spectrum only {span:.2f} eV above eps_F'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
