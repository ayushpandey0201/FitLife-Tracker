"""Tests for the CLI adapter.

Notably a regression for A1: importing the legacy entrypoint must NOT run the
program (the original prompted for input at import time, making the whole
codebase untestable).
"""

from __future__ import annotations

import importlib
from collections.abc import Iterator

import pytest
from app import cli


def test_importing_legacy_entrypoint_does_not_run() -> None:
    """Importing must be side-effect free (no prompts)."""
    module = importlib.import_module("python_project_vs")
    assert hasattr(module, "main")


def test_cli_main_produces_a_plan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["Ayush", "28", "178", "82", "75", "m", "moderate", "nonveg", "12"])

    def fake_input(_prompt: str = "") -> str:
        return next(answers)

    monkeypatch.setattr("builtins.input", fake_input)
    cli.main()

    out = capsys.readouterr().out
    assert "FitLife plan for Ayush" in out
    assert "Daily calorie target:" in out
    assert "Suggested meals" in out


def test_cli_reprompts_on_bad_numeric_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bad input re-prompts instead of crashing (fixes A5)."""

    def feed() -> Iterator[str]:
        yield "Ayush"
        yield "not-a-number"  # bad age -> re-prompt
        yield "28"
        yield from ["178", "82", "75", "m", "moderate", "nonveg", "12"]

    answers = feed()
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    cli.main()

    out = capsys.readouterr().out
    assert "Invalid input" in out
    assert "FitLife plan for Ayush" in out
