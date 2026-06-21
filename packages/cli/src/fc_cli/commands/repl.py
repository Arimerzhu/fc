"""REPL mode for fc CLI.

Provides an interactive shell where commands share a persistent backend connection.
Usage: fc repl
"""

from __future__ import annotations

import logging
import shlex
from typing import Any

import click

logger = logging.getLogger(__name__)


def _get_backend():
    """获取 backend 实例（委托给 main.get_backend 统一管理）。"""
    from fc_cli.main import get_backend
    return get_backend()


@click.command(name="repl")
@click.option("--prompt", default="fc> ", help="REPL prompt string.")
@click.pass_context
def repl_command(ctx: click.Context, prompt: str) -> None:
    """Start an interactive REPL session.

    In REPL mode, all commands share a persistent backend connection,
    so multi-step workflows maintain state across commands.

    \b
    Examples:
      fc repl
      fc> document new --name Test
      fc> part add box --name Box --param Length=20
      fc> document info
      fc> exit
    """
    from fc_cli.main import _backend_type, _output, cli, _repl_mode

    # Enable REPL mode globally so _output.error does not call sys.exit
    import fc_cli.main as _main_mod
    _main_mod._repl_mode = True

    click.echo("fc REPL — Interactive FreeCAD CLI")
    click.echo("Type 'help' for commands, 'exit' or Ctrl+D to quit.")
    click.echo()

    # Create persistent backend
    backend = _get_backend()
    try:
        backend.connect()
        click.echo(f"Connected to FreeCAD ({_backend_type} backend)")
    except Exception as e:
        click.echo(f"Warning: Could not connect to FreeCAD: {e}", err=True)
        click.echo("Commands will fail until FreeCAD is available.", err=True)

    # Build command lookup from the CLI group
    commands: dict[str, click.Command] = {}
    for name, cmd in cli.commands.items():
        commands[name] = cmd
        # Also register subcommands (e.g., "document new")
        if isinstance(cmd, click.Group):
            for sub_name, sub_cmd in cmd.commands.items():
                commands[f"{name} {sub_name}"] = sub_cmd

    history: list[str] = []

    try:
        while True:
            try:
                line = click.prompt(prompt, prompt_suffix="")
            except (EOFError, KeyboardInterrupt):
                click.echo("\nExiting REPL.")
                break

            line = line.strip()
            if not line:
                continue

            # Track history
            history.append(line)

            # Handle special commands
            if line.lower() in ("exit", "quit", "q"):
                click.echo("Exiting REPL.")
                break
            elif line.lower() == "history":
                for i, h in enumerate(history, 1):
                    click.echo(f"  {i:4d}  {h}")
                continue
            elif line.lower() == "help":
                click.echo("Available commands:")
                for name in sorted(commands.keys()):
                    click.echo(f"  {name}")
                click.echo("\nSpecial commands: help, history, exit")
                continue

            # Parse and execute
            try:
                parts = shlex.split(line)
            except ValueError as e:
                _output.error(f"Parse error: {e}", repl_mode=True)
                continue

            if not parts:
                continue

            # Find the command
            cmd = None
            cmd_name = parts[0]
            args = parts[1:]

            # Try "name subcommand" first, then just "name"
            if len(parts) >= 2:
                combined = f"{parts[0]} {parts[1]}"
                if combined in commands:
                    cmd = commands[combined]
                    args = parts[2:]

            if cmd is None:
                if cmd_name in commands:
                    cmd = commands[cmd_name]
                else:
                    _output.error(f"Unknown command: {cmd_name}. Type 'help' for available commands.",
                                  repl_mode=True)
                    continue

            # Execute the command
            try:
                with cmd.make_context(cmd.name, args, parent=ctx) as sub_ctx:
                    cmd.invoke(sub_ctx)
            except SystemExit:
                pass  # Click calls sys.exit on --help
            except Exception as e:
                _output.error(f"Error: {e}", repl_mode=True)

    finally:
        _main_mod._repl_mode = False
        try:
            backend.disconnect()
        except Exception:
            pass
        click.echo("Disconnected. Goodbye!")
