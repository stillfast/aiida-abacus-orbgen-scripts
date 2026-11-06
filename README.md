# aiida-abacus-orbgen-scripts

How the ABACUS NAO generation parameters are chosen, in the layout of
`acwf-verification-scripts`: numbered stages, a `launch.py` planner and an `analyze.py`
that applies the selection rule.

```
1-ecutwfc/         choose the plane-wave cutoff        (PW only, no orbital)
2-rcut-ecutjy/     choose (r_cut, ecutjy) at l_max = 4 (orbital vs PW)
3-eos/             check the resulting NAO: eta, V0, B0 against plane waves
utils/             the ladders and the selection rules, importable and testable
demo/              fixtures used to verify the scripts (see caveat below)
```

The order matters: `ecutwfc` is a *plane-wave* quantity and must be fixed first, because
every later total energy -- the orb generation reference and the PW reference the NAO is
compared against -- is computed at it.

## Nothing is submitted unless you ask

Both launchers are planners. They print the job list, write it to JSON, and stop:

```bash
python 1-ecutwfc/launch.py --out plan1.json          # dry run (default)
python 2-rcut-ecutjy/launch.py --out plan2.json      # dry run (default)
```

`--submit` exists but stage 2 deliberately refuses to submit from the planner: the
structures / pseudopotential / code have to be visible in the script that submits, not
hidden behind a flag. For real submission use the workflow directly:

```python
from aiida.plugins import WorkflowFactory
Orbgen = WorkflowFactory("abacus.orbgen.converge")
builder = Orbgen.get_builder()
builder.r_cuts = List([9, 10, 11, 12])
builder.ecutjys = List([100, 125, 150])
builder.l_maxes = List([4])
```

## Stage 1 -- `ecutwfc`

**Rule**: the cutoff is converged when adding more changes nothing, i.e. when the pair
`(X, X_next)` is inside the tolerance *and so is every later pair*. Report the `from`
value.

Verified against the real U ladder from `project/u_14ve/ecutwfc/`:

```bash
python 1-ecutwfc/analyze.py demo/ecutwfc_u14ve.csv --tolerance 2.0
```

```
     100 -> 120      -436.85
     120 -> 150       -63.38
     150 -> 180        -5.94
     180 -> 200        -1.34  OK
chosen ecutwfc = 180 Ry
```

That is exactly the project's conclusion (`>= 180 Ry`).

> Off-by-one trap: reporting the `to` of the first passing pair gives **200 Ry** instead
> of 180. The rule is "200 added nothing to 180", so the converged value is 180.

## Stage 2 -- `(r_cut, ecutjy)` at `l_max = 4`

**Rule**: compare every grid point's total energy with the **plane-wave** reference and
keep the *cheapest* point inside `--tolerance` (default 1 kcal/mol = 43.364 meV/atom).

`r_cut` and `ecutjy` are scanned **jointly** because they are not separable: a small
`r_cut` truncates the basis in space and no amount of `ecutjy` recovers what lies beyond
the cutoff.

```bash
python 2-rcut-ecutjy/analyze.py table.csv --natoms 2 --tolerance 43.364
```

CSV columns: `r_cut,ecutjy,l_max,nbasis_per_atom,error_<geometry>,...` where each
`error_<geometry>` is the total-energy error against PW in eV per cell.

> **Why not a neighbour-difference rule here.** For `ecutjy` a ladder-style rule is
> defensible (two very large Bessel sets describe the same space). For `r_cut` it is not:
> the error has a systematic offset that *never* goes away by adding functions, so
> consecutive `r_cut` values keep differing and a neighbour rule would keep walking up
> the ladder. Only the distance to PW decides.

Cost ranking (both knobs exposed in `params.py`):

```
cost = nbasis_per_atom * natoms * (1 + r_cut / r_cut_reference) ** cost_exponent
```

## Status / caveat

* Stage 1 is **validated against the real U ladder** and reproduces 180 Ry.
* `demo/rcut_ecutjy_fixture.csv` is a **fixture, not a result**: it was built to exercise
  the code paths. Its numbers are in the right ballpark of the measured behaviour (it
  reports "nothing inside 1 kcal/mol up to r_cut 13", which matches the independent
  `new_nao/rcut_lmax` finding that r_cut 12 gives 1.07 kcal/mol for the primitive and
  more once contracted). Plug in the real ladder to get the real answer.
* No AiiDA job was submitted while building this.

## Stage 3 -- `3-eos`

Checks that the NAO chosen in stages 1-2 reproduces the structure and the elastic
response.  `launch.py` plans an `abacus.orbgen.eos` run (dry run by default);
`analyze.py` reads a *finished* campaign and prints the selection table.

The campaign for uranium was already produced by the project's own `2-eos` workflow, so
this stage is used in read-back mode -- no job is resubmitted:

```bash
python 3-eos/analyze.py --report-dir \
    ../../bcc_uranium/aiida-uranium-alpha/2-eos/reports
```

```
basis    V0/atom   dV0 (%)   B0 (GPa)   dB0 (%)     BP     E0/atom  dE (meV)  eta (meV)
pw       20.0916    +0.000     202.34     +0.00   8.51  -2481.4847       0.0        nan
sz       20.3976    +1.523     173.82    -14.09  11.08  -2480.5042     980.5     113.17
dzp      20.1210    +0.146     204.45     +1.05   8.78  -2481.4071      77.6       8.10
tzdp     20.1136    +0.109     201.07     -0.62   8.62  -2481.4408      43.9       4.41
```

**DZP passes eta (8.1 meV), V0 (+0.15 %) and B0 (+1.1 %); only the total energy
(77.6 meV/atom) is above 1 kcal/mol, and TZDP (43.9 meV/atom) sits right on it.**
The same pattern came out of the independent fcc benchmark (`5-nao_eos`): structure and
elasticity saturate at DZP, energy differences need TZDP.
