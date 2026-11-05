#!/usr/bin/env python
"""Submit the plane-wave cutoff ladder of stage 1.

Five things must be identical across the ladder -- structure, pseudopotential, code,
k-points and every SCF setting except ``ecutwfc``.  Rather than re-declaring them here
(and getting one of them subtly wrong), the script **clones them from a finished
CalcJobNode** that is known good:

    python submit.py --template 463407 463414 --cutoffs 100 120 150 180 200

Each template contributes one reference geometry; every geometry is run at every cutoff.
The only field that changes between jobs is ``ecutwfc``.

Use ``--dry-run`` to print the plan without touching AiiDA.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", type=int, nargs="+", required=True,
                    help="CalcJobNode PKs whose inputs are cloned (one per geometry)")
    ap.add_argument("--cutoffs", type=float, nargs="+", required=True,
                    help="ecutwfc values in Ry")
    ap.add_argument("--label", default="ecutwfc", help="label prefix for the jobs")
    ap.add_argument("--group", default=None, help="add every job to this Group (created if needed)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan only")
    args = ap.parse_args()

    from aiida import load_profile
    from aiida.orm import CalcJobNode, Dict, Group, load_node

    load_profile("aiida_profile")

    templates = [load_node(pk) for pk in args.template]
    for t in templates:
        # process_type is the entry point string ("aiida.calculations:abacus.abacus"),
        # not the class name -- check the class instead
        if not isinstance(t, CalcJobNode):
            raise SystemExit(f"PK {t.pk} is a {type(t).__name__}, not a CalcJobNode")

    plan = []
    for t in templates:
        cloned = {link.link_label: link.node
                  for link in t.base.links.get_incoming().all()
                  if link.link_label in ("structure", "pseudos__U", "code", "settings", "kpoints")}
        # metadata.options must be cloned too: queue_name (the SLURM partition) lives
        # there.  Without it sbatch fails with
        #     "No partition specified or system default partition"
        options = {}
        for key in ("queue_name", "resources", "withmpi", "max_wallclock_seconds",
                    "custom_mpirun", "job_extra_directives", "account", "qos"):
            try:
                value = t.get_option(key)
            except (AttributeError, KeyError):
                value = None
            if value not in (None, {}):
                options[key] = value
        try:
            options["parser_name"] = t.get_option("parser_name")
        except (AttributeError, KeyError):
            pass
        missing = {"structure", "pseudos__U", "code"} - set(cloned)
        if missing:
            raise SystemExit(f"PK {t.pk} is missing inputs {sorted(missing)}")
        base_params = t.inputs.parameters.get_dict()
        for cutoff in args.cutoffs:
            params = {k: (dict(v) if isinstance(v, dict) else v)
                      for k, v in base_params.items()}
            params.setdefault("input", {})["ecutwfc"] = cutoff
            plan.append({"template": t.pk, "structure": cloned["structure"].pk,
                         "cutoff": cutoff, "inputs": cloned, "parameters": params,
                         "options": options})

    print(f"{'template':>10}{'structure':>11}{'ecutwfc':>10}  label")
    for item in plan:
        print(f"{item['template']:>10}{item['structure']:>11}{item['cutoff']:>10g}"
              f"  {args.label}-{item['cutoff']:g}")
    if plan:
        print(f"\noptions cloned from the template: {plan[0]['options']}")
    print(f"\n{len(plan)} jobs "
          f"({len(templates)} geometries x {len(args.cutoffs)} cutoffs)")

    if args.dry_run:
        print("\n[dry run] nothing submitted.")
        return 0

    from aiida.engine import submit
    from aiida.plugins import CalculationFactory

    AbacusCalculation = CalculationFactory("abacus.abacus")
    group = None
    if args.group:
        group = Group.collection.get_or_create(args.group)[0]

    pks = []
    for item in plan:
        inputs = {
            "code": item["inputs"]["code"],
            "structure": item["inputs"]["structure"],
            "pseudos": {"U": item["inputs"]["pseudos__U"]},
            "parameters": Dict(dict=item["parameters"]),
            "metadata": {"label": f"{args.label}-{item['cutoff']:g}-s{item['structure']}",
                         "options": dict(item["options"])},
        }
        for key in ("settings", "kpoints"):
            if key in item["inputs"]:
                inputs[key] = item["inputs"][key]
        node = submit(AbacusCalculation, **inputs)
        pks.append(node.pk)
        if group is not None:
            group.add_nodes(node)
        print(f"  submitted {node.pk}  ecutwfc={item['cutoff']:g}  "
              f"structure={item['structure']}")
    print(f"\nsubmitted {len(pks)}: {pks}")
    if group is not None:
        print(f"group: {group.label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
