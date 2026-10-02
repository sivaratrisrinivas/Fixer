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

The scripted models exist to show that the harness can tell a real fix from no change or from gamed tests. A harness that scores everything 100% measures nothing. The oracle also checks that the loop runs several tool calls in one turn. Real model numbers come from `--model gemini`. They haven't been recorded here because this repo's CI has no API key.

## Layout

```
fixer/workspace.py   path containment
fixer/tools.py       tools, diff and approval, subprocess sandboxing
fixer/agent.py       provider-neutral loop (Model.step -> Reply)
fixer/gemini.py      Gemini adapter (default gemini-2.5-flash, override with --model or FIXER_MODEL)
fixer/cli.py         python -m fixer
evals/               seeded tasks, scripted models, harness
tests/               31 pytest tests
calculator/          demo project to point the agent at
```

## Development

```bash
pip install -r requirements-dev.txt
pytest --cov=fixer --cov=evals
ruff check . && ruff format --check .
```

CI runs lint, the tests (88% coverage), and the offline eval with a gate: the oracle must pass every task and the no-op baseline must pass none.
