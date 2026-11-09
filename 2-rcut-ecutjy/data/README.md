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

The ladders also cover a wider grid than the figure: `rcut_ladder.csv` includes
r_cut 8 au from the earlier LCAO-only campaign (`project/u_14ve/rcut/`, PKs
468364-468557), while `tsw_vs_pw.png` comes from the newer `abacus.orbgen.base`
scan (r_cut 9-12 x ecutjy 100/125/150).  r_cut 8 is absent from the figure because
that scan never included it -- not because it was dropped.
