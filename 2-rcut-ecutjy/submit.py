#!/usr/bin/env python
"""Submit one or more (r_cut, ecutjy) points of stage 2 through abacus.orbgen.base.

Each point runs the full chain: NSW primitive -> LCAO SCF per reference geometry (with
the primitive basis) -> spillage fit.  The *contracted* orbitals that come out are what
stage 2 compares against plane waves later.

The reference geometries are rebuilt here from the orbgen config (prototype + bond
lengths + `celldm`), so the SIAB folder names are guaranteed to be the ones the fit
looks for; `orbgen.nsw` publishes them and the workchain cross-checks.

    python submit.py --orbgen-json ../new_nao/orb_gen_j125_v2/orbgen.json \
                     --template 463407 --r-cut 12 --ecutjy 125 --l-max 4 --dry-run

`--template` is a finished CalcJobNode whose pseudopotential, code, settings and
metadata.options are cloned (the partition lives in `metadata.options.queue_name`; a
hand-built metadata dict silently loses it and sbatch fails with "No partition
specified").
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOHR_TO_ANG = 0.529177210903


def build_structures(cfg: dict, r_cut: float, element: str) -> dict:
    """Rebuild the SIAB reference geometries as StructureData, keyed by folder name."""
    from aiida.orm import StructureData
    from aiida_orbgen.interfaces.nsw import folder_rcut
    from aiida_orbgen.interfaces.stru import dft_folder_name

    geom = cfg["geoms"][0]
    celldm = float(geom.get("celldm", 35.0))            # Bohr
    side = celldm * BOHR_TO_ANG
    centre = side / 2.0
    out = {}
    if str(cfg.get("spill_guess", "")).lower() == "atomic":
        # the atomic initialiser reads the monomer SCF
        mono = StructureData(cell=[[side, 0, 0], [0, side, 0], [0, 0, side]])
        mono.append_atom(symbols=element, position=(centre, centre, centre))
        out[dft_folder_name(element, "monomer", 0, folder_rcut(r_cut))] = mono
    for pert in geom["pertmags"]:
        stru = StructureData(cell=[[side, 0, 0], [0, side, 0], [0, 0, side]])
        stru.append_atom(symbols=element, position=(centre, centre, centre))
        stru.append_atom(symbols=element, position=(centre, centre, centre + pert))
        # folder_rcut() normalises 12.0 -> 12, which is the spelling SIAB itself writes
        out[dft_folder_name(element, geom.get("proto", "dimer"), pert,
                            folder_rcut(r_cut))] = stru
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orbgen-json", required=True, help="orbgen.json (element, geoms, orbitals)")
    ap.add_argument("--template", type=int, required=True,
                    help="CalcJobNode PK to clone pseudopotential / code / settings / options")
    ap.add_argument("--r-cut", type=float, nargs="+", required=True)
    ap.add_argument("--ecutjy", type=float, nargs="+", required=True)
    ap.add_argument("--l-max", type=int, default=4)
    ap.add_argument("--mem-gb", type=float, default=190.0,
                    help="per-node memory in GB.  AiiDA renders "
                         "'#SBATCH --mem=<max_memory_kb // 1024>', and the computer default "
                         "(50000000 kB = 48.8 GB) is not enough for a 12 a.u. primitive. "
                         "190 GB matches the 276-node / 190 GB class on yeesuan; asking "
                         "for more pins the scarce 384 GB nodes.")
    ap.add_argument("--ecutwfc", type=float, default=180.0,
                    help="plane-wave cutoff chosen in stage 1 (default 180)")
    ap.add_argument("--nbands", type=int, default=60,
                    help="bands for the reference SCF (default 60, as in orb_gen)")
    ap.add_argument("--scf-thr", default="1e-6")
    ap.add_argument("--group", default="orbgen-rcut-ecutjy")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from aiida import load_profile
    from aiida.engine import submit
    from aiida.orm import Dict, Group, load_node
    from aiida.plugins import WorkflowFactory

    from aiida_abacus_orbgen.utils import encode_config

    load_profile("aiida_profile")

    cfg = json.loads(Path(args.orbgen_json).read_text())
    element = cfg.get("element") or cfg.get("elem")

    template = load_node(args.template)
    options = {}
    for key in ("queue_name", "resources", "withmpi", "max_wallclock_seconds"):
        try:
            value = template.get_option(key)
        except (AttributeError, KeyError):
            value = None
        if value not in (None, {}):
            options[key] = value
    pseudos = next(l.node for l in template.base.links.get_incoming().all()
                   if l.link_label.startswith("pseudos__"))

    # `AtomicOrbitalData` is not a subclass of `aiida.orm.UpfData` (it derives from the
    # abacus UpfData), so it cannot be handed to an input typed `valid_type=orm.UpfData`.
    # Unwrap the bare pseudopotential and store it as a plain UpfData.
    from aiida.orm import UpfData
    import os
    import tempfile
    # UpfData validates the *path* filename ("must start with the element symbol"), so
    # the temp file has to carry the original name -- a bare tmpXXXX.upf is rejected.
    tmpdir = tempfile.mkdtemp(prefix="upf_")
    upf_path = os.path.join(tmpdir, pseudos.filename)
    with open(upf_path, "wb") as handle:
        handle.write(pseudos.get_content(mode="rb"))
    upf = UpfData(file=upf_path)
    upf.store()
    print(f"pseudopotential: UpfData pk={upf.pk} ({pseudos.filename})")
    code = template.inputs.code

    # `abacus.abacus` declares kpoints as required even for gamma_only runs
    kpoints = template.inputs.kpoints if "kpoints" in template.inputs else None

    # AiiDA renders the SLURM header as `#SBATCH --mem=<max_memory_kb // 1024>`, taken
    # from `metadata.options.max_memory_kb`.  The computer default here is 50000000 kB
    # (~49 GB), which is fine for the small EOS ladders but OOMs a 12 a.u. / 125 Ry
    # primitive (995 functions/atom).  Ask for the big nodes explicitly.
    options["max_memory_kb"] = int(args.mem_gb * 1024 * 1024)   # -> --mem=<GB*1024> MB

    scf_parameters = {
        "nspin": 1, "ntype": 1, "basis_type": "lcao", "ks_solver": "genelpa",
        "ecutwfc": args.ecutwfc, "nbands": args.nbands, "lmaxmax": args.l_max,
        "gamma_only": 1, "out_chg": 1,
        "scf_thr": args.scf_thr, "scf_nmax": 9000,
        "smearing_method": "gauss", "smearing_sigma": 0.02,
        "mixing_type": "broyden", "mixing_beta": 0.4, "mixing_ndim": 12, "mixing_gg0": 0,
        "out_mat_hs": "1 12", "out_mat_tk": "1 12",
        # without this ABACUS writes no WFC_NAO_GAMMA{k}.txt and the spillage fit dies
        # with FileNotFoundError on the wavefunction file
        "out_wfc_lcao": 1,
        "printe": 1, "device": "cpu",
    }

    points = [{"r_cut": r, "ecutjy": e, "l_max": args.l_max}
              for r in args.r_cut for e in args.ecutjy]
    print(f"orbgen config : {args.orbgen_json}")
    print(f"element       : {element}   ecutwfc {args.ecutwfc:g} Ry   nbands {args.nbands}")
    print(f"template      : {args.template}  (options: {options})")
    print(f"points        : {len(points)}")

    Workflow = WorkflowFactory("abacus.orbgen.base")
    group = None
    if not args.dry_run:
        group = Group.collection.get_or_create(args.group)[0]

    submitted = []
    for point in points:
        r_cut = point["r_cut"]
        structures = build_structures(cfg, r_cut, element)
        print(f"\n  r_cut={r_cut:g} ecutjy={point['ecutjy']:g} l_max={point['l_max']}"
              f"  -> {len(structures)} geometries: {sorted(structures)}")
        if args.dry_run:
            continue
        builder = Workflow.get_builder()
        # AiiDA's Dict forbids dots in keys; the config has "torch.lr"
        builder.siab_config = Dict(dict=encode_config(cfg))
        builder.settings = Dict(dict=point)
        builder.orbgen_config = Dict(dict=encode_config(cfg))
        import re
        folder_names = {}
        for name, stru in structures.items():
            # AiiDA link labels: alphanumerics + underscores only
            key = re.sub(r"[^0-9a-zA-Z_]", "_", name)
            builder.structures[key] = stru
            folder_names[key] = name
        builder.folder_names = Dict(dict=folder_names)
        builder.upf = upf
        builder.abacus_code = code
        builder.scf_parameters = Dict(dict=scf_parameters)
        if kpoints is not None:
            builder.kpoints = kpoints
        builder.scf_options = Dict(dict=options)
        builder.metadata.label = f"orbgen-r{r_cut:g}-j{point['ecutjy']:g}-l{point['l_max']}"
        node = submit(builder)
        group.add_nodes(node)
        submitted.append((node.pk, point))
        print(f"    submitted {node.pk}  {builder.metadata.label}")

    if args.dry_run:
        print("\n[dry run] nothing submitted.")
        return 0
    print(f"\nsubmitted {len(submitted)}: {[p for p, _ in submitted]}")
    print(f"group: {group.label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
