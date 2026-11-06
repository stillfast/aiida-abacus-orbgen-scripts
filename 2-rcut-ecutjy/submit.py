#!/usr/bin/env python
"""Submit (r_cut, ecutjy) points of stage 2 through ``abacus.orbgen.base``.

Each point walks the whole chain -- NSW primitive, one LCAO SCF per reference geometry
(with that primitive), then the spillage fit.

**No ABACUS parameter is written here.**  `abacus.orbgen.base` takes the INPUT deck
straight out of SIAB's ``generate_all``, so ``bessel_nao_rcut``, the smearing, the
per-geometry ``nbands`` (the monomer gets ``__iop_spill_guess_atomic_nbands__``, the
dimers ``geoms[0].nbands``) and the geometry all come from the config.  This script only
decides *which* ``(r_cut, ecutjy, l_max)`` to run and how the job should be scheduled
(queue, memory, code).

    python submit.py --orbgen-json ../../project/u_14ve/2-nao_gen/orbgen.json \
                     --template 463407 --r-cut 12 --ecutjy 125 --l-max 4 --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orbgen-json", required=True)
    ap.add_argument("--template", type=int, required=True,
                    help="CalcJobNode PK to clone pseudopotential / code / scheduling options")
    ap.add_argument("--r-cut", type=float, nargs="+", required=True)
    ap.add_argument("--ecutjy", type=float, nargs="+", required=True)
    ap.add_argument("--l-max", type=int, default=4)
    ap.add_argument("--mem-gb", type=float, default=190.0,
                    help="per-node memory in GB (the computer default is only 48.8 GB)")
    ap.add_argument("--queue", default=None,
                    help="SLURM partition; overrides the template's queue_name "
                         "(e.g. d2_ys for the large-memory nodes)")
    ap.add_argument("--group", default="orbgen-rcut-ecutjy")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from aiida import load_profile
    from aiida.engine import submit
    from aiida.orm import Dict, Group, UpfData, load_node
    from aiida.plugins import WorkflowFactory

    from aiida_abacus_orbgen.utils import encode_config

    load_profile("aiida_profile")

    cfg = json.loads(Path(args.orbgen_json).read_text())
    template = load_node(args.template)

    options = {}
    for key in ("queue_name", "resources", "withmpi", "max_wallclock_seconds"):
        try:
            value = template.get_option(key)
        except (AttributeError, KeyError):
            value = None
        if value not in (None, {}):
            options[key] = value
    options["max_memory_kb"] = int(args.mem_gb * 1024 * 1024)
    if args.queue:
        options["queue_name"] = args.queue

    # `AtomicOrbitalData` is not an `aiida.orm.UpfData`, so unwrap the bare UPF; the
    # filename must keep the element prefix or UpfData refuses to parse it
    import os
    import tempfile
    pseudos = next(l.node for l in template.base.links.get_incoming().all()
                   if l.link_label.startswith("pseudos__"))
    tmpdir = tempfile.mkdtemp(prefix="upf_")
    upf_path = os.path.join(tmpdir, pseudos.filename)
    with open(upf_path, "wb") as handle:
        handle.write(pseudos.get_content(mode="rb"))
    upf = UpfData(file=upf_path)
    upf.store()

    points = [{"r_cut": r, "ecutjy": e, "l_max": args.l_max}
              for r in args.r_cut for e in args.ecutjy]
    print(f"orbgen config : {args.orbgen_json}  (element {cfg.get('element')})")
    print(f"upf           : pk {upf.pk} ({pseudos.filename})")
    print(f"scheduling    : queue={options.get('queue_name')} mem={args.mem_gb:g} GB")
    print(f"points        : {len(points)}  (no ABACUS parameter is written by this script)")

    Workflow = WorkflowFactory("abacus.orbgen.base")
    group = None
    if not args.dry_run:
        group = Group.collection.get_or_create(args.group)[0]

    submitted = []
    for point in points:
        print(f"\n  r_cut={point['r_cut']:g} ecutjy={point['ecutjy']:g} l_max={point['l_max']}")
        if args.dry_run:
            continue
        builder = Workflow.get_builder()
        builder.siab_config = Dict(dict=encode_config(cfg))
        builder.settings = Dict(dict=point)
        builder.orbgen_config = Dict(dict=encode_config(cfg))
        builder.upf = upf
        builder.abacus_code = template.inputs.code
        builder.scf_options = Dict(dict=options)
        builder.metadata.label = f"orbgen-r{point['r_cut']:g}-j{point['ecutjy']:g}-l{point['l_max']}"
        node = submit(builder)
        group.add_nodes(node)
        submitted.append(node.pk)
        print(f"    submitted {node.pk}  {builder.metadata.label}")

    if args.dry_run:
        print("\n[dry run] nothing submitted.")
        return 0
    print(f"\nsubmitted {len(submitted)}: {submitted}")
    print(f"group: {group.label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
