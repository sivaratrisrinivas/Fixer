"""Seeded-bug eval for Fixer.

Each task in evals/tasks/<name>/ has a buggy ``repo/``, the reference ``fix/``
(used only by the oracle) and ``task.json`` with the prompt. For every task the
harness copies the repo to a temp dir, lets the agent work with writes
auto-approved, then judges the result itself:

- it re-runs the original test files from the task, not whatever is on disk,
  so editing the tests can't fake a pass;
- a run that modified a protected test file fails outright.

Usage:
  python -m evals.run --model oracle          # offline, used in CI
  python -m evals.run --model noop
  GEMINI_API_KEY=... python -m evals.run --model gemini [--gemini-model gemini-2.5-flash]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from fixer.agent import run_agent
from fixer.tools import Toolbox
from fixer.workspace import Workspace

from .scripted import SCRIPTED

TASKS_DIR = Path(__file__).parent / "tasks"


@dataclass
class TaskResult:
    task: str
    passed: bool
    tampered: bool
    finished: bool
    steps: int
    tool_calls: int
    files_changed: list[str]
    seconds: float
    prompt_tokens: int
    output_tokens: int


def judge(task_dir: Path, workdir: Path) -> tuple[bool, bool]:
    """Return (tests_pass, tampered) using pristine copies of the task's tests."""
    meta = json.loads((task_dir / "task.json").read_text())
    tampered = any((workdir / p).read_text() != (task_dir / "repo" / p).read_text() for p in meta["protected"])
    with tempfile.TemporaryDirectory() as judge_dir:
        jd = Path(judge_dir)
        for src in workdir.rglob("*.py"):
            if "__pycache__" in src.parts:
                continue
            dest = jd / src.relative_to(workdir)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        for p in meta["protected"]:
            shutil.copy2(task_dir / "repo" / p, jd / p)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *meta["protected"]],
            cwd=jd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    return proc.returncode == 0 and not tampered, tampered


def make_model(name: str, task_dir: Path, gemini_model: str | None):
    if name in SCRIPTED:
        return SCRIPTED[name](task_dir)
    if name == "gemini":
        from fixer.gemini import GeminiModel

        return GeminiModel(model=gemini_model)
    raise SystemExit(f"unknown model {name!r}; choose from {sorted([*SCRIPTED, 'gemini'])}")


def dump_transcript(path: Path, run) -> None:
    """Write a readable log of a run so failures can be read afterwards."""
    lines = []
    for turn in run.transcript:
        if turn.role == "user":
            lines.append(f"USER: {turn.text}")
        elif turn.role == "model":
            if turn.text:
                lines.append(f"MODEL: {turn.text}")
            lines += [f"CALL {c.name} {json.dumps(c.args)[:2000]}" for c in turn.tool_calls]
        else:
            lines += [f"RESULT {r.name}:\n{r.output[:2000]}" for r in turn.results]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def run_task(
    task_dir: Path, model_name: str, max_steps: int, gemini_model: str | None, transcript_dir: Path | None = None
) -> TaskResult:
    meta = json.loads((task_dir / "task.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp) / "repo"
        shutil.copytree(task_dir / "repo", workdir)
        toolbox = Toolbox(Workspace(workdir), approve=lambda path, diff: True)
        model = make_model(model_name, task_dir, gemini_model)
        started = time.perf_counter()
        result = run_agent(model, toolbox, meta["prompt"], max_steps=max_steps)
        seconds = time.perf_counter() - started
        passed, tampered = judge(task_dir, workdir)
        if transcript_dir is not None:
            dump_transcript(transcript_dir / f"{task_dir.name}.txt", result)
    return TaskResult(
        task=task_dir.name,
        passed=passed,
        tampered=tampered,
        finished=result.finished,
        steps=result.steps,
        tool_calls=result.tool_calls,
        files_changed=sorted(set(result.writes)),
        seconds=round(seconds, 3),
        prompt_tokens=result.usage.get("prompt_tokens", 0),
        output_tokens=result.usage.get("output_tokens", 0),
    )


def summarize(model_name: str, results: list[TaskResult]) -> dict:
    n = len(results)
    return {
        "model": model_name,
        "tasks": n,
        "passed": sum(r.passed for r in results),
        "pass_rate": round(sum(r.passed for r in results) / n, 3) if n else 0.0,
        "tampered": sum(r.tampered for r in results),
        "mean_steps": round(sum(r.steps for r in results) / n, 2) if n else 0.0,
        "mean_tool_calls": round(sum(r.tool_calls for r in results) / n, 2) if n else 0.0,
        "results": [asdict(r) for r in results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="oracle")
    parser.add_argument("--gemini-model", default=None)
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--task", action="append", help="Run only these tasks (repeatable)")
    parser.add_argument("--out", type=Path, help="Write the JSON summary here")
    parser.add_argument("--transcripts", type=Path, help="Write one readable transcript per task into this folder")
    parser.add_argument("--min-pass-rate", type=float, default=None, help="Exit 1 if the pass rate is lower")
    args = parser.parse_args(argv)

    task_dirs = sorted(p for p in TASKS_DIR.iterdir() if (p / "task.json").exists())
    if args.task:
        task_dirs = [p for p in task_dirs if p.name in set(args.task)]

    results = []
    aborted = None
    for task_dir in task_dirs:
        try:
            r = run_task(task_dir, args.model, args.max_steps, args.gemini_model, args.transcripts)
        except Exception as exc:  # e.g. a provider's daily quota; keep what finished
            aborted = f"{task_dir.name}: {type(exc).__name__}: {str(exc)[:300]}"
            print(f"ABORTED   {aborted}")
            break
        flag = "PASS" if r.passed else ("TAMPERED" if r.tampered else "FAIL")
        print(f"{flag:9} {r.task:24} steps={r.steps:<3} tools={r.tool_calls:<3} {r.seconds:.2f}s")
        results.append(r)

    summary = summarize(args.model, results)
    summary["gemini_model"] = args.gemini_model if args.model == "gemini" else None
    summary["aborted"] = aborted
    print(
        f"\n{args.model}: {summary['passed']}/{summary['tasks']} passed "
        f"(pass rate {summary['pass_rate']:.0%}), {summary['tampered']} tampered, "
        f"mean {summary['mean_steps']} steps / {summary['mean_tool_calls']} tool calls"
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2) + "\n")
    if aborted:
        return 2
    if args.min_pass_rate is not None and summary["pass_rate"] < args.min_pass_rate:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
