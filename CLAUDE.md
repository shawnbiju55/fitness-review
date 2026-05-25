# CLAUDE.md — fitness-review pipeline

## Environment

- **OS:** Windows 11. Shell is **PowerShell**, not bash.
- **Python:** 3.14, venv at `.venv\Scripts\python.exe`
- **Encoding:** Always set `$env:PYTHONIOENCODING="utf-8"` before running Python.
- **Git remote:** `origin` → `https://github.com/shawnbiju55/fitness-review.git`, branch `main`.

## Shell rules (CRITICAL)

- Use PowerShell syntax only. No `rm`, no `cat`, no heredocs, no `&&` chaining.
- Use `Remove-Item -Force` for deletions.
- Use semicolons (`;`) to chain commands, not `&&`.
- Commit messages: single-line string, no multi-line, no `--co-authored-by`.
  Example: `git commit -m "chore: description here"`
- Never use `bash` tool. Always use `PowerShell` tool.

## Coding rules (from Karpathy guidelines)

1. **Think before coding.** State assumptions. If uncertain, ask — don't guess.
2. **Simplicity first.** Minimum code that solves the problem. No speculative features. No abstractions for single-use code.
3. **Surgical changes.** Touch only what the task requires. Don't "improve" adjacent code, comments, or formatting. Match existing style. Every changed line must trace to the task.
4. **Goal-driven execution.** For multi-step tasks, state a plan with verifiable checkpoints before starting. Loop until verified.

## File rules

- Do NOT touch: `pull/garmin.py`, `watermarks.db`, anything under `credentials/`, `.env`
- Do NOT add new pip dependencies unless explicitly told to.
- Do NOT create test files, CI configs, or tooling that wasn't asked for.
- Do NOT rename files or restructure directories unless explicitly told to.

## Git rules

- One logical change per commit. Commit message format: `type: description`
  Types: `chore`, `feat`, `fix`, `refactor`, `docs`
- After staging, run `git diff --cached --stat` to confirm only intended files are staged.
- Never force-push. Never rebase onto origin without asking.
- Never run `git stash`. If working tree is dirty, ask.

## Verification protocol

After completing any task:
1. Run: `python -c "import ast; [ast.parse(open(f).read()) for f in [LIST_OF_CHANGED_FILES]]; print('AST OK')"` — confirms no syntax errors.
2. Run: `grep -rn "SEARCH_TERM" *.py pull/ transform/ load/` for any terms that should have been fully removed (e.g., "dayone", "sentiment", "GMAIL_CREDENTIALS_JSON").
3. Re-read every file you changed: `cat <file>` and confirm the content matches what you intended.
4. Run `git diff --cached` before committing. Review the diff. If anything doesn't trace to the task, unstage it.

## Project context

This is an automated Garmin fitness data pipeline:
- `pull/garmin.py` → fetches activities, sleep, daily summaries from Garmin Connect
- `transform/normalize.py` → schema enforcement + dedup
- `transform/analysis.py` → Claude API generates weekly markdown report
- `load/drive.py` → appends CSVs to Google Drive
- `load/gmail.py` → emails weekly report
- `load/watermark.py` → SQLite incremental load tracking
- `load/auth.py` → shared OAuth2 credentials (Drive + Gmail)
- `config.py` → all constants, schema definitions, date helpers
- `run.py` → orchestrator entry point

Data model: three source tables joined on `date`:
- `garmin_activities_master.csv` (1:many per date)
- `garmin_sleep_master.csv` (1:1 per date)
- `garmin_daily_master.csv` (1:1 per date)
