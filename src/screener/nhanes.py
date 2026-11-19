"""Locate, verify and load the public NHANES files.

Dev cycles: 2011-12 (_G), 2013-14 (_H), 2015-16 (_I). Test: 2017-March 2020 pre-pandemic
(P_ files). Weights: dev uses WTMEC2YR divided by 3 (so pooling three 2-year cycles keeps one
population total); test uses WTMECPRP only. Never use the single-cycle 2017-18 / 2019-20 files.

Nothing here computes outcomes. The test-set lock arrives in issue #7.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"

COMPONENTS = ("DEMO", "DIQ", "GHB", "BMX", "BPQ", "MCQ", "RHQ", "PAQ", "SMQ")


@dataclass(frozen=True)
class Cycle:
    name: str  # also the sub-directory under data/raw/
    role: str  # "dev" or "test"
    year_folder: str  # CDC folder: the cycle start year
    suffix: str = ""  # "_G" style, dev cycles
    prefix: str = ""  # "P_" style, the pre-pandemic file
    weight_col: str = "WTMEC2YR"
    weight_divisor: float = 3.0


CYCLES: tuple[Cycle, ...] = (
    Cycle("2011-12", "dev", "2011", suffix="_G"),
    Cycle("2013-14", "dev", "2013", suffix="_H"),
    Cycle("2015-16", "dev", "2015", suffix="_I"),
    Cycle("2017-2020", "test", "2017", prefix="P_", weight_col="WTMECPRP", weight_divisor=1.0),
)

# Variables named in the approved column list (docs/columns.md lands in #5), by component.
# Banned variables are deliberately not listed: they are never required.
REQUIRED_VARS_BY_COMPONENT: dict[str, tuple[str, ...]] = {
    "DEMO": ("SEQN", "RIDAGEYR", "RIAGENDR", "RIDRETH3", "RIDEXPRG", "DMDEDUC2",
             "SDMVSTRA", "SDMVPSU"),
    "DIQ": ("DIQ010", "DIQ050", "DIQ070"),
    "GHB": ("LBXGH",),
    "BMX": ("BMXWT", "BMXHT", "BMXBMI", "BMXWAIST"),
    "BPQ": ("BPQ020",),
    "MCQ": ("MCQ300C",),
    "RHQ": ("RHQ162",),
    "PAQ": ("PAQ605", "PAQ620", "PAQ635", "PAQ650", "PAQ665"),
    "SMQ": ("SMQ020",),
}


def cycle_by_name(name: str) -> Cycle:
    for c in CYCLES:
        if c.name == name:
            return c
    raise KeyError(name)


def file_name(cycle: Cycle, component: str) -> str:
    return f"{cycle.prefix}{component}{cycle.suffix}.xpt"


def file_url(cycle: Cycle, component: str) -> str:
    return f"{BASE_URL}/{cycle.year_folder}/DataFiles/{file_name(cycle, component)}"


def is_xpt(path: Path) -> bool:
    """True if the file starts with the SAS transport header (not, say, an HTML error page)."""
    magic = b"HEADER RECORD*******LIBRARY"
    with open(path, "rb") as fh:
        return fh.read(len(magic)) == magic


# ----------------------------------------------------------------------------- manifest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_manifest(manifest: Path) -> dict:
    if manifest.exists():
        return json.loads(manifest.read_text())
    return {"files": {}}


def record_in_manifest(manifest: Path, raw_dir: Path, path: Path, url: str) -> None:
    data = _read_manifest(manifest)
    rel = path.relative_to(raw_dir).as_posix()
    data["files"][rel] = {"url": url, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def verify_manifest(manifest: Path, raw_dir: Path) -> list[str]:
    """Return the relative paths whose file is missing or whose checksum changed."""
    bad = []
    for rel, entry in _read_manifest(manifest)["files"].items():
        p = raw_dir / rel
        if not p.exists() or sha256_file(p) != entry["sha256"]:
            bad.append(rel)
    return sorted(bad)


# ----------------------------------------------------------------------------- loading


def read_xpt(path: Path) -> pd.DataFrame:
    df = pd.read_sas(path, format="xport", encoding="utf-8")
    df.columns = [c.upper() for c in df.columns]
    return df


def load_cycle(
    cycle: Cycle,
    raw_dir: Path,
    components: Iterable[str] = COMPONENTS,
    reader: Callable[[Path], pd.DataFrame] = read_xpt,
) -> pd.DataFrame:
    """One row per DEMO participant (all interviewed), other components left-joined on SEQN.

    Adds: `cycle`, `weight_mec` (exam weight, dev divided by 3), `strata_key` (cycle:stratum).
    Participants not examined have missing lab and exam values.
    """
    frames = {c: reader(raw_dir / cycle.name / file_name(cycle, c)) for c in components}
    out = frames["DEMO"]
    out["SEQN"] = out["SEQN"].astype("int64")
    for comp, df in frames.items():
        if comp == "DEMO":
            continue
        df = df.copy()
        df["SEQN"] = df["SEQN"].astype("int64")
        out = out.merge(df, on="SEQN", how="left", validate="one_to_one")
    out["cycle"] = cycle.name
    out["weight_mec"] = out[cycle.weight_col] / cycle.weight_divisor
    out["strata_key"] = cycle.name + ":" + out["SDMVSTRA"].astype("int64").astype(str)
    return out


def load_dev(raw_dir: Path, reader: Callable[[Path], pd.DataFrame] = read_xpt) -> pd.DataFrame:
    """The three development cycles stacked."""
    frames = [load_cycle(c, raw_dir, reader=reader) for c in CYCLES if c.role == "dev"]
    return pd.concat(frames, ignore_index=True)


def stratum_collisions(frames: Iterable[pd.DataFrame]) -> set[int]:
    """Raw SDMVSTRA ids that appear in more than one cycle. `strata_key` is unique either way."""
    seen: dict[int, set[str]] = {}
    for f in frames:
        for cyc, strata in f.groupby("cycle")["SDMVSTRA"]:
            for s in strata.dropna().astype("int64").unique():
                seen.setdefault(int(s), set()).add(cyc)
    return {s for s, cycles in seen.items() if len(cycles) > 1}


def check_columns(frame: pd.DataFrame, cycle: Cycle) -> list[str]:
    """Required variables (plus this cycle's exam weight) absent from a loaded frame."""
    needed = [v for vs in REQUIRED_VARS_BY_COMPONENT.values() for v in vs] + [cycle.weight_col]
    return [v for v in needed if v not in frame.columns]
