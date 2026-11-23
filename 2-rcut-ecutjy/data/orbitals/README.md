# Final orbitals: l_max 4, r_cut 12 au, ecutjy 125 Ry

The product of stage 2.  Produced by `abacus.orbgen.base` workchain **PK 562761**
(ecutwfc 180 Ry, `spill_guess: atomic`), which ran the four reference geometries
(U2 at 2.10 / 2.40 / 2.80 A plus the monomer) in the primitive NSW basis and then fit
the contraction.

| file | scheme | functions/atom | spillage |
|---|---|---:|---:|
| `U_gga_12au_125Ry_2s1p1d1f.orb` | SZ | 17 | 1.0983e-02 |
| `U_gga_12au_125Ry_4s2p2d2f1g.orb` | DZP | 60 | 2.8994e-03 |
| `U_gga_12au_125Ry_6s3p3d3f2g.orb` | TZDP | 105 | 5.9091e-04 |

`spillage` is the fraction of the primitive-basis states the contracted set fails to
span (`sum_c |<psi|phi_c>|^2`), i.e. how much accuracy the contraction throws away.

## Using them

The pseudopotential is `U.pbe-n-nc.sorted.UPF` (14 valence electrons, md5
`024f9a435d4b` on the UPF itself).  In ABACUS:

```
ntype            1
lmaxmax          4
basis_type       lcao
```

and point `orbital_dir` at this directory.  Registered families carrying the same
three files: `sg15_14ve_6p_{sz,dzp,tzdp}`.

## Caveat on the coefficients

These are one fit, not the unique fit.  Two runs of the same scheme from the same
reference states differ by ~3e-4 relative in the radial coefficients (the optimiser is
not bit-reproducible), and for the TZDP scheme the spread reaches 4e-1 while the
spillage still agrees to 0.05 % -- the high-zeta fit is ill-conditioned, so the
individual functions are not determined even though their quality is.  Compare orbitals
by spillage, eta or total energy, never coefficient by coefficient.
