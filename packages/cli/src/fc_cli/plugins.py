"""Plugin loader for fc CLI.

Plugins are Python files placed in ~/.fc/plugins/ (or FC_PLUGIN_DIR env var).
Each plugin file can define Click commands or command groups that get
automatically registered into the fc CLI.

Plugin API:
- Each plugin module can define `fc_commands` (list of Click commands/groups)
- Or define a Click group named `fc_plugin` that gets added as a subcommand
- Or define functions decorated with `@fc_command()` to register individual commands
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)

# Default plugin directories
DEFAULT_PLUGIN_DIRS = [
    Path.home() / ".fc" / "plugins",
    Path("/usr/local/share/fc/plugins"),
]

# Global registry of loaded plugins
_loaded_plugins: dict[str, Any] = {}


def get_plugin_dirs() -> list[Path]:
    """Get all plugin search directories.

    Returns:
        List of Path objects for plugin directories.
    """
    dirs: list[Path] = []
    # Environment variable override
    env_dir = os.environ.get("FC_PLUGIN_DIR")
    if env_dir:
        dirs.append(Path(env_dir))
    # Default dirs
    dirs.extend(DEFAULT_PLUGIN_DIRS)
    return [d for d in dirs if d.exists() and d.is_dir()]


def discover_plugins() -> list[Path]:
    """Discover all plugin files in plugin directories.

    Returns:
        List of Path objects for .py plugin files.
    """
    plugins: list[Path] = []
    for plugin_dir in get_plugin_dirs():
        for f in sorted(plugin_dir.glob("*.py")):
            if not f.name.startswith("_"):
                plugins.append(f)
    return plugins


def load_plugin(plugin_path: Path) -> list[click.Command | click.Group]:
    """Load a single plugin file and return its commands.

    Args:
        plugin_path: Path to the .py plugin file.

    Returns:
        List of Click Command/Group objects to register.
    """
    name = plugin_path.stem
    if name in _loaded_plugins:
        logger.debug(f"Plugin '{name}' already loaded, skipping")
        return []

    try:
        spec = importlib.util.spec_from_file_location(f"fc_plugin_{name}", plugin_path)
        if spec is None or spec.loader is None:
            logger.warning(f"Cannot load plugin spec: {plugin_path}")
            return []
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _loaded_plugins[name] = module
    except Exception as e:
        logger.error(f"Failed to load plugin '{name}': {e}")
        return []

    commands: list[click.Command | click.Group] = []

    # Pattern 1: fc_commands list
    if hasattr(module, "fc_commands"):
        for cmd in module.fc_commands:
            if isinstance(cmd, (click.Command, click.Group)):
                commands.append(cmd)

    # Pattern 2: fc_plugin Click group
    if hasattr(module, "fc_plugin") and isinstance(module.fc_plugin, (click.Command, click.Group)):
        commands.append(module.fc_plugin)

    # Pattern 3: @fc_command decorator results
    if hasattr(module, "_fc_command_registry"):
        commands.extend(module._fc_command_registry)

    logger.info(f"Loaded plugin '{name}': {len(commands)} command(s)")
    return commands


def load_all_plugins(cli_group: click.Group) -> int:
    """Discover and load all plugins, registering them into the CLI.

    Args:
        cli_group: The Click group to register plugin commands into.

    Returns:
        Number of plugins loaded.
    """
    count = 0
    for plugin_path in discover_plugins():
        commands = load_plugin(plugin_path)
        for cmd in commands:
            cli_group.add_command(cmd)
        if commands:
            count += 1
    return count


def fc_command(name: str | None = None, **kwargs):
    """Decorator to register a function as an fc CLI command.

    Usage:
        @fc_command()
        def my_tool(param: str):
            '''My custom tool.'''
            click.echo(f"Hello {param}")
    """
    def decorator(f):
        cmd_name = name or f.__name__.replace("_", "-")

        @click.command(name=cmd_name, **kwargs)
        @click.argument("args", nargs=-1, required=False)
        def wrapper(args):
            f(*args) if args else f()

        # Register in module-level registry
        caller_module = inspect.getmodule(inspect.stack()[1][0])
        if caller_module is not None:
            if not hasattr(caller_module, "_fc_command_registry"):
                caller_module._fc_command_registry = []
            caller_module._fc_command_registry.append(wrapper)
        return f
    return decorator
