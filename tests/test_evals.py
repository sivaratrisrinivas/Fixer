import json

from evals import run as eval_run


def test_oracle_passes_and_baselines_fail(tmp_path):
    out = tmp_path / "oracle.json"
    assert (
        eval_run.main(
            [
                "--model",
                "oracle",
                "--task",
                "slugify_case",
                "--task",
                "safe_div_zero",
                "--out",
                str(out),
                "--min-pass-rate",
                "1.0",
            ]
        )
        == 0
    )
    summary = json.loads(out.read_text())
    assert summary["passed"] == 2 and summary["tampered"] == 0

    assert eval_run.main(["--model", "noop", "--task", "slugify_case", "--min-pass-rate", "0.5"]) == 1


def test_editing_tests_is_caught():
    result = eval_run.run_task(eval_run.TASKS_DIR / "mutable_default", "tamper", 5, None)
    assert result.tampered and not result.passed
    assert result.files_changed == ["test_tags.py"]


def test_every_task_is_actually_broken_and_actually_fixable():
    for task_dir in sorted(p for p in eval_run.TASKS_DIR.iterdir() if (p / "task.json").exists()):
        broken = eval_run.run_task(task_dir, "noop", 5, None)
        fixed = eval_run.run_task(task_dir, "oracle", 10, None)
        assert not broken.passed, task_dir.name
        assert fixed.passed, task_dir.name
