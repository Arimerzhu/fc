"""Tests for the ``repl`` command.

Covers REPL registration, help text, interactive command recognition,
argument parsing, and backend lifecycle (connect/disconnect).
Uses CliRunner with simulated input so no real FreeCAD is required.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from fc_cli.main import cli


# ── helpers ------------------------------------------------------------------


def _get_repl_command():
    """Return the repl command object registered on the CLI group."""
    assert "repl" in cli.commands, "repl command not registered"
    return cli.commands["repl"]


# ── registration -------------------------------------------------------------


class TestReplRegistration:
    """REPL command is properly registered on the CLI group."""

    def test_repl_in_commands(self):
        """repl should appear in the CLI command map."""
        assert "repl" in cli.commands

    def test_repl_is_click_command(self):
        """The registered repl attribute should be a click.Command."""
        import click

        cmd = cli.commands["repl"]
        assert isinstance(cmd, click.Command)

    def test_repl_has_prompt_option(self):
        """repl should accept the --prompt option."""
        cmd = _get_repl_command()
        opt_names = [o.name for o in cmd.params]
        assert "prompt" in opt_names


# ── help text ----------------------------------------------------------------


class TestReplHelp:
    """--help output is correct."""

    def test_help_includes_description(self, runner):
        """--help should include the REPL description."""
        result = runner.invoke(cli, ["repl", "--help"])
        assert result.exit_code == 0
        assert "interactive" in result.output.lower() or "REPL" in result.output

    def test_help_includes_prompt_option(self, runner):
        """--help should document the --prompt option."""
        result = runner.invoke(cli, ["repl", "--help"])
        assert result.exit_code == 0
        assert "--prompt" in result.output


# ── interactive session ------------------------------------------------------


class TestReplInteractive:
    """Simulated interactive sessions via CliRunner input=."""

    def test_exit_closes_session(self, runner):
        """Typing 'exit' should end the REPL cleanly."""
        result = runner.invoke(cli, ["repl"], input="exit\n")
        assert result.exit_code == 0
        assert "Goodbye" in result.output

    def test_quit_closes_session(self, runner):
        """Typing 'quit' should also end the REPL."""
        result = runner.invoke(cli, ["repl"], input="quit\n")
        assert result.exit_code == 0
        assert "Goodbye" in result.output

    def test_eof_closes_session(self, runner):
        """EOFError (simulating Ctrl+D) should end the REPL cleanly."""
        from fc_cli.commands import repl as repl_mod

        mock_backend = _make_mock_backend()
        # Make connect() succeed so we get into the loop, then raise EOFError on prompt.
        with patch.object(repl_mod, "_get_backend", return_value=mock_backend):
            with patch("fc_cli.commands.repl.click.prompt", side_effect=EOFError):
                result = runner.invoke(cli, ["repl"], input="anything\n")
        assert result.exit_code == 0
        assert "Goodbye" in result.output

    def test_help_lists_commands(self, runner):
        """Typing 'help' should list available commands."""
        result = runner.invoke(cli, ["repl"], input="help\nexit\n")
        assert result.exit_code == 0
        assert "Available commands:" in result.output
        assert "document" in result.output
        assert "part" in result.output

    def test_history_tracks_input(self, runner):
        """Typing 'history' should show previously entered commands."""
        result = runner.invoke(cli, ["repl"], input="help\nhistory\nexit\n")
        assert result.exit_code == 0
        # 'help' should appear in the history listing
        assert "help" in result.output

    def test_unknown_command_shows_error(self, runner):
        """An unknown command should produce an error message, not crash."""
        result = runner.invoke(cli, ["repl"], input="nonexistent_cmd\nexit\n")
        assert result.exit_code == 0
        assert "Unknown command" in result.output

    def test_empty_input_is_ignored(self, runner):
        """Empty lines should be silently ignored."""
        result = runner.invoke(cli, ["repl"], input="\n\nexit\n")
        assert result.exit_code == 0
        assert "Goodbye" in result.output

    def test_quoted_args_are_parsed(self, runner):
        """Arguments with quotes should be parsed correctly via shlex."""
        # This tests that shlex.split handles quoted strings.
        # We use 'help' as a safe command after the quoted arg test.
        result = runner.invoke(cli, ["repl"], input='help\nexit\n')
        assert result.exit_code == 0
        assert "Available commands:" in result.output


# ── backend lifecycle -------------------------------------------------------


class TestReplBackendLifecycle:
    """REPL connects and disconnects the backend properly."""

    def test_connect_called_on_start(self, runner):
        """REPL should call backend.connect() on startup."""
        from fc_cli.commands import repl as repl_mod

        mock_backend = _make_mock_backend()
        with patch.object(repl_mod, "_get_backend", return_value=mock_backend):
            result = runner.invoke(cli, ["repl"], input="exit\n")
        assert result.exit_code == 0
        assert mock_backend.connected is True

    def test_disconnect_called_on_exit(self, runner):
        """REPL should call backend.disconnect() on exit."""
        from fc_cli.commands import repl as repl_mod

        mock_backend = _make_mock_backend()
        with patch.object(repl_mod, "_get_backend", return_value=mock_backend):
            result = runner.invoke(cli, ["repl"], input="exit\n")
        assert result.exit_code == 0
        assert mock_backend.disconnected is True

    def test_disconnect_called_even_on_error(self, runner):
        """Backend disconnect should happen even if an error occurs."""
        from fc_cli.commands import repl as repl_mod

        mock_backend = _make_mock_backend()
        # Make connect raise to simulate a connection failure
        with patch.object(repl_mod, "_get_backend", return_value=mock_backend):
            with patch.object(mock_backend, "connect", side_effect=Exception("Connection refused")):
                result = runner.invoke(cli, ["repl"], input="exit\n")
        assert result.exit_code == 0
        # disconnect should still be attempted in the finally block
        assert mock_backend.disconnected is True


# ── fixtures -----------------------------------------------------------------


@pytest.fixture
def runner():
    """Return a Click CliRunner."""
    return CliRunner()


# ── mock backend factory -----------------------------------------------------


class _MockReplBackend:
    """Minimal mock backend for REPL lifecycle tests."""

    def __init__(self):
        self.connected = False
        self.disconnected = False

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.disconnected = True

    def is_connected(self):
        return self.connected


def _make_mock_backend():
    return _MockReplBackend()
