"""The ladders and grids the two stages scan.

Everything is a plain dataclass holding a list, so it can be printed, dumped to JSON and
re-loaded by the launchers without any dependency on an AiiDA profile.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

KCAL_TO_MEV = 43.364


@dataclass
class EcutwfcLadder:
    """Stage 1: plane-wave cutoff ladder (PW only, no orbital involved)."""

    values: list[float] = field(default_factory=lambda: [100, 120, 140, 160, 180, 200, 220])
    tolerance_mev_per_atom: float = 2.0
    #: the project's rule: the cutoff is converged once two neighbouring cutoffs differ
    #: by less than `tolerance_mev_per_atom`.  2 meV/atom is what gave >= 180 Ry for U.
    structures: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RcutEcutjyGrid:
    """Stage 2: joint (r_cut, ecutjy) grid at fixed l_max."""

    r_cuts: list[float] = field(default_factory=lambda: [9, 10, 11, 12])
    ecutjys: list[float] = field(default_factory=lambda: [100, 125, 150])
    l_max: int = 4                      # fixed, as chosen for U
    tolerance_mev_per_atom: float = KCAL_TO_MEV
    cost_exponent: float = 1.0
    r_cut_reference: float = 10.0
    structures: dict[str, str] = field(default_factory=dict)

    def points(self) -> list[dict]:
        """Every grid point, cheapest-looking first."""
        pts = [{"r_cut": float(r), "ecutjy": float(e), "l_max": int(self.l_max)}
               for r in self.r_cuts for e in self.ecutjys]
        return sorted(pts, key=lambda p: (p["l_max"], p["ecutjy"], p["r_cut"]))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["points"] = self.points()
        return d


def load_json(path: str | Path) -> dict:
    with open(path) as handle:
        return json.load(handle)
