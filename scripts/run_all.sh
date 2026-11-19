#!/usr/bin/env bash
# One-command reproduce script. Stub: grows as the pipeline tickets land (#3-#10).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3

echo "== tests =="
"$PY" -m pytest -q

echo "== data: fetch (skips files already present; about 100 MB on the first run) =="
"$PY" scripts/fetch_nhanes.py

echo "== data: load check =="
"$PY" scripts/check_nhanes.py

echo "== pipeline =="
echo "Not implemented yet: A1c drift (#3), cohort (#4), features (#5), ADA baseline (#6),"
echo "models (#8), band (#9), test evaluation (#10)."
