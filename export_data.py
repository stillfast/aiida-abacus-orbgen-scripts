#!/usr/bin/env python
"""Export every campaign result that lives in AiiDA to plain files.

Nothing here recomputes anything: it walks the WorkChainNodes of the three stages and
writes what they already recorded, so the numbers can be inspected, diffed and shipped
without a database.

    python export_data.py --out out/          # JSON + CSV + a summary table
    python export_data.py --out out/ --archive # also `verdi archive create`

Outputs
-------
orbgen_base.csv    one row per (r_cut, ecutjy, l_max): spillages, orbital files,
                   primitive-basis SCF energies and the TSW-vs-PW deltas
eos.csv            one row per EOS fit: V0, B0, B0', E0, rms
all.json           everything above, plus the provenance (PKs, labels)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

KCAL_MEV = 43.364
EOS_GROUPS = ("orbgen-rcut-ecutjy", "orbgen-rcut-ecutjy-d2", "orbgen-control-r10-j150")


def scf_energy(node):
    if "retrieved" not in node.outputs:
        return None
    for sub in ("OUT.aiida", "OUT.ABACUS"):
        try:
            text = node.outputs.retrieved.get_object_content(f"{sub}/running_scf.log")
        except Exception:                                        # noqa: BLE001
            continue
        hits = re.findall(r"!FINAL_ETOT_IS\s+(-?[0-9.]+)", text)
        if hits:
            return float(hits[-1])
    return None


def collect_orbgen(pw_refs):
    from aiida.orm import Group

    rows, seen = [], set()
    for label in EOS_GROUPS:
        try:
            group = Group.collection.get(label=label)
        except Exception:                                        # noqa: BLE001
            continue
        for node in group.nodes:
            if type(node).__name__ != "WorkChainNode":
                continue
            if node.process_state.value != "finished" or node.exit_status != 0:
                continue
            s = node.inputs.settings.get_dict()
            key = (s["ecutjy"], s["r_cut"], s["l_max"])
            if key in seen:
                continue
            seen.add(key)
            from aiida_abacus_orbgen.utils import decode_config
            result = decode_config(node.outputs.result.get_dict())
            energies, deltas = {}, []
            for child in node.called:
                if type(child).__name__ != "CalcJobNode":
                    continue
                m = re.search(r"dimer_(\d)_(\d+)_", child.label or "")
                if m:
                    e = scf_energy(child)
                    if e is not None:
                        energies[f"{m.group(1)}.{m.group(2)}"] = e
            for bl, epw in pw_refs.items():
                if energies.get(bl) is not None:
                    deltas.append((energies[bl] - epw) / 2.0 * 1000.0)
            rows.append({
                "pk": node.pk, "r_cut": s["r_cut"], "ecutjy": s["ecutjy"],
                "l_max": s["l_max"], "nbf_per_atom": result.get("nbf_per_atom"),
                "spillages": result.get("spillages"),
                "orbitals": result.get("nao_orbitals"),
                "scf_energies_eV": energies,
                "dE_meV_per_atom": round(sum(deltas) / len(deltas), 2) if deltas else None,
                "dE_kcal_per_atom": round(sum(deltas) / len(deltas) / KCAL_MEV, 3) if deltas else None,
            })
    return sorted(rows, key=lambda r: (r["ecutjy"], r["r_cut"]))


def collect_eos():
    from aiida.orm import QueryBuilder, WorkChainNode

    rows = []
    for (node,) in QueryBuilder().append(
            WorkChainNode, filters={"process_type": {"like": "%orbgen.eos%"}}).all():
        if node.process_state.value != "finished":
            continue
        try:
            d = node.outputs.eos.get_dict()
        except Exception:                                        # noqa: BLE001
            continue
        rows.append({"pk": node.pk, "orbital": d.get("orbital"),
                     "V0_per_atom": round(d["V0_per_atom"], 6), "B0_GPa": round(d["B0_GPa"], 3),
                     "BP": round(d["BP"], 3), "E0_eV": round(d["E0"], 6),
                     "rms_meV": round(d["rms_meV"], 4), "npoints": d["npoints"],
                     "scales": d["scales"]})
    return sorted(rows, key=lambda r: r["pk"])


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = {k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                     for k, v in row.items()}
            writer.writerow(clean)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="out", help="output directory")
    ap.add_argument("--archive", action="store_true", help="also create an AiiDA archive")
    args = ap.parse_args()

    from aiida import load_profile
    load_profile("aiida_profile")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # PW reference at ecutwfc 180, 35 Bohr cell (stage-1 ladder)
    pw_refs = {"2.10": -4951.807006023504, "2.40": -4952.064018093108}

    orbgen = collect_orbgen(pw_refs)
    eos = collect_eos()

    write_csv(out / "orbgen_base.csv", orbgen,
              ["pk", "r_cut", "ecutjy", "l_max", "nbf_per_atom", "spillages",
               "dE_meV_per_atom", "dE_kcal_per_atom", "orbitals", "scf_energies_eV"])
    write_csv(out / "eos.csv", eos,
              ["pk", "orbital", "V0_per_atom", "B0_GPa", "BP", "E0_eV", "rms_meV",
               "npoints", "scales"])
    (out / "all.json").write_text(json.dumps(
        {"pw_reference_eV": pw_refs, "orbgen_base": orbgen, "eos": eos}, indent=2))

    print(f"{'stage':<12}{'rows':>6}")
    print(f"{'orbgen_base':<12}{len(orbgen):>6}")
    print(f"{'eos':<12}{len(eos):>6}")
    print(f"\nwrote {out}/orbgen_base.csv, {out}/eos.csv, {out}/all.json")

    if orbgen:
        print(f"\n{'ecutjy':>7}{'r_cut':>7}{'nbf':>6}  {'dE meV/at':>10}{'kcal/at':>9}")
        for r in orbgen:
            print(f"{r['ecutjy']:>7g}{r['r_cut']:>7g}{r['nbf_per_atom']:>6}"
                  f"{str(r['dE_meV_per_atom']):>10}{str(r['dE_kcal_per_atom']):>9}")
    if eos:
        print(f"\n{'pk':>7}  {'V0/atom':>9}{'B0 GPa':>9}{'B0p':>7}{'rms meV':>9}  orbital")
        for r in eos:
            print(f"{r['pk']:>7}  {r['V0_per_atom']:>9.4f}{r['B0_GPa']:>9.1f}"
                  f"{r['BP']:>7.2f}{r['rms_meV']:>9.3f}  {r['orbital']}")

    if args.archive:
        import subprocess
        pks = [str(r["pk"]) for r in orbgen + eos]
        cmd = ["verdi", "-p", "aiida_profile", "archive", "create",
               "--description", "orbgen campaign (stages 1-3)", str(out / "campaign.aiida")]
        for pk in pks:
            cmd.extend(["-n", pk])
        print("\n" + " ".join(cmd))
        subprocess.run(cmd, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
