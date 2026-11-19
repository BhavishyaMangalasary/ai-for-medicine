#!/usr/bin/env python3
"""Download the public NHANES XPT files into data/raw/<cycle>/ and record SHA-256 in a manifest.

Idempotent: files already present and matching the manifest are skipped. A file whose checksum
differs from the manifest is an error (never silently overwritten). Standard library only.
Run from the repo root:  python scripts/fetch_nhanes.py
"""
import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from screener import nhanes as nh  # noqa: E402


def fetch(cycle, component, raw_dir, manifest):
    dest = raw_dir / cycle.name / nh.file_name(cycle, component)
    url = nh.file_url(cycle, component)
    rel = dest.relative_to(raw_dir).as_posix()
    known = nh._read_manifest(manifest)["files"].get(rel)
    if dest.exists() and known:
        if nh.sha256_file(dest) != known["sha256"]:
            raise SystemExit(f"checksum mismatch for existing {rel}; delete it deliberately to refetch")
        return "skip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    req = urllib.request.Request(url, headers={"User-Agent": "nhanes-fetch"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    if not nh.is_xpt(tmp):
        tmp.unlink()
        raise SystemExit(f"{url} did not return a SAS transport file")
    tmp.rename(dest)
    nh.record_in_manifest(manifest, raw_dir, dest, url)
    return "downloaded"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    args = ap.parse_args()
    raw_dir = args.raw_dir
    manifest = raw_dir / "manifest.json"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for cycle in nh.CYCLES:
        for comp in nh.COMPONENTS:
            status = fetch(cycle, comp, raw_dir, manifest)
            print(f"{status:10s} {cycle.name}/{nh.file_name(cycle, comp)}")
    bad = nh.verify_manifest(manifest, raw_dir)
    if bad:
        raise SystemExit(f"manifest verification failed: {bad}")
    print(f"manifest ok: {len(nh._read_manifest(manifest)['files'])} files")


if __name__ == "__main__":
    main()
