"""Unit tests for the NHANES loader. Real-data checks live in test_nhanes_integration.py."""
import hashlib
import json

import pandas as pd
import pytest

from screener import nhanes as nh


def test_cycles_dev_and_test_layout():
    names = {c.name: c.role for c in nh.CYCLES}
    assert names == {
        "2011-12": "dev",
        "2013-14": "dev",
        "2015-16": "dev",
        "2017-2020": "test",
    }


def test_file_name_dev_suffix_and_test_prefix():
    dev = nh.cycle_by_name("2011-12")
    test = nh.cycle_by_name("2017-2020")
    assert nh.file_name(dev, "DEMO") == "DEMO_G.xpt"
    assert nh.file_name(nh.cycle_by_name("2013-14"), "GHB") == "GHB_H.xpt"
    assert nh.file_name(nh.cycle_by_name("2015-16"), "SMQ") == "SMQ_I.xpt"
    assert nh.file_name(test, "GHB") == "P_GHB.xpt"


def test_file_url():
    assert nh.file_url(nh.cycle_by_name("2013-14"), "GHB") == (
        "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/GHB_H.xpt"
    )
    assert nh.file_url(nh.cycle_by_name("2017-2020"), "DEMO") == (
        "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_DEMO.xpt"
    )


def test_components_are_the_nine_agreed():
    assert nh.COMPONENTS == ("DEMO", "DIQ", "GHB", "BMX", "BPQ", "MCQ", "RHQ", "PAQ", "SMQ")


def test_is_xpt_accepts_real_header_and_rejects_html(tmp_path):
    good = tmp_path / "a.xpt"
    good.write_bytes(b"HEADER RECORD*******LIBRARY HEADER RECORD!!!!!!!000000000000000000000000000000  ")
    bad = tmp_path / "b.xpt"
    bad.write_bytes(b"<!DOCTYPE html><html>Page Not Found</html>")
    assert nh.is_xpt(good)
    assert not nh.is_xpt(bad)


def test_manifest_roundtrip_and_tamper_detection(tmp_path):
    f = tmp_path / "2011-12" / "DEMO_G.xpt"
    f.parent.mkdir()
    f.write_bytes(b"abc")
    manifest = tmp_path / "manifest.json"
    nh.record_in_manifest(manifest, tmp_path, f, url="http://x/DEMO_G.xpt")
    entry = json.loads(manifest.read_text())["files"]["2011-12/DEMO_G.xpt"]
    assert entry["sha256"] == hashlib.sha256(b"abc").hexdigest()
    assert entry["bytes"] == 3
    assert nh.verify_manifest(manifest, tmp_path) == []
    f.write_bytes(b"abd")
    assert nh.verify_manifest(manifest, tmp_path) == ["2011-12/DEMO_G.xpt"]
    f.unlink()
    assert nh.verify_manifest(manifest, tmp_path) == ["2011-12/DEMO_G.xpt"]


def _fake_reader_factory(tables):
    """tables: {file_name: DataFrame}. Returns a reader(path) like read_xpt."""

    def reader(path):
        return tables[path.name].copy()

    return reader


def test_load_cycle_merges_on_seqn_adds_cycle_and_dev_weight(tmp_path):
    cyc = nh.cycle_by_name("2011-12")
    d = tmp_path / cyc.name
    d.mkdir()
    tables = {
        "DEMO_G.xpt": pd.DataFrame(
            {"SEQN": [1, 2, 3], "RIDAGEYR": [30, 50, 70], "WTMEC2YR": [300.0, 600.0, 0.0],
             "SDMVSTRA": [90, 90, 91], "SDMVPSU": [1, 2, 1]}
        ),
        "GHB_G.xpt": pd.DataFrame({"SEQN": [1, 2], "LBXGH": [5.4, 6.7]}),
    }
    for name in tables:
        (d / name).write_bytes(b"x")
    out = nh.load_cycle(cyc, tmp_path, components=("DEMO", "GHB"), reader=_fake_reader_factory(tables))
    assert list(out["SEQN"]) == [1, 2, 3]
    assert set(out["cycle"]) == {"2011-12"}
    assert out.loc[out.SEQN == 1, "LBXGH"].item() == 5.4
    assert pd.isna(out.loc[out.SEQN == 3, "LBXGH"].item())  # not examined -> no lab
    # dev weights are divided by 3 so pooling three cycles keeps the population total
    assert out["weight_mec"].tolist() == [100.0, 200.0, 0.0]
    assert out["strata_key"].tolist() == ["2011-12:90", "2011-12:90", "2011-12:91"]


def test_load_cycle_test_uses_pre_pandemic_weight_undivided(tmp_path):
    cyc = nh.cycle_by_name("2017-2020")
    d = tmp_path / cyc.name
    d.mkdir()
    tables = {
        "P_DEMO.xpt": pd.DataFrame(
            {"SEQN": [9], "RIDAGEYR": [40], "WTMECPRP": [500.0], "SDMVSTRA": [150], "SDMVPSU": [1]}
        ),
    }
    (d / "P_DEMO.xpt").write_bytes(b"x")
    out = nh.load_cycle(cyc, tmp_path, components=("DEMO",), reader=_fake_reader_factory(tables))
    assert out["weight_mec"].tolist() == [500.0]
    assert "2017-2020:150" in out["strata_key"].tolist()


def test_load_cycle_coerces_seqn_to_int(tmp_path):
    cyc = nh.cycle_by_name("2015-16")
    d = tmp_path / cyc.name
    d.mkdir()
    tables = {"DEMO_I.xpt": pd.DataFrame({"SEQN": [83732.0], "WTMEC2YR": [3.0],
                                          "SDMVSTRA": [119.0], "SDMVPSU": [1.0]})}
    (d / "DEMO_I.xpt").write_bytes(b"x")
    out = nh.load_cycle(cyc, tmp_path, components=("DEMO",), reader=_fake_reader_factory(tables))
    assert out["SEQN"].dtype.kind == "i"


def test_stratum_collisions_detects_raw_id_shared_across_cycles():
    a = pd.DataFrame({"cycle": ["A"] * 2, "SDMVSTRA": [90, 91]})
    b = pd.DataFrame({"cycle": ["B"] * 2, "SDMVSTRA": [91, 92]})
    assert nh.stratum_collisions([a, b]) == {91}
    c = pd.DataFrame({"cycle": ["C"], "SDMVSTRA": [150]})
    assert nh.stratum_collisions([a, c]) == set()


def test_check_columns_reports_missing_by_variable():
    cyc = nh.cycle_by_name("2011-12")
    frame = pd.DataFrame(columns=["SEQN", "RIDAGEYR", "LBXGH"])
    missing = nh.check_columns(frame, cyc)
    assert "LBXGH" not in missing
    assert "RHQ162" in missing and "SMQ020" in missing
    assert "WTMEC2YR" in missing  # the dev weight is required in the dev frame


def test_required_columns_cover_the_approved_list():
    required = set(nh.REQUIRED_VARS_BY_COMPONENT["DEMO"]) | set(nh.REQUIRED_VARS_BY_COMPONENT["SMQ"])
    assert {"RIDAGEYR", "RIAGENDR", "RIDRETH3", "RIDEXPRG", "DMDEDUC2",
            "SDMVSTRA", "SDMVPSU", "SMQ020"} <= required
    all_vars = {v for vs in nh.REQUIRED_VARS_BY_COMPONENT.values() for v in vs}
    assert {"LBXGH", "DIQ010", "DIQ050", "DIQ070", "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST",
            "BPQ020", "MCQ300C", "RHQ162", "PAQ605", "PAQ620", "PAQ635", "PAQ650",
            "PAQ665"} <= all_vars
