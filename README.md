# Fixer

A small coding agent for the terminal. You point it at a project directory and describe a bug. It reads the code, runs the tests, proposes a change as a diff, waits for you to approve it, and then re-runs the tests. Gemini drives it through function calling, but the loop, the tools and the eval don't depend on any one provider.

```bash
pip install -r requirements.txt
echo 'GEMINI_API_KEY=...' > .env
python -m fixer "3 + 7 * 2 should be 17" --dir calculator
```

## What it can do

| Tool | What it does |
| --- | --- |
| `list_files` | List a directory, hiding `.git`, `__pycache__`, virtualenvs and similar noise |
| `read_file` | Read UTF-8 text, capped at 10,000 characters |
| `write_file` | Show a unified diff and write only after you approve it |
| `run_python` | Run a `.py` file with arguments; 30 s timeout, output capped |
| `run_tests` | Run pytest, or unittest discovery if pytest isn't installed, and report the result |

The model may ask for several tools in one turn, and all of them run. Each run is limited to `--max-steps` model turns (default 20).

## Safety

- **Containment.** Every path is resolved with symlinks followed and must stay inside `--dir`. Absolute paths, `..`, symlinks that leave the tree and sibling folders with the same prefix are all refused. The old `startswith` check allowed `../app-secrets` for a root of `app`.
- **Approval before writes.** You see the diff and answer `y` or `N`. Without a terminal, writes are refused unless you pass `--yes`.
- **No secrets for child processes.** Code the agent runs gets a minimal environment, so `GEMINI_API_KEY` and other variables don't leak into it.
- **Errors go back to the model.** A rejected write or a missing file comes back as text the model can react to, not as a crash.

## Evals

`evals/` holds six seeded-bug tasks: operator precedence, an off-by-one in pagination, a mutable default argument, slug case, divide by zero and a unit conversion. Each task is a small repo, a prompt and the tests that define "fixed".

For each task the harness copies the repo to a temp dir and runs the agent with writes auto-approved. It then judges the result **itself**: it re-runs pristine copies of the task's tests, and a run that edited a test file fails outright.

```bash
python -m evals.run --model oracle      # scripted reference fix
python -m evals.run --model noop        # looks around, changes nothing
python -m evals.run --model tamper      # rewrites the tests to pass
GEMINI_API_KEY=... python -m evals.run --model gemini --out evals/results/gemini.json
```

Results from this repo (offline scripted models, Python 3.12):

| Model | Passed | Tampered | Mean steps | Mean tool calls |
| --- | --- | --- | --- | --- |
| oracle | 6/6 | 0 | 5.0 | 5.0 |
| noop | 0/6 | 0 | 2.0 | 1.0 |
| tamper | 0/6 | 6 | 3.0 | 2.0 |

The scripted models exist to show that the harness can tell a real fix from no change or from gamed tests. A harness that scores everything 100% measures nothing. The oracle also checks that the loop runs several tool calls in one turn.

Real Gemini runs (2026-10-03, Gemini API free tier, writes auto-approved, max 15 steps):

| Model | Tasks run | Passed | Tampered | Mean steps | Mean tool calls |
| --- | --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | 6 | 6/6 | 0 | 7.0 | 6.0 |
| gemini-2.5-flash | 3 (stopped by quota) | 3/3 | 0 | 6.0 | 5.0 |
| gemini-3.5-flash | 1 (stopped by quota) | 1/1 | 0 | 6.0 | 6.0 |

Only the flash-lite row is a full run. The free tier allows 20 requests per day each for gemini-2.5-flash and gemini-3.5-flash, and a 6-task run needs about 40, so those runs stopped partway. JSON and readable transcripts are in `evals/recorded/`.

What the transcripts show:

- gemini-3.5-flash-lite made the same one-line fix as the reference on every task, with one write each, and ran the tests before and after.
- gemini-2.5-flash skipped running the tests before editing on 2 of 3 tasks. On `mutable_default` its first fix still mutated the caller's list; the failing test caught it, and the second write fixed it.
- No run touched a test file.
- 6/6 on the smallest model means these six tasks are now too easy to separate models. They still catch a broken agent loop, which is what found the bug below. Harder tasks (bugs spread over two files, misleading prompts, failing tests that need reading a traceback) are the next step.

Bug found by the real run: Gemini 3 models return a "thought signature" with each function call and reject the next request if it is not sent back. The adapter dropped it, so every Gemini 3 run failed on step 2 with HTTP 400. It now keeps the signature on each `ToolCall`. The adapter also spaces calls (`FIXER_MIN_INTERVAL_S`), retries per-minute 429s using the server's retry delay, and stops on a daily quota instead of retrying. The harness keeps finished tasks when a provider error stops a run, and `--transcripts DIR` writes one readable log per task.

```bash
GEMINI_API_KEY=... FIXER_MIN_INTERVAL_S=5 python -m evals.run --model gemini --gemini-model gemini-3.5-flash-lite \
  --out evals/recorded/gemini-3.5-flash-lite.json --transcripts evals/recorded/transcripts-gemini-3.5-flash-lite
```

## Layout

```
fixer/workspace.py   path containment
fixer/tools.py       tools, diff and approval, subprocess sandboxing
fixer/agent.py       provider-neutral loop (Model.step -> Reply)
fixer/gemini.py      Gemini adapter (default gemini-2.5-flash, override with --model or FIXER_MODEL)
fixer/cli.py         python -m fixer
evals/               seeded tasks, scripted models, harness, recorded Gemini runs
tests/               37 pytest tests
calculator/          demo project to point the agent at
```

## Development

```bash
pip install -r requirements-dev.txt
pytest --cov=fixer --cov=evals
ruff check . && ruff format --check .
```

CI runs lint, the tests (89% coverage), and the offline eval with a gate: the oracle must pass every task and the no-op baseline must pass none.
