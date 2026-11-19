"""Scaffold contract: folders from AGENTS.md, ignored data, pinned deps, README sections."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FOLDERS = ["src", "tests", "scripts", "app", "artifacts", "docs"]

README_SECTIONS = [
    "Problem and who has it",
    "Method",
    "Evaluation",
    "Who benefits, and who could be harmed",
    "Limitations",
    "What I would do with another month",
    "How to run",
    "AI tools disclosure",
    "Attribution",
]


def test_owner_table_folders_exist():
    for folder in FOLDERS:
        assert (ROOT / folder).is_dir(), f"missing folder: {folder}"


def test_data_dir_is_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", "-q", "data/raw/example.xpt"], cwd=ROOT
    )
    assert result.returncode == 0, "data/ must be gitignored"


def test_requirements_are_exactly_pinned():
    lines = [
        line.strip()
        for line in (ROOT / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lines, "requirements.txt is empty"
    for line in lines:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][A-Za-z0-9_.+-]*", line), line


def test_python_version_is_pinned():
    assert re.fullmatch(r"3\.\d+", (ROOT / ".python-version").read_text().strip())


def test_readme_has_required_sections():
    text = (ROOT / "README.md").read_text()
    headings = re.findall(r"^#{1,3}\s+(.+?)\s*$", text, flags=re.MULTILINE)
    for section in README_SECTIONS:
        assert section in headings, f"README missing heading: {section}"


def test_run_all_exists_and_is_executable():
    script = ROOT / "scripts" / "run_all.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111, "run_all.sh must be executable"
