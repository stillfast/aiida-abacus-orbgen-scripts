"""The selection rules, kept separate from any AiiDA query so they can be unit-tested.

Both stages reduce to the same two questions:

  * how much does the quantity change between neighbouring rungs of the ladder, and
  * how far is each rung from the reference (plane waves)?

The difference is only which one decides:

  stage 1 (ecutwfc)            -> neighbour difference decides (PW converges to itself);
  stage 2 (r_cut, ecutjy)      -> distance to the PW reference decides, because the
                                  orbital basis has a *systematic* offset that never
                                  vanishes with more zeta functions, so "neighbour
                                  difference" is not a criterion at all.
"""
from __future__ import annotations

from dataclasses import dataclass

KCAL_TO_MEV = 43.364


@dataclass
class LadderRow:
    value: float                 # ecutwfc, or a label encoded by the caller
    energy: float                # total energy, eV
    natoms: int = 1

    def per_atom(self) -> float:
        return self.energy / self.natoms


def adjacent_differences(rows: list[LadderRow]) -> list[dict]:
    """|E(i) - E(i-1)| in meV/atom, for the sorted ladder."""
    rows = sorted(rows, key=lambda r: r.value)
    out = []
    for prev, cur in zip(rows, rows[1:]):
        delta = (cur.per_atom() - prev.per_atom()) * 1000.0
        out.append({"from": prev.value, "to": cur.value,
                    "delta_mev_per_atom": delta, "abs_mev_per_atom": abs(delta)})
    return out


def select_ecutwfc(rows: list[LadderRow], tolerance_mev_per_atom: float) -> dict:
    """Smallest cutoff whose neighbour difference is below the tolerance.

    This is the project's rule for `ecutwfc`: it is a *plane-wave-only* quantity, so
    consecutive cutoffs must agree with each other.  2 meV/atom gave >= 180 Ry for U.
    """
    diffs = adjacent_differences(rows)
    if not diffs:
        raise ValueError("need at least two cutoff points")
    passed = [d["abs_mev_per_atom"] <= tolerance_mev_per_atom for d in diffs]
    if not any(passed):
        return {"chosen": None, "reason": "no neighbouring pair within tolerance",
                "diffs": diffs}
    # The cutoff X is converged when *adding more* changes nothing, i.e. when the pair
    # (X, X_next) is inside the tolerance -- so the answer is the `from` of the first
    # pair that passes AND is followed only by pairs that pass.
    #
    # Getting this wrong by taking `to` shifts the answer one rung up: on the real U
    # ladder (150->180 = 5.9, 180->200 = 1.3 meV/atom) it returns 200 Ry instead of the
    # 180 Ry the project actually chose.
    chosen = None
    for i, ok in enumerate(passed):
        if ok and all(passed[i:]):
            chosen = diffs[i]["from"]
            break
    if chosen is None:
        return {"chosen": None, "reason": "tolerance only met on the last rung",
                "diffs": diffs}
    return {"chosen": chosen,
            "rule": f"|dE| between neighbours <= {tolerance_mev_per_atom} meV/atom",
            "diffs": diffs}


def errors_vs_reference(rows: dict[str, float], reference: dict[str, float],
                        natoms: int) -> dict:
    """``{label: E}`` and ``{label: E_ref}`` -> ``{label: dE in meV/atom}``."""
    out = {}
    for label, energy in rows.items():
        if label in reference:
            out[label] = (energy - reference[label]) / natoms * 1000.0
    return out


def select_rcut_ecutjy(candidates: list[dict], tolerance_mev_per_atom: float,
                       cost_exponent: float = 1.0, r_cut_reference: float = 10.0,
                       natoms: int = 1) -> dict:
    """Cheapest (r_cut, ecutjy, l_max) whose mean |dE| vs PW is inside the tolerance.

    ``candidates`` items need ``r_cut``, ``ecutjy``, ``l_max``, ``nbasis_per_atom`` and
    either ``mean_error_mev`` or ``errors_mev`` (a dict over geometries).
    """
    scored = []
    for c in candidates:
        errs = c.get("errors_mev")
        if errs:
            mean_err = sum(errs.values()) / len(errs)
        else:
            mean_err = c.get("mean_error_mev", float("nan"))
        cost = (c["nbasis_per_atom"] * natoms
                * (1.0 + c["r_cut"] / r_cut_reference) ** cost_exponent)
        scored.append({**c,
                       "mean_error_mev": mean_err,
                       "mean_error_kcal": mean_err / KCAL_TO_MEV,
                       "cost": cost,
                       "passes": abs(mean_err) <= tolerance_mev_per_atom})
    passing = [s for s in scored if s["passes"]]
    best = min(passing, key=lambda s: s["cost"]) if passing else None
    return {"best": best, "table": sorted(scored, key=lambda s: s["cost"]),
            "tolerance_mev_per_atom": tolerance_mev_per_atom}
