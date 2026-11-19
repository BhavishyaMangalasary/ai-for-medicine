#!/usr/bin/env python3
"""Load every cycle, print row counts, check required columns and stratum ids.

Counts and column presence only (A1c presence, never A1c values): no outcomes are computed, so
this never looks at the test labels.
Writes artifacts/nhanes_load_report.json. Run from the repo root:  python scripts/check_nhanes.py
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from screener import nhanes as nh  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--out", type=Path, default=ROOT / "artifacts" / "nhanes_load_report.json")
    args = ap.parse_args()

    bad = nh.verify_manifest(args.raw_dir / "manifest.json", args.raw_dir)
    if bad:
        raise SystemExit(f"manifest verification failed: {bad}")

    report = {"cycles": {}, "stratum_id_collisions": None, "missing_columns": {}}
    frames = []
    for cycle in nh.CYCLES:
        per_component = {}
        for comp in nh.COMPONENTS:
            df = nh.read_xpt(args.raw_dir / cycle.name / nh.file_name(cycle, comp))
            per_component[comp] = len(df)
        merged = nh.load_cycle(cycle, args.raw_dir)
        frames.append(merged)
        missing = nh.check_columns(merged, cycle)
        if missing:
            report["missing_columns"][cycle.name] = missing
        report["cycles"][cycle.name] = {
            "role": cycle.role,
            "rows_per_component": per_component,
            "merged_rows": len(merged),
            "rows_with_a1c": int(merged["LBXGH"].notna().sum()),
            "adults_20plus_with_a1c": int(((merged["RIDAGEYR"] >= 20) & merged["LBXGH"].notna()).sum()),
            "strata_range": [int(merged["SDMVSTRA"].min()), int(merged["SDMVSTRA"].max())],
        }
        print(f"{cycle.name:10s} {cycle.role:4s} merged={len(merged):6d} "
              f"adults20+_with_A1c={report['cycles'][cycle.name]['adults_20plus_with_a1c']:6d} "
              f"strata={report['cycles'][cycle.name]['strata_range']} missing={missing or 'none'}")
    collisions = sorted(nh.stratum_collisions(frames))
    report["stratum_id_collisions"] = collisions
    print("raw SDMVSTRA ids shared across cycles:", collisions or "none")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
