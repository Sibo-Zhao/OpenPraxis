"""CLI 命令解析与输出测试。"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from openpraxis.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "add" in result.output
    assert "list" in result.output


def test_add_help() -> None:
    result = runner.invoke(app, ["add", "--help"])
    assert result.exit_code == 0
    assert "file" in result.output or "FILE" in result.output


def test_list_help() -> None:
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
