# Stage 2 data

Machine-readable versions of the tables that back `tsw_vs_pw.png` and the
`(r_cut, ecutjy)` choice.  Everything here is a *result*, not a fixture.

| file | what it is | where it came from |
|---|---|---|
| `tsw_vs_pw.csv` | 12 points: primitive (TSW) basis vs plane waves, `ecutjy` x `r_cut`, meV/atom | AiiDA, `abacus.orbgen.base` workchains (PKs in the `pk` column) |
| `timings.csv` | wall time of each primitive-basis SCF | AiiDA, `mtime - ctime` of the CalcJobNodes |
| `rcut_ladder.csv` | r_cut 8-12 au, three bond lengths, mean/max deviation | `project/u_14ve/rcut/README.md` |
| `ecutjy_ladder.csv` | ecutjy 100/125/150 Ry, including the 11 h timeout | `project/u_14ve/ecutjy/README.md` |
| `lmax_ladder.csv` | l_max 3/4/5, including the exit-301 failures | `project/u_14ve/lmax/README.md` |

## Reproducing the figure without AiiDA

```bash
python 2-rcut-ecutjy/plot_tsw_vs_pw.py --from-csv 2-rcut-ecutjy/data/tsw_vs_pw.csv
```

`--from-csv` never imports AiiDA.  Regenerate the CSV from the database with
`--csv-out`, or re-export the ladder data with `export_data.py`.

## Two different criteria live in this directory -- do not mix them

`tsw_vs_pw.csv` and the three ladder files answer different questions, against
different references.

| file | reference | quantity | bar |
|---|---|---|---|
| `tsw_vs_pw.csv` | plane waves | \|E_TSW - E_PW\| **per atom** | 43.364 meV/atom (1 kcal/mol) |
| `rcut/ecutjy/lmax_ladder.csv` | another **LCAO** parameter set | \|A(p) - A(ref)\| of the **atomization energy** `A = E(U2) - 2 E(U)` | 50 meV (0.05 eV) |

The ladder files therefore use two numbers per cell, `dE_per_atom` and `dA`, and the
verdict follows `dA` -- not the energy difference against PW.  All four files are
per atom; nothing here is per dimer.

## One dataset, not two

`tsw_vs_pw.csv` spans r_cut 8-12 au at ecutjy 150 Ry plus r_cut 9-12 at 100 and
125 Ry.  The r_cut 8 point is **reused**, not recomputed: it comes from the earlier
LCAO-only ladder (PK 468364), and that ladder's r_cut 9-12 points reproduce this
scan's 150 Ry column to 0.1 meV, which is what makes pooling legitimate.

Cross-check against the published ladder table, after converting both to the same
reference (the ladder quotes the deviation from r_cut 12, the CSV from PW):

| r_cut | CSV minus its r_cut-12 row | ladder table | difference |
|---|---|---|---|
| 8 | 383.4 meV | 380 | +3.4 |
| 9 | 146.3 | 147 | -0.7 |
| 10 | 53.7 | 55 | -1.3 |
| 11 | 15.4 | 16 | -0.6 |

Residual differences are the rounding of the old table.  So the two campaigns are
the same physics and the figure can carry both without mixing methods.

The ladder files still exist because they answer a different question (atomization
energy against another LCAO parameter set, 50 meV bar); they are not an alternative
source for the same figure.
