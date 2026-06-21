"""SVG rendering and visual quality check module.

Renders engineering drawing SVG to PNG and performs quality checks.
Uses matplotlib as the rendering backend (pure Python, no extra deps).

Usage:
    from fc_core.io.svg_renderer import render_svg, check_drawing_quality
    png_bytes = render_svg(svg_content)
    report = check_drawing_quality(svg_content)
"""

from __future__ import annotations

import io
import os
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VisualCheckResult:
    """Single visual check result."""
    check_name: str
    passed: bool
    detail: str = ""
    suggestion: str = ""


@dataclass
class DrawingQualityReport:
    """Drawing quality report."""
    checks: list[VisualCheckResult] = field(default_factory=list)
    screenshot_path: str = ""
    render_time_sec: float = 0.0
    passed: bool = True
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "render_time_sec": round(self.render_time_sec, 2),
            "screenshot_path": self.screenshot_path,
            "checks": [
                {
                    "check_name": c.check_name,
                    "passed": c.passed,
                    "detail": c.detail,
                    "suggestion": c.suggestion,
                }
                for c in self.checks
            ],
        }


def _parse_svg_paths(svg_content: str) -> dict[str, list]:
    """Parse path data from SVG content, grouped by line type.

    Returns:
        Dict {line_type: [(x1,y1,x2,y2), ...]}
    """
    paths: dict[str, list] = {
        "visible": [],
        "hidden": [],
        "center": [],
        "phantom": [],
    }

    path_pattern = re.compile(
        r'<path[^>]*d="([^"]+)"[^>]*(?:stroke-dasharray="([^"]*)")?[^>]*/?>'
    )
    for match in path_pattern.finditer(svg_content):
        d_attr = match.group(1)
        dash_attr = match.group(2)
        points = _parse_path_d(d_attr)
        if not points:
            continue

        if dash_attr and "12," in dash_attr:
            line_type = "center"
        elif dash_attr and "4," in dash_attr:
            line_type = "hidden"
        elif dash_attr and "15," in dash_attr:
            line_type = "phantom"
        else:
            line_type = "visible"

        paths[line_type].extend(points)

    return paths


def _parse_path_d(d_attr: str) -> list[tuple]:
    """Parse SVG path d attribute, extract line segment endpoints.

    Supports M (move to) and L (line to) commands.
    Handles both separated (M x y) and concatenated (Mx,y) formats.
    """
    import re

    segments = []
    # Normalize: ensure space between command letters and numbers
    # e.g. "M-57.084,20.410" -> "M -57.084 20.410"
    normalized = re.sub(r'([MLml])', r'\1 ', d_attr)
    normalized = normalized.replace(',', ' ')
    parts = normalized.split()

    i = 0
    cx, cy = 0.0, 0.0

    while i < len(parts):
        cmd = parts[i]
        if cmd in ("M", "m") and i + 2 < len(parts):
            try:
                nx = float(parts[i + 1])
                ny = float(parts[i + 2])
            except ValueError:
                i += 1
                continue
            if cmd == "M":
                cx, cy = nx, ny
            else:
                cx, cy = cx + nx, cy + ny
            i += 3
        elif cmd in ("L", "l") and i + 2 < len(parts):
            try:
                nx = float(parts[i + 1])
                ny = float(parts[i + 2])
            except ValueError:
                i += 1
                continue
            if cmd == "l":
                nx, ny = cx + nx, cy + ny
            segments.append((cx, cy, nx, ny))
            cx, cy = nx, ny
            i += 3
        else:
            i += 1

    return segments


def render_svg(
    svg_content: str,
    output_path: str | None = None,
    dpi: int = 150,
    background: str = "white",
) -> bytes:
    """Render SVG content to PNG using matplotlib.

    Args:
        svg_content: SVG XML string.
        output_path: Optional PNG output path.
        dpi: Render DPI.
        background: Background color.

    Returns:
        PNG image bytes.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    t0 = time.time()
    paths = _parse_svg_paths(svg_content)

    fig, ax = plt.subplots(1, 1, figsize=(11.89, 8.41), dpi=dpi)
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)

    style_config = {
        "center": {"color": "black", "linewidth": 0.5, "linestyle": (0, (12, 2, 3, 2)), "alpha": 0.6},
        "hidden": {"color": "black", "linewidth": 0.7, "linestyle": (0, (4, 2)), "alpha": 0.6},
        "visible": {"color": "black", "linewidth": 1.0, "linestyle": "-", "alpha": 1.0},
        "phantom": {"color": "black", "linewidth": 0.5, "linestyle": (0, (15, 2, 3, 2, 3, 2)), "alpha": 0.4},
    }

    total_lines = 0
    for line_type, segments in paths.items():
        if not segments:
            continue
        style = style_config.get(line_type, style_config["visible"])
        # LineCollection expects [(x1,y1),(x2,y2)] format
        lc_segments = [((x1, y1), (x2, y2)) for x1, y1, x2, y2 in segments]
        lc = LineCollection(
            lc_segments,
            colors=style["color"],
            linewidths=style["linewidth"],
            linestyle=style["linestyle"],
            alpha=style["alpha"],
        )
        ax.add_collection(lc)
        total_lines += len(segments)

    if total_lines > 0:
        ax.autoscale()
        ax.set_aspect("equal")
    else:
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)

    ax.axis("off")
    fig.tight_layout(pad=0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=background, edgecolor="none")
    plt.close(fig)

    png_bytes = buf.getvalue()
    elapsed = time.time() - t0
    logger.info("SVG rendered in %.1fs (%d bytes PNG, %d lines)", elapsed, len(png_bytes), total_lines)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        logger.info("PNG saved: %s", output_path)

    return png_bytes


def check_drawing_quality(
    svg_content: str,
    view_name: str = "assembly",
    screenshot_path: str | None = None,
    dpi: int = 100,
) -> DrawingQualityReport:
    """Check engineering drawing render quality.

    Auto-checks:
    1. SVG content validity
    2. SVG structure (path count, group count)
    3. Successful PNG rendering
    4. Non-empty output
    5. Path density check

    Args:
        svg_content: SVG XML string.
        view_name: View name for report.
        screenshot_path: Optional screenshot save path.
        dpi: Render DPI.

    Returns:
        DrawingQualityReport with all check results.
    """
    report = DrawingQualityReport()
    t0 = time.time()

    # 1. Basic SVG check
    if not svg_content or len(svg_content) < 100:
        report.checks.append(VisualCheckResult(
            check_name="svg_content_valid",
            passed=False,
            detail="SVG content is empty or too short",
            suggestion="Check SVG generation logic",
        ))
        report.passed = False
        report.summary = "Invalid SVG content"
        return report

    report.checks.append(VisualCheckResult(
        check_name="svg_content_valid",
        passed=True,
        detail=f"SVG content length: {len(svg_content):,} bytes",
    ))

    # 2. SVG structure check
    path_count = len(re.findall(r"<path", svg_content))
    g_count = len(re.findall(r"<g ", svg_content))
    text_count = len(re.findall(r"<text", svg_content))

    report.checks.append(VisualCheckResult(
        check_name="svg_structure",
        passed=True,
        detail=f"Paths: {path_count}, Groups: {g_count}, Texts: {text_count}",
    ))

    if path_count > 1000:
        report.checks.append(VisualCheckResult(
            check_name="path_count_warning",
            passed=False,
            detail=f"Too many path elements: {path_count}, consider path merging",
            suggestion="Use AssemblyDrawing path merging optimization",
        ))

    # 3. Render test
    try:
        png_bytes = render_svg(svg_content, output_path=screenshot_path, dpi=dpi)
        render_time = time.time() - t0
        report.render_time_sec = render_time

        if not png_bytes or len(png_bytes) < 1000:
            report.checks.append(VisualCheckResult(
                check_name="render_output",
                passed=False,
                detail="Render output is empty",
                suggestion="Check if SVG content is valid",
            ))
            report.passed = False
        else:
            report.checks.append(VisualCheckResult(
                check_name="render_output",
                passed=True,
                detail=f"Render OK: {len(png_bytes):,} bytes, {render_time:.1f}s",
            ))

            if len(png_bytes) < 5000:
                report.checks.append(VisualCheckResult(
                    check_name="content_density",
                    passed=False,
                    detail=f"PNG too small ({len(png_bytes):,} bytes), may lack content",
                    suggestion="Check if views have actual edge data",
                ))
            else:
                report.checks.append(VisualCheckResult(
                    check_name="content_density",
                    passed=True,
                    detail=f"PNG size OK: {len(png_bytes):,} bytes",
                ))

            paths = _parse_svg_paths(svg_content)
            total_segments = sum(len(s) for s in paths.values())
            if total_segments == 0:
                report.checks.append(VisualCheckResult(
                    check_name="path_data",
                    passed=False,
                    detail="No path segments parsed",
                    suggestion="Check SVG path data format",
                ))
            else:
                detail = f"Total segments: {total_segments}"
                for lt, segs in paths.items():
                    if segs:
                        detail += f", {lt}: {len(segs)}"
                report.checks.append(VisualCheckResult(
                    check_name="path_data",
                    passed=True,
                    detail=detail,
                ))

    except Exception as e:
        report.checks.append(VisualCheckResult(
            check_name="render_test",
            passed=False,
            detail=f"Render failed: {e}",
            suggestion="Check SVG for unsupported features",
        ))
        report.passed = False

    failed = [c for c in report.checks if not c.passed]
    if failed:
        report.passed = False
        report.summary = f"{len(failed)} check(s) failed: {', '.join(c.check_name for c in failed)}"
    else:
        report.passed = True
        report.summary = f"All {len(report.checks)} checks passed"

    return report
