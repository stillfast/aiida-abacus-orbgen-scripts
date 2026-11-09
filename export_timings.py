#!/usr/bin/env python
"""Wall time of every primitive-basis SCF, parsed from ABACUS itself.

ABACUS ends ``running_scf.log`` with

    Start  Time  : Fri Nov  6 14:37:35 2026
    Finish Time  : Fri Nov  6 14:39:56 2026
    Total  Time  : 0 h 2 mins 21 secs

so the number is the run's own wall clock and survives being copied into a cached node
(a cached node reuses the *original* retrieved folder, so its log is the real run).
That is why this parser is used instead of ``mtime - ctime``, which is ~0 for a cache
hit and would silently make the scan look free.

    python export_timings.py --out 2-rcut-ecutjy/data/timings.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

GROUPS = ("orbgen-rcut-ecutjy", "orbgen-rcut-ecutjy-d2", "orbgen-control-r10-j150")
TOTAL = re.compile(r"Total\s+Time\s*:\s*(\d+)\s*h\s*(\d+)\s*mins?\s*(\d+)\s*secs?")
ITER = re.compile(r"^\s*(?:GE|CG|DA)\s*\d+", re.M)


def total_seconds(text: str):
    m = TOTAL.search(text)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


def log_of(node):
    for sub in ("OUT.aiida", "OUT.ABACUS"):
        try:
            return node.outputs.retrieved.get_object_content(f"{sub}/running_scf.log")
        except Exception:                                        # noqa: BLE001
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="2-rcut-ecutjy/data/timings.csv")
    args = ap.parse_args()

    from aiida import load_profile
    from aiida.orm import Group

    load_profile("aiida_profile")
    rows, seen = [], set()
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
            key = (s["ecutjy"], s["r_cut"])
            if key in seen:
                continue
            seen.add(key)
            for child in wc.called:
                if type(child).__name__ != "CalcJobNode":
                    continue
                text = log_of(child)
                if text is None:
                    continue
                secs = total_seconds(text)
                if secs is None:
                    continue
                rows.append({"ecutjy_Ry": s["ecutjy"], "r_cut_AU": s["r_cut"],
                             "geometry": child.label.replace("scf-", ""),
                             "n_scf_iter": len(ITER.findall(text)),
                             "wall_s": secs,
                             "cached": int(child.base.caching.is_created_from_cache),
                             "calcjob_pk": child.pk})
    rows.sort(key=lambda r: (r["ecutjy_Ry"], r["r_cut_AU"], r["geometry"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        handle.write("# Wall time per primitive-basis SCF, parsed from ABACUS's own\n")
        handle.write("# tail line 'Total Time : X h Y mins Z secs' in running_scf.log.\n")
        handle.write("# This is valid even for cached nodes: a cached CalcJob reuses the\n")
        handle.write("# original retrieved folder, so the log is the real run.  A\n")
        handle.write("# mtime-ctime estimate would read ~0 s for those and be useless.\n")
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} ({len(rows)} SCFs)")

    agg = {}
    for r in rows:
        agg.setdefault((r["ecutjy_Ry"], r["r_cut_AU"]), []).append(r)
    print(f"\n{'ecutjy':>7}{'r_cut':>7}{'SCF 数':>7}{'总时间 (min)':>14}{'单体 (min)':>13}{'单点均值 (min)':>16}")
    for (e, rc), rs in sorted(agg.items()):
        tot = sum(r["wall_s"] for r in rs) / 60
        mono = [r["wall_s"] for r in rs if "monomer" in r["geometry"]]
        print(f"{e:>7g}{rc:>7g}{len(rs):>7}{tot:>14.1f}"
              f"{(mono[0]/60 if mono else 0):>13.1f}{tot/len(rs):>16.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
