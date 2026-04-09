from __future__ import annotations

from run_experiments import _sanitize_cli_argv, parse_args


def test_sanitize_cli_argv_removes_bash_line_continuation_tokens() -> None:
    raw = ["--n", "100", "\\", "--max-steps", "500", "\\n", "--seed", "42"]
    assert _sanitize_cli_argv(raw) == ["--n", "100", "--max-steps", "500", "--seed", "42"]


def test_parse_args_accepts_sanitized_copy_paste_command() -> None:
    args = parse_args(["\\", "--n", "100", "\\", "--max-steps", "500", "--seed", "123"])
    assert args.n == 100
    assert args.max_steps == 500
    assert args.seed == 123
