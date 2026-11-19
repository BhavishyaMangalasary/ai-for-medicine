"""Checks against the real downloaded files. Skipped when data/raw/ has not been fetched.
Fetch with:  python scripts/fetch_nhanes.py"""
from pathlib import Path

import pytest

from screener import nhanes as nh

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
pytestmark = pytest.mark.skipif(
    not (RAW / "manifest.json").exists(), reason="NHANES files not downloaded"
)


def test_manifest_lists_all_36_files_and_checksums_match():
    manifest = nh._read_manifest(RAW / "manifest.json")["files"]
    assert len(manifest) == len(nh.CYCLES) * len(nh.COMPONENTS) == 36
    assert nh.verify_manifest(RAW / "manifest.json", RAW) == []


@pytest.fixture(scope="module")
def frames():
    return {c.name: nh.load_cycle(c, RAW) for c in nh.CYCLES}


def test_every_required_column_is_present_in_every_cycle(frames):
    for cycle in nh.CYCLES:
        assert nh.check_columns(frames[cycle.name], cycle) == [], cycle.name


def test_seqn_unique_within_each_cycle_and_weights_positive(frames):
    for name, f in frames.items():
        assert f["SEQN"].is_unique, name
        assert (f["weight_mec"] > 0).all(), name


def test_strata_keys_never_collide_across_cycles(frames):
    keys = {name: set(f["strata_key"]) for name, f in frames.items()}
    names = list(keys)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert keys[a].isdisjoint(keys[b]), (a, b)


def test_dev_pooled_weights_are_a_third_of_the_two_year_weights():
    dev = nh.load_dev(RAW)
    assert set(dev["cycle"]) == {"2011-12", "2013-14", "2015-16"}
    assert ((dev["weight_mec"] * 3 - dev["WTMEC2YR"]).abs() < 1e-6).all()
