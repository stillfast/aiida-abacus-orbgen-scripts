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

## The reference set is now complete

The four PW references are all present and were produced with the **same** cell (35 Bohr
= 18.5212 A cubic), the **same** pseudopotential (`U.pbe-n-nc.UPF`, md5 shared with the
NAO runs), the same `ecutwfc 180 Ry` and the same `gamma_only` setting, so the only
difference from the NAO side is the basis.

| geometry | PW total energy (eV) | PK |
|---|---:|---|
| U2 2.10 A | -4951.807006023504 | 561552 |
| U2 2.40 A | -4952.064018093108 | 561562 |
| U2 2.80 A | -4950.826505580118 | 580303 |
| monomer | -2473.881319189626 | 580305 |

`dE_mean4` is the headline: the mean error over **all four** reference geometries, the
monomer weighted the same as each dimer.  It measures how well the primitive basis spans
these structures, i.e. it bounds the accuracy available to the contraction.

It is **not** the set the spillage fit optimises.  Four SCFs are run, with different
roles:

| geometry | ran | role |
|---|---|---|
| U2 2.10 A | yes | fit target |
| U2 2.40 A | yes | fit target |
| U2 2.80 A | yes | fit target |
| monomer | yes | `spill_guess: atomic` initial guess only |

`SIAB/abacus/api.py` adds the monomer job under the comment `# then the initial guess`,
and `SIAB/driver/main.py` builds the fit folder list from `geoms[].pertmags`, which holds
only the three bond lengths.  `dE_mean3` (dimers only) is kept because it is what the
older tables quoted.

| ecutjy | r_cut | 2.10 | 2.40 | 2.80 | monomer | **mean4** |
| ecutjy | r_cut | 2.10 | 2.40 | 2.80 | mean3 | **monomer** |
|---|---:|---:|---:|---:|---:|---:|
| 125 | 12 | 51.71 | 44.79 | 42.47 | 46.32 | 47.86 |
| 150 | 11 | 43.10 | 35.44 | 31.28 | 36.61 | 41.42 |
| 150 | 12 | 27.30 | 20.43 | 17.02 | **21.58** | **19.81** |

Note the progression in the last row: the error shrinks as the bond stretches, and the
monomer (19.8 meV) is *smaller* than the mean over the compressed dimers.  That is the
opposite of the earlier r_cut behaviour, which is why both numbers are kept.

## A discarded PW reference

`new_nao/ecutjy_r12_l4/PW-ref/` holds a monomer PW run at **-2473.617376 eV** that must
not be used: its `STRU` has `LATTICE_CONSTANT 1.889726877` with
`LATTICE_VECTORS = 20 0 0 / 0 20 0 / 0 0 20`, i.e. a 20 A (37.8 Bohr) cube, not the
35 Bohr cell the NAO runs use.  Comparing against it produces a *negative* dE
(-244 meV), which would violate the variational bound and is a symptom of the cell
mismatch, not of a better basis.  PK 580305 replaces it.  The r_cut 9-12 rows agree with `tsw_vs_pw.csv` to
0.1 meV (e.g. r_cut 12 at ecutjy 150: (27.3 + 20.4)/2 = 23.9 meV/atom), which is the
check that the pooling is sound.

| file | rows | grid |
|---|---|---|
| `tsw_vs_pw.csv` | 12 | r_cut 9-12 x ecutjy 100/125/150 |
| `rcut_ladder.csv` | 4 | r_cut 9-12 at ecutjy 150, l_max 4 |
| `ecutjy_ladder.csv` | 3 | ecutjy 100/125/150 at r_cut 12 |
| `lmax_ladder.csv` | 2 | l_max 3/4 at r_cut 12, ecutjy 150 |
| `timings.csv` | 48 | wall time per primitive-basis SCF |
| `cost_vs_accuracy.csv` | 12 | cost and error per point, with the pass/fail verdict |
| `../../../3-eos/data/basis_selection.csv` | 4 | V0, B0, eta, eta10 per basis |

## Reproducing without AiiDA

```bash
python 2-rcut-ecutjy/plot_tsw_vs_pw.py --from-csv 2-rcut-ecutjy/data/tsw_vs_pw.csv
```

`--from-csv` never imports AiiDA.  Regenerate from the database with `--csv-out`, or
re-derive the ladders with `python export_vs_pw.py`.

## Cost

`cost_vs_accuracy.csv` is the join of the two files above and the data behind
`tsw_cost.png`:

| ecutjy | r_cut | total (min) | dE (meV/atom) | verdict |
|---|---:|---:|---:|---|
| 100 | 9 | 27.9 | 535.0 | fail |
| 125 | 10 | 62.4 | 98.4 | fail |
| 125 | 12 | 190.6 | 48.2 | fail |
| 150 | 11 | 159.5 | 39.3 | pass |
| 150 | 12 | 207.7 | 23.9 | pass |

`total_wall_min` is the sum of the four primitive-basis SCFs, taken from ABACUS's own
`Total Time` line.  Do not use `mtime - ctime` of the CalcJobNode for this: a cache hit
never ran, so it reads ~2 s and would make the scan look free.

**Caveat** -- the wall times were collected across two partitions (`q_ysuan` at 190 GB
and `d2_ys` at 1.5 TB) and over several days, so cluster load varies between rows.
Trends within one ecutjy are reliable; comparing single points across ecutjy is not.
