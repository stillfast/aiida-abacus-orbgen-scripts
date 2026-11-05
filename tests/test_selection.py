"""Tests for the selection rules.

Pure standard library -- no AiiDA, no database.  The first test pins the answer for the
*real* uranium cutoff ladder from the project, which is the whole point of stage 1.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from utils.analysis import LadderRow, select_ecutwfc, select_rcut_ecutjy  # noqa: E402

# project/u_14ve/ecutwfc/: the ladder that produced ">= 180 Ry"
U_LADDER = [(100, -2473.375153), (120, -2473.812005), (150, -2473.875385),
            (180, -2473.881320), (200, -2473.882663)]


def rows():
    return [LadderRow(value=v, energy=e, natoms=1) for v, e in U_LADDER]


def test_ecutwfc_reproduces_the_project_choice():
    """180 Ry: the step 180 -> 200 adds only 1.34 meV/atom, so 180 is converged."""
    result = select_ecutwfc(rows(), tolerance_mev_per_atom=2.0)
    assert result["chosen"] == 180


def test_ecutwfc_needs_the_from_end_of_the_pair():
    """Regression: reporting the `to` of the passing pair gives 200 instead of 180."""
    assert select_ecutwfc(rows(), 2.0)["chosen"] != 200


def test_ecutwfc_ladder_too_short_returns_none():
    assert select_ecutwfc(rows()[:2], 2.0)["chosen"] is None


def test_rcut_ecutjy_picks_the_cheapest_passing_point():
    candidates = [
        {"r_cut": 9, "ecutjy": 125, "l_max": 4, "nbasis_per_atom": 565,
         "errors_mev": {"a": 300.0, "b": 200.0}},
        {"r_cut": 12, "ecutjy": 125, "l_max": 4, "nbasis_per_atom": 995,
         "errors_mev": {"a": 30.0, "b": 20.0}},
        {"r_cut": 13, "ecutjy": 150, "l_max": 4, "nbasis_per_atom": 1210,
         "errors_mev": {"a": 10.0, "b": 8.0}},
    ]
    best = select_rcut_ecutjy(candidates, tolerance_mev_per_atom=43.364)["best"]
    assert (best["r_cut"], best["ecutjy"]) == (12, 125)


def test_rcut_ecutjy_returns_none_when_nothing_passes():
    candidates = [{"r_cut": 9, "ecutjy": 100, "l_max": 4, "nbasis_per_atom": 500,
                   "errors_mev": {"a": 500.0}}]
    assert select_rcut_ecutjy(candidates, 43.364)["best"] is None
