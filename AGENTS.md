# Rules for every agent in this repo

## 1. Ownership
- Each area has one owner agent (table in section 5). Only edit files inside your own folders.
- Need a change elsewhere? Stop and tell me what and why. Do not edit it yourself.
- If more than one agent is running, each works in its own git worktree and branch.

## 2. I am the lead
- I decide what gets built and who owns what. Ask me before changing scope, adding a dependency, or touching another area.
- Keep the demo path working at all times. Nice-to-have tickets come after must-haves.

## 3. Workflow
1. Take one GitHub issue at a time. Say which one.
2. Branch `<issue#>-<slug>` from a fresh `main`.
3. Small commits. Stage only your own files. Never run `git add -A`.
4. Open a PR with `Closes #N`. Merge only after it runs locally.
5. `git fetch` and rebase before pushing. Never force-push `main`.
6. If you change something others depend on (API route, schema, env var), tell me in your summary.

## 4. Secrets and checks
- Never print, log, commit or post an API key. Keys go in `.env.local`, which is gitignored.
- Call model and payment APIs from server code, never from the client.
- Before saying something is done, run it or its test, and say what you ran.
- When your context is getting full, run handoff and write the handoff file before stopping.

## 5. Who owns what
Solo project: one owner (Claude Code, main, working for the lead) owns every folder below. `data/` holds raw and processed NHANES files and is gitignored.

| Area | Agent | Folders |
|---|---|---|
| Pipeline: data load, cohort and label, features, models, evaluation | Claude Code (main) | `src/`, `tests/`, `scripts/` |
| Demo app (Gradio, deployed as a Hugging Face Space) | Claude Code (main) | `app/` |
| Frozen model, thresholds and result files | Claude Code (main) | `artifacts/` |
| README, write-up, design notes, video script | Claude Code (main) | `docs/`, `README.md` |