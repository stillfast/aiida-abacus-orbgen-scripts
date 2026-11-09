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

## Unit conventions -- read before quoting a number

Two conventions are in circulation and they differ by a factor of two:

* `tsw_vs_pw.csv` is **per atom**; 1 kcal/mol = **43.364 meV/atom**.
* `rcut_ladder.csv`, `ecutjy_ladder.csv` and `lmax_ladder.csv` come from the older
  project tables, which quoted the error **per U2 dimer**; there 1 kcal/mol =
  43.364 meV/dimer = **21.68 meV/atom**.

Do not mix the two: a 24 meV value means "passes comfortably" under the per-atom
convention and "marginal" under the per-dimer one.
