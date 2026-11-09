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

## One convention throughout

Every CSV in this directory now quotes the **same** quantity:

    |E_LCAO - E_PW| per atom, in meV

with 1 kcal/mol = 43.364 meV/atom.  The ladder files used to quote the atomization
energy difference against another LCAO set (a 50 meV bar); they were re-derived from
the same AiiDA workchains by `export_vs_pw.py`, so `data/` no longer mixes criteria.

Only the 2.10 and 2.40 A geometries have a PW run, so the 2.80 A column of the older
tables is not reproduced here.  The r_cut 9-12 rows agree with `tsw_vs_pw.csv` to
0.1 meV (e.g. r_cut 12 at ecutjy 150: (27.3 + 20.4)/2 = 23.9 meV/atom), which is the
check that the pooling is sound.

| file | rows | grid |
|---|---|---|
| `tsw_vs_pw.csv` | 13 | r_cut 8-12 x ecutjy 150, r_cut 9-12 x ecutjy 100/125 |
| `rcut_ladder.csv` | 5 | r_cut 8-12 at ecutjy 150, l_max 4 |
| `ecutjy_ladder.csv` | 3 | ecutjy 100/125/150 at r_cut 12 |
| `lmax_ladder.csv` | 2 | l_max 3/4 at r_cut 12, ecutjy 150 |
| `timings.csv` | 52 | wall time per primitive-basis SCF |
| `../../../3-eos/data/basis_selection.csv` | 4 | V0, B0, eta, eta10 per basis |

## Reproducing without AiiDA

```bash
python 2-rcut-ecutjy/plot_tsw_vs_pw.py --from-csv 2-rcut-ecutjy/data/tsw_vs_pw.csv
```

`--from-csv` never imports AiiDA.  Regenerate from the database with `--csv-out`, or
re-derive the ladders with `python export_vs_pw.py`.
