"""Tests for `lattice setup-claude-skill` command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from lattice.cli.main import cli


def test_installs_skill_to_claude_skills_dir(tmp_path: Path) -> None:
    """Copies bundled skill to ~/.claude/skills/lattice/."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch.object(Path, "home", return_value=fake_home):
        runner = CliRunner()
        result = runner.invoke(cli, ["setup-claude-skill"])

    assert result.exit_code == 0, result.output
    dest = fake_home / ".claude" / "skills" / "lattice"
    assert dest.is_dir()
    assert (dest / "SKILL.md").exists()


def test_refuses_overwrite_without_force(tmp_path: Path) -> None:
    """Refuses to overwrite if skill already exists."""
    fake_home = tmp_path / "home"
    dest = fake_home / ".claude" / "skills" / "lattice"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("existing")

    with patch.object(Path, "home", return_value=fake_home):
        runner = CliRunner()
        result = runner.invoke(cli, ["setup-claude-skill"])

    assert result.exit_code == 0
    assert "Use --force" in result.output
    # Original file should be untouched
    assert (dest / "SKILL.md").read_text() == "existing"


def test_force_overwrites_existing(tmp_path: Path) -> None:
    """--force replaces existing skill directory."""
    fake_home = tmp_path / "home"
    dest = fake_home / ".claude" / "skills" / "lattice"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("old content")

    with patch.object(Path, "home", return_value=fake_home):
        runner = CliRunner()
        result = runner.invoke(cli, ["setup-claude-skill", "--force"])

    assert result.exit_code == 0, result.output
    # Should have the bundled content, not "old content"
    assert (dest / "SKILL.md").exists()
    assert (dest / "SKILL.md").read_text() != "old content"


def test_excludes_python_artifacts(tmp_path: Path) -> None:
    """Should not copy __init__.py or __pycache__."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch.object(Path, "home", return_value=fake_home):
        runner = CliRunner()
        result = runner.invoke(cli, ["setup-claude-skill"])

    assert result.exit_code == 0, result.output
    dest = fake_home / ".claude" / "skills" / "lattice"
    assert not (dest / "__init__.py").exists()
    assert not (dest / "__pycache__").exists()


def test_check_script_is_executable(tmp_path: Path) -> None:
    """scripts/lattice-check.sh should be executable after install."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with patch.object(Path, "home", return_value=fake_home):
        runner = CliRunner()
        result = runner.invoke(cli, ["setup-claude-skill"])

    assert result.exit_code == 0, result.output
    check_script = fake_home / ".claude" / "skills" / "lattice" / "scripts" / "lattice-check.sh"
    if check_script.exists():
        assert check_script.stat().st_mode & 0o111  # any execute bit set
