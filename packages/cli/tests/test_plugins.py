"""Tests for fc CLI plugin system.

Covers:
- get_plugin_dirs() returns valid directories
- discover_plugins() finds .py files
- load_plugin() loads and returns commands
- load_all_plugins() registers into Click group
- Full flow with temp plugin directory
- Plugin load failure does not crash
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import click
import pytest

from fc_cli.plugins import (
    discover_plugins,
    fc_command,
    get_plugin_dirs,
    load_all_plugins,
    load_plugin,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_plugin_dir(tmp_path):
    """Create a temporary plugin directory with a valid plugin."""
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()

    # Valid plugin with fc_commands
    valid_plugin = plugin_dir / "valid_plugin.py"
    valid_plugin.write_text(
        "import click\n"
        "@click.command()\n"
        "def hello(name: str = 'World'):\n"
        "    click.echo(f'Hello {name}')\n"
        "fc_commands = [hello]\n"
    )

    # Plugin with syntax error
    bad_plugin = plugin_dir / "bad_plugin.py"
    bad_plugin.write_text("this is not valid python!!!\n")

    # Plugin with fc_plugin group
    group_plugin = plugin_dir / "group_plugin.py"
    group_plugin.write_text(
        "import click\n"
        "@click.group()\n"
        "def fc_plugin():\n"
        "    pass\n"
        "@fc_plugin.command()\n"
        "def sub():\n"
        "    click.echo('sub')\n"
    )

    # Non-plugin file (starts with _)
    private_file = plugin_dir / "_private.py"
    private_file.write_text("# private\n")

    return plugin_dir


@pytest.fixture
def cli_group():
    """Create a fresh Click group for testing."""
    from fc_cli.plugins import _loaded_plugins
    _loaded_plugins.clear()

    @click.group()
    def test_cli():
        pass
    return test_cli


# ---------------------------------------------------------------------------
# get_plugin_dirs
# ---------------------------------------------------------------------------


class TestGetPluginDirs:
    def test_returns_list(self):
        dirs = get_plugin_dirs()
        assert isinstance(dirs, list)

    def test_env_var_override(self, tmp_path):
        plugin_dir = tmp_path / "my_plugins"
        plugin_dir.mkdir()
        with patch.dict(os.environ, {"FC_PLUGIN_DIR": str(plugin_dir)}):
            dirs = get_plugin_dirs()
        assert plugin_dir in dirs

    def test_env_var_missing_dir_ignored(self, tmp_path):
        bad_path = str(tmp_path / "nonexistent")
        with patch.dict(os.environ, {"FC_PLUGIN_DIR": bad_path}):
            dirs = get_plugin_dirs()
        assert bad_path not in [str(d) for d in dirs]

    def test_skips_nonexistent_default_dirs(self):
        """Default dirs that don't exist should be filtered out."""
        dirs = get_plugin_dirs()
        for d in dirs:
            assert d.exists()


# ---------------------------------------------------------------------------
# discover_plugins
# ---------------------------------------------------------------------------


class TestDiscoverPlugins:
    def test_finds_py_files(self, tmp_plugin_dir):
        with patch.dict(os.environ, {"FC_PLUGIN_DIR": str(tmp_plugin_dir)}):
            plugins = discover_plugins()
        names = [p.stem for p in plugins]
        assert "valid_plugin" in names
        assert "bad_plugin" in names
        assert "group_plugin" in names

    def test_skips_private_files(self, tmp_plugin_dir):
        with patch.dict(os.environ, {"FC_PLUGIN_DIR": str(tmp_plugin_dir)}):
            plugins = discover_plugins()
        names = [p.stem for p in plugins]
        assert "_private" not in names

    def test_empty_dir(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with patch.dict(os.environ, {"FC_PLUGIN_DIR": str(empty_dir)}):
            plugins = discover_plugins()
        assert plugins == []


# ---------------------------------------------------------------------------
# load_plugin
# ---------------------------------------------------------------------------


class TestLoadPlugin:
    def test_loads_fc_commands(self, tmp_plugin_dir, cli_group):
        plugin_path = tmp_plugin_dir / "valid_plugin.py"
        commands = load_plugin(plugin_path)
        assert len(commands) == 1
        assert isinstance(commands[0], click.Command)
        assert commands[0].name == "hello"

    def test_loads_fc_plugin_group(self, tmp_plugin_dir):
        plugin_path = tmp_plugin_dir / "group_plugin.py"
        commands = load_plugin(plugin_path)
        assert len(commands) >= 1

    def test_syntax_error_returns_empty(self, tmp_plugin_dir):
        plugin_path = tmp_plugin_dir / "bad_plugin.py"
        commands = load_plugin(plugin_path)
        assert commands == []

    def test_skips_already_loaded(self, tmp_plugin_dir):
        plugin_path = tmp_plugin_dir / "valid_plugin.py"
        load_plugin(plugin_path)
        # Second load should return empty (already loaded)
        commands = load_plugin(plugin_path)
        assert commands == []


# ---------------------------------------------------------------------------
# load_all_plugins
# ---------------------------------------------------------------------------


class TestLoadAllPlugins:
    def test_registers_commands(self, tmp_plugin_dir, cli_group):
        with patch.dict(os.environ, {"FC_PLUGIN_DIR": str(tmp_plugin_dir)}):
            count = load_all_plugins(cli_group)
        assert count >= 1

    def test_bad_plugin_does_not_crash(self, tmp_plugin_dir, cli_group):
        """A bad plugin should not prevent loading other plugins."""
        with patch.dict(os.environ, {"FC_PLUGIN_DIR": str(tmp_plugin_dir)}):
            count = load_all_plugins(cli_group)
        # Should still load valid plugins despite bad_plugin.py
        assert count >= 1

    def test_no_plugins_dir(self, tmp_path, cli_group):
        empty_dir = tmp_path / "no_plugins"
        empty_dir.mkdir()
        with patch.dict(os.environ, {"FC_PLUGIN_DIR": str(empty_dir)}):
            count = load_all_plugins(cli_group)
        assert count == 0


# ---------------------------------------------------------------------------
# fc_command decorator
# ---------------------------------------------------------------------------


class TestFcCommandDecorator:
    def test_decorator_creates_command(self):
        @fc_command(name="test-cmd")
        def my_func():
            pass
        # The decorator should not crash
        assert callable(my_func)

    def test_decorator_default_name(self):
        @fc_command()
        def my_tool():
            pass
        assert callable(my_tool)
