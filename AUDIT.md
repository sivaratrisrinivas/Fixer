# Eval audit (2026-10-03)

Scope: the seeded-bug eval in `evals/` run with a real model for the first time.

## What ran

Gemini API free tier, key on the maintainer's account, writes auto-approved, max 15 steps, pristine tests used for judging.

| Model | Tasks | Passed | Tampered | Mean steps | Notes |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 6 | 6 | 0 | 7.0 | full run, about 6,500 prompt and 250 output tokens per task |
| gemini-2.5-flash | 3 | 3 | 0 | 6.0 | stopped: free tier is 20 requests per day for this model |
| gemini-3.5-flash | 1 | 1 | 0 | 6.0 | stopped: same 20 per day limit |

## Findings

### The adapter could not run Gemini 3 models
**Status:** Fixed. Gemini 3 returns a thought signature with every function call and returns HTTP 400 if the next request leaves it out. `fixer/gemini.py` rebuilt calls without it. The signature now rides on `ToolCall.signature`. Test: `test_thought_signature_round_trips`.

### No rate-limit handling
**Status:** Fixed. The first run died on a 429. The adapter now spaces calls (`FIXER_MIN_INTERVAL_S`), retries per-minute limits using the server's retry delay, and gives up at once on a per-day quota. The harness records finished tasks and the abort reason instead of losing the whole run.

### The six tasks no longer separate models
**Status:** Problem exists. The smallest model passed 6/6 with the reference one-line fix every time. The eval still proves the loop, the judge and the tamper check work, but a pass rate here says little about model quality.
**Fix:** add harder tasks: a bug that spans two files, a prompt that names the wrong function, a task where the obvious fix breaks another test, and a task where the right answer is to change nothing.

### Process, not just outcome
**Status:** Observed, not gated. gemini-2.5-flash edited before reproducing on 2 of 3 tasks, and its first `mutable_default` fix was incomplete (the test caught it). flash-lite reproduced first on all 6. Transcripts are in `evals/recorded/` so this can be checked by reading.

### Tampering
**Status:** OK. 0 of 10 real-model task runs touched a protected test file. The scripted `tamper` model still shows the check works (6 of 6 flagged).

### Repo hygiene
**Status:** Fixed. `.gitignore` had `__pycache__/` and `.venv/` on one line, so neither was ignored and 15 `.pyc` files were committed. They are removed.

## Not done

- Full 6-task runs on gemini-2.5-flash and gemini-3.5-flash need a day with unused free quota (20 requests per model per day is less than one run).
- CI does not run the real-model eval; it has no API key, and the offline gates (oracle 6/6, no-op 0/6) stay as they are.
