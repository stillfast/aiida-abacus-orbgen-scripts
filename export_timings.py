#!/usr/bin/env python
"""Wall time per SCF, straight out of AiiDA -- the data behind the cost argument.

`elapsed_s` is `mtime - ctime` of the CalcJobNode, i.e. from the moment the job was
created (queue submission) to the last write; it therefore *includes* queue wait, which
is what actually matters when comparing parameter sets.

    python export_timings.py --out 2-rcut-ecutjy/data/timings.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

GROUPS = ("orbgen-rcut-ecutjy", "orbgen-rcut-ecutjy-d2", "orbgen-control-r10-j150")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="2-rcut-ecutjy/data/timings.csv")
    args = ap.parse_args()

    from aiida import load_profile
    from aiida.orm import Group

    load_profile("aiida_profile")
    rows = []
    for label in GROUPS:
        try:
            group = Group.collection.get(label=label)
        except Exception:                                        # noqa: BLE001
            continue
        for wc in group.nodes:
            if type(wc).__name__ != "WorkChainNode":
                continue
            if wc.process_state.value != "finished" or wc.exit_status != 0:
                continue
            s = wc.inputs.settings.get_dict()
            for child in wc.called:
                if type(child).__name__ != "CalcJobNode":
                    continue
                elapsed = (child.mtime - child.ctime).total_seconds()
                cached = bool(child.base.caching.is_created_from_cache)
                # a cached node never ran: its ctime is the moment it was cloned from
                # the original, so an elapsed time of ~0 says nothing about cost
                rows.append({"ecutjy_Ry": s["ecutjy"], "r_cut_AU": s["r_cut"],
                             "geometry": child.label.replace("scf-", ""),
                             "cached": int(cached),
                             "elapsed_s": "" if cached else int(elapsed),
                             "n_scf_steps": "",
                             "workchain_pk": wc.pk, "calcjob_pk": child.pk})
    rows.sort(key=lambda r: (r["ecutjy_Ry"], r["r_cut_AU"], r["geometry"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        handle.write("# Wall time of every primitive-basis SCF of the (r_cut, ecutjy) scan.\n")
        handle.write("# elapsed_s = mtime - ctime of the CalcJobNode, so it includes queue wait.\n")
        handle.write("# cached=1 means the node was cloned from an earlier run, so it never\n")
        handle.write("# executed and elapsed_s is left empty on purpose.  Only cached=0 rows\n")
        handle.write("# can support a cost argument.\n")
        handle.write("# n_scf_steps is not parsed yet; leave it empty rather than guess.\n")
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else
                                ["ecutjy_Ry", "r_cut_AU", "geometry", "elapsed_s",
                                 "n_scf_steps", "workchain_pk", "calcjob_pk"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
