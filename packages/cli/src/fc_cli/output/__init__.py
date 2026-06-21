"""Output formatting for CLI commands.

Supports JSON output (for AI agents) and human-readable output.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console(stderr=True)


class OutputManager:
    """Manages CLI output formatting."""

    def __init__(self, use_json: bool = False):
        self._json = use_json

    @property
    def is_json(self) -> bool:
        return self._json

    def output(self, data: Any, message: str = "") -> None:
        """Print data in the configured format."""
        if self._json:
            self._output_json(data)
        else:
            self._output_human(data, message)

    def _output_json(self, data: Any) -> None:
        """Output as JSON to stdout."""
        if isinstance(data, dict):
            print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        elif hasattr(data, "to_dict"):
            print(json.dumps(data.to_dict(), indent=2, default=str, ensure_ascii=False))
        else:
            print(json.dumps(data, indent=2, default=str, ensure_ascii=False))

    def _output_human(self, data: Any, message: str = "") -> None:
        """Output as human-readable text."""
        if message:
            console.print(f"[bold green]✓[/bold green] {message}")

        if isinstance(data, dict):
            self._output_dict(data)
        elif isinstance(data, list):
            self._output_list(data)
        elif hasattr(data, "to_dict"):
            self._output_dict(data.to_dict())

    def _output_dict(self, data: dict[str, Any], indent: int = 0) -> None:
        """Output a dict as key-value pairs."""
        for key, value in data.items():
            if isinstance(value, dict):
                console.print(f"[dim]{'  ' * indent}{key}:[/dim]")
                self._output_dict(value, indent + 1)
            elif isinstance(value, list):
                console.print(f"[dim]{'  ' * indent}{key}:[/dim]")
                self._output_list(value, indent + 1)
            else:
                console.print(f"[dim]{'  ' * indent}[/dim]{key}: {value}")

    def _output_list(self, data: list[Any], indent: int = 0) -> None:
        """Output a list."""
        prefix = "  " * indent
        for i, item in enumerate(data):
            if isinstance(item, dict):
                label = item.get("name", item.get("label", item.get("type_id", f"#{i}")))
                console.print(f"{prefix}[bold]{label}[/bold]")
                for k, v in item.items():
                    if k not in ("name", "label") and not isinstance(v, (dict, list)):
                        console.print(f"{prefix}  {k}: {v}")
            else:
                console.print(f"{prefix}• {item}")

    def error(self, message: str, code: str = "", suggestion: str = "",
              exit_code: int = 1, repl_mode: bool = False) -> None:
        """Output an error message."""
        if self._json:
            error_data = {"status": "error", "message": message}
            if code:
                error_data["code"] = code
            if suggestion:
                error_data["suggestion"] = suggestion
            print(json.dumps(error_data, indent=2, ensure_ascii=False), file=sys.stderr)
        else:
            console.print(f"[bold red]✗ Error:[/bold red] {message}")
            if suggestion:
                console.print(f"[dim]  Suggestion: {suggestion}[/dim]")

        if not repl_mode:
            sys.exit(exit_code)

    def table(self, title: str, columns: list[str],
              rows: list[list[Any]]) -> None:
        """Output data as a rich table."""
        if self._json:
            data = [dict(zip(columns, row)) for row in rows]
            print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        else:
            t = Table(title=title, show_header=True, header_style="bold")
            for col in columns:
                t.add_column(str(col))
            for row in rows:
                t.add_row(*[str(c) for c in row])
            console.print(t)

    def success(self, message: str) -> None:
        """Output a success message."""
        if self._json:
            print(json.dumps({"status": "ok", "message": message}))
        else:
            console.print(f"[bold green]✓[/bold green] {message}")
