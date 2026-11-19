#!/usr/bin/env bash
# One-command reproduce script. Stub: grows as the pipeline tickets land (#2-#10).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3

echo "== tests =="
"$PY" -m pytest -q

echo "== pipeline =="
echo "Not implemented yet: data load (#2), A1c drift (#3), cohort (#4), features (#5),"
echo "ADA baseline (#6), models (#8), band (#9), test evaluation (#10)."
