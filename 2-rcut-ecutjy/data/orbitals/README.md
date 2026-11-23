# Final NAO set: U, r_cut 12 bohr, E_cut(jY) 125 Ry, l_max 4

The product of stage 2 — a pseudopotential and the three contracted orbitals that go
with it.  Copy this directory somewhere and point ABACUS at it.

| file | size | what it is |
|---|---:|---|
| `U.pbe-n-nc.UPF` | 497 KB | norm-conserving PBE pseudopotential, **14 valence electrons**, no SOC, md5 `024f9a435d4b4c50e9267d14ff369f4e` |
| `U_gga_12au_125Ry_2s1p1d1f.orb` | 138 KB | SZ scheme, 17 functions/atom, spillage 1.0983e-02 |
| `U_gga_12au_125Ry_4s2p2d2f1g.orb` | 302 KB | DZP scheme, 60 functions/atom, spillage 2.8994e-03 |
| `U_gga_12au_125Ry_6s3p3d3f2g.orb` | 466 KB | TZDP scheme, 105 functions/atom, spillage 5.9091e-04 |

Produced by `abacus.orbgen.base` workchain **PK 562761** with `ecutwfc 180 Ry` and
`spill_guess: atomic`.  `spillage` is the fraction of the primitive-basis states the
contracted set fails to span, i.e. how much accuracy the contraction throws away.

### Which geometries are the fit targets

Four SCFs were run, but they do not all enter the objective:

| geometry | ran | role |
|---|---|---|
| U2 2.10 A | yes | **fit target** |
| U2 2.40 A | yes | **fit target** |
| U2 2.80 A | yes | **fit target** |
| monomer | yes | **initial guess only** |

`spill_guess: atomic` adds the monomer job so that the optimiser can start from linear
combinations of its s/p/d/f bands (`SIAB/abacus/api.py`, comment `# then the initial
guess`); `SIAB/driver/main.py` builds the fit folder list from `geoms[].pertmags`, which
contains only the three bond lengths.  With `spill_guess: random` the monomer job would
not be submitted at all.

## The .orb header does not name a pseudopotential

It carries only `Element`, `Energy Cutoff`, `Radius Cutoff`, `Lmax` and the per-l
zeta counts.  So nothing stops you from pairing these orbitals with the *wrong* UPF and
getting a silently wrong answer — **always pair them with the file above**.  The
registered families `sg15_14ve_6p_{sz,dzp,tzdp}` carry the same UPF, so using a family
name rather than a bare directory avoids the mistake.

## Minimal ABACUS input

```
ntype            1
lmaxmax          4
basis_type       lcao
ks_solver        genelpa
ecutwfc          180
pseudo_dir       <this directory>
orbital_dir      <this directory>
```
and in `STRU`:

```
ATOMIC_SPECIES
U  238.02891  U.pbe-n-nc.UPF
```

Choosing the scheme: DZP is enough for structures, elastic constants and occupied
bands (eta 8.1 meV, dV0 +0.15 %, dB0 +1.1 %); energy differences need TZDP (43.9
meV/atom, right at 1 kcal/mol).  SZ is not usable (eta 113 meV, dB0 -14 %).  See
`../../../3-eos/data/basis_selection.csv`.

## Caveat on the coefficients

These are one fit, not the unique fit.  Two runs of the same scheme from the same
reference states differ by ~3e-4 relative; for the TZDP scheme the spread reaches 4e-1
while the spillage still agrees to 0.05 % — the high-zeta fit is ill-conditioned, so the
individual functions are not determined even though their quality is.  Compare orbitals
by spillage, eta or total energy, never coefficient by coefficient.
