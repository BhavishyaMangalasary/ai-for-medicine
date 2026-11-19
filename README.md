# NHANES screener for undiagnosed diabetes

A community-health-worker screening aid: for a US adult with no diabetes diagnosis, reassure or recommend a finger-stick A1c. Compared against the ADA Diabetes Risk Test on the same NHANES variables.

> Work in progress. Sections below are filled in by issue #14.

## Problem and who has it

TBD (#14)

## Method

TBD (#14)

## Evaluation

TBD (#14). Will state the metric, how it was measured, results with CIs, and the A1c drift flag if triggered (#3).

## Who benefits, and who could be harmed

TBD (#14)

## Limitations

TBD (#14)

## What I would do with another month

TBD (#14)

## How to run

Python 3.12.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt   # exact versions; requirements.lock has the full freeze
scripts/run_all.sh                          # tests, then downloads NHANES (~100 MB, first run only) and checks it;
                                            # more pipeline stages are added as tickets land
```

Seeds: one global `SEED` in `src/screener/__init__.py`; use `make_rng(stream)` for every random operation.

## AI tools disclosure

TBD (#14)

## Attribution

TBD (#14)
