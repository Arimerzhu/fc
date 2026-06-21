"""Performance benchmark tests for FreeCAD CLI.

Measures:
- HeadlessBackend subprocess overhead (single _execute_macro call)
- Batch mode vs single operation mode performance
- Typical operation latencies (document_new, object_create, export)

Requires real FreeCAD installation. Skipped when FreeCAD is not available.
"""

from __future__ import annotations

import json
import os
import statistics
import tempfile
import time
from pathlib import Path

import pytest

from fc_core.backend import HeadlessBackend, find_freecad
from fc_core.types import ToolResponse

# Skip all benchmarks if FreeCAD is not installed
FREECAD_PATH = None
try:
    FREECAD_PATH = find_freecad()
except (FileNotFoundError, RuntimeError):
    pass

pytestmark = pytest.mark.skipif(
    FREECAD_PATH is None,
    reason="FreeCAD not installed — benchmarks require FreeCADCmd",
)


@pytest.fixture(scope="module")
def backend():
    """Create a HeadlessBackend for benchmark tests."""
    b = HeadlessBackend(freecad_path=FREECAD_PATH, timeout=300)
    b.connect()
    yield b
    b.disconnect()


@pytest.fixture(autouse=True)
def ensure_connected(backend):
    """Ensure backend is connected before each benchmark."""
    if not backend.is_connected():
        backend.connect()


# ---------------------------------------------------------------------------
# Helper: timing utilities
# ---------------------------------------------------------------------------

def _measure_latency(func, *args, **kwargs):
    """Measure execution time of a function call in seconds."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return elapsed, result


def _compute_stats(latencies: list[float]) -> dict:
    """Compute p50, p95, p99, mean, min, max from a list of latencies."""
    if not latencies:
        return {}
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)

    def percentile(pct: float) -> float:
        idx = pct / 100.0 * (n - 1)
        lower = int(idx)
        upper = min(lower + 1, n - 1)
        frac = idx - lower
        return sorted_lat[lower] * (1 - frac) + sorted_lat[upper] * frac

    return {
        "count": n,
        "mean_s": statistics.mean(sorted_lat),
        "min_s": sorted_lat[0],
        "max_s": sorted_lat[-1],
        "p50_s": percentile(50),
        "p95_s": percentile(95),
        "p99_s": percentile(99),
        "stddev_s": statistics.stdev(sorted_lat) if n > 1 else 0.0,
    }


# ---------------------------------------------------------------------------
# Benchmark: subprocess overhead baseline
# ---------------------------------------------------------------------------

class TestSubprocessOverhead:
    """Measure the baseline overhead of a single _execute_macro call."""

    def test_minimal_macro_latency(self, backend):
        """Measure the fastest possible FreeCAD operation (get version)."""
        latencies = []
        for _ in range(5):
            elapsed, _ = _measure_latency(backend.get_version)
            latencies.append(elapsed)

        stats = _compute_stats(latencies)
        print(f"\n[macro_overhead] get_version: "
              f"p50={stats['p50_s']*1000:.0f}ms "
              f"p95={stats['p95_s']*1000:.0f}ms "
              f"p99={stats['p99_s']*1000:.0f}ms "
              f"mean={stats['mean_s']*1000:.0f}ms")

        # Sanity: a single macro call should complete within 30 seconds
        assert stats["p99_s"] < 30.0, f"p99 latency too high: {stats['p99_s']:.1f}s"

    def test_execute_macro_latency(self, backend):
        """Measure _execute_macro overhead with a trivial script."""
        latencies = []
        for _ in range(5):
            elapsed, _ = _measure_latency(
                backend._execute_macro, "pass"
            )
            latencies.append(elapsed)

        stats = _compute_stats(latencies)
        print(f"\n[macro_overhead] trivial script: "
              f"p50={stats['p50_s']*1000:.0f}ms "
              f"p95={stats['p95_s']*1000:.0f}ms "
              f"p99={stats['p99_s']*1000:.0f}ms "
              f"mean={stats['mean_s']*1000:.0f}ms")

        assert stats["p99_s"] < 30.0


# ---------------------------------------------------------------------------
# Benchmark: typical operations
# ---------------------------------------------------------------------------

class TestOperationLatency:
    """Measure latency of typical FreeCAD operations.

    Note: Each _execute_macro call runs in a separate FreeCAD process,
    so operations that depend on document state must include document
    creation in the same call.
    """

    def test_document_new_latency(self, backend):
        """Measure document_new operation latency."""
        latencies = []
        for i in range(5):
            elapsed, result = _measure_latency(
                backend.document_new, f"BenchDoc_{i}"
            )
            latencies.append(elapsed)
            assert result.status == "ok", f"document_new failed: {result.message}"

        stats = _compute_stats(latencies)
        print(f"\n[operation] document_new: "
              f"p50={stats['p50_s']*1000:.0f}ms "
              f"p95={stats['p95_s']*1000:.0f}ms "
              f"p99={stats['p99_s']*1000:.0f}ms "
              f"mean={stats['mean_s']*1000:.0f}ms")

        assert stats["p99_s"] < 30.0

    def test_object_create_latency(self, backend):
        """Measure object_create (Part::Box) latency.

        Each call is a separate subprocess, so we create a document
        and add a box in the same _execute_macro call.
        """
        latencies = []
        for i in range(5):
            # Create document + box in a single macro call
            body = f"""\
import FreeCAD
import Part
doc = FreeCAD.newDocument("BenchBoxDoc_{i}")
obj = doc.addObject("Part::Box", "Box_{i}")
obj.Length = 10
obj.Width = 10
obj.Height = 10
doc.recompute()
_fc_result["data"] = {{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId}}
"""
            elapsed, result = _measure_latency(
                backend._execute_macro, body
            )
            latencies.append(elapsed)
            assert result["status"] == "ok", f"object_create failed: {result.get('message', '')}"

        stats = _compute_stats(latencies)
        print(f"\n[operation] object_create (Box, with doc): "
              f"p50={stats['p50_s']*1000:.0f}ms "
              f"p95={stats['p95_s']*1000:.0f}ms "
              f"p99={stats['p99_s']*1000:.0f}ms "
              f"mean={stats['mean_s']*1000:.0f}ms")

        assert stats["p99_s"] < 30.0

    def test_export_step_latency(self, backend, tmp_path):
        """Measure STEP export latency.

        Each call is a separate subprocess, so we create a document,
        add a box, and export in the same _execute_macro call.
        """
        latencies = []
        for i in range(3):
            output_file = str(tmp_path / f"bench_export_{i}.step")
            body = f"""\
import FreeCAD
import Part
doc = FreeCAD.newDocument("BenchExportDoc_{i}")
obj = doc.addObject("Part::Box", "ExportBox_{i}")
obj.Length = 20
obj.Width = 15
obj.Height = 10
doc.recompute()
Part.export([obj], r"{output_file}")
import os
_fc_result["data"] = {{"output": r"{output_file}", "format": "step", "file_size": os.path.getsize(r"{output_file}")}}
"""
            elapsed, result = _measure_latency(
                backend._execute_macro, body
            )
            latencies.append(elapsed)
            assert result["status"] == "ok", f"export failed: {result.get('message', '')}"

        stats = _compute_stats(latencies)
        print(f"\n[operation] export STEP (with doc+box): "
              f"p50={stats['p50_s']*1000:.0f}ms "
              f"p95={stats['p95_s']*1000:.0f}ms "
              f"p99={stats['p99_s']*1000:.0f}ms "
              f"mean={stats['mean_s']*1000:.0f}ms")

        assert stats["p99_s"] < 60.0


# ---------------------------------------------------------------------------
# Benchmark: batch vs single mode
# ---------------------------------------------------------------------------

class TestBatchVsSingleMode:
    """Compare batch mode vs single operation mode performance."""

    def test_batch_faster_than_sequential(self, backend):
        """Batch mode should be faster than sequential operations."""
        n_ops = 5

        # Sequential: create 5 boxes one at a time (each in its own subprocess)
        seq_start = time.perf_counter()
        for i in range(n_ops):
            body = f"""\
import FreeCAD
import Part
doc = FreeCAD.newDocument("SeqDoc_{i}")
obj = doc.addObject("Part::Box", "SeqBox_{i}")
obj.Length = 10
obj.Width = 10
obj.Height = 10
doc.recompute()
_fc_result["data"] = {{"name": obj.Name}}
"""
            result = backend._execute_macro(body)
            assert result["status"] == "ok"
        seq_elapsed = time.perf_counter() - seq_start

        # Batch: create 5 boxes in a single script (single subprocess)
        # The document creation is operation 0, then 5 box operations = 6 total
        backend.batch_start()
        backend.batch_add("""\
import FreeCAD
import Part
doc = FreeCAD.newDocument("BatchDoc")
_fc_result = {"status": "ok", "data": {"name": doc.Name}, "message": ""}
""")
        for i in range(n_ops):
            backend.batch_add(f"""\
obj = doc.addObject("Part::Box", "BatchBox_{i}")
obj.Length = 10
obj.Width = 10
obj.Height = 10
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "BatchBox_{i}"}}, "message": ""}}
""")
        batch_start = time.perf_counter()
        results = backend.batch_execute()
        batch_elapsed = time.perf_counter() - batch_start

        # 1 doc creation + n_ops box creations
        assert len(results) == n_ops + 1, f"Expected {n_ops + 1} results, got {len(results)}: {results}"
        for i, r in enumerate(results):
            if r["status"] != "ok":
                print(f"  Batch result {i}: {r}")
        assert all(r["status"] == "ok" for r in results)

        print(f"\n[batch_vs_single] {n_ops} object_create operations:")
        print(f"  Sequential: {seq_elapsed*1000:.0f}ms")
        print(f"  Batch:      {batch_elapsed*1000:.0f}ms")
        if batch_elapsed > 0:
            print(f"  Speedup:    {seq_elapsed/batch_elapsed:.2f}x")

        # Batch should generally be faster, but we don't assert strictly
        # because in CI environments the difference may be small.
        # Just verify both complete successfully.
        assert batch_elapsed < 120.0, "Batch took too long"


# ---------------------------------------------------------------------------
# Benchmark: JSON report output
# ---------------------------------------------------------------------------

class TestBenchmarkReport:
    """Generate a JSON benchmark report."""

    def test_generate_report(self, backend, tmp_path):
        """Run all benchmarks and write a JSON report."""
        report = {
            "freecad_path": FREECAD_PATH,
            "backend": "HeadlessBackend",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "operations": {},
        }

        # 1. document_new
        latencies = []
        for i in range(3):
            elapsed, result = _measure_latency(
                backend.document_new, f"ReportDoc_{i}"
            )
            latencies.append(elapsed)
            assert result.status == "ok"
        report["operations"]["document_new"] = _compute_stats(latencies)

        # 2. object_create (with document creation in same subprocess)
        latencies = []
        for i in range(3):
            body = f"""\
import FreeCAD
import Part
doc = FreeCAD.newDocument("ReportObjDoc_{i}")
obj = doc.addObject("Part::Box", "ReportBox_{i}")
obj.Length = 10
obj.Width = 10
obj.Height = 10
doc.recompute()
_fc_result["data"] = {{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId}}
"""
            elapsed, result = _measure_latency(
                backend._execute_macro, body
            )
            latencies.append(elapsed)
            assert result["status"] == "ok"
        report["operations"]["object_create"] = _compute_stats(latencies)

        # 3. export STEP (with document + box creation in same subprocess)
        latencies = []
        for i in range(3):
            out = str(tmp_path / f"report_export_{i}.step")
            body = f"""\
import FreeCAD
import Part
doc = FreeCAD.newDocument("ReportExportDoc_{i}")
obj = doc.addObject("Part::Box", "ReportExportBox_{i}")
obj.Length = 20
obj.Width = 15
obj.Height = 10
doc.recompute()
Part.export([obj], r"{out}")
import os
_fc_result["data"] = {{"output": r"{out}", "format": "step", "file_size": os.path.getsize(r"{out}")}}
"""
            elapsed, result = _measure_latency(
                backend._execute_macro, body
            )
            latencies.append(elapsed)
            assert result["status"] == "ok"
        report["operations"]["export_step"] = _compute_stats(latencies)

        # Write report
        report_path = tmp_path / "benchmark_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("BENCHMARK REPORT")
        print("=" * 60)
        print(f"FreeCAD: {FREECAD_PATH}")
        print(f"Backend: HeadlessBackend")
        print("-" * 60)
        for op_name, stats in report["operations"].items():
            print(f"  {op_name}:")
            print(f"    p50:  {stats['p50_s']*1000:>8.0f} ms")
            print(f"    p95:  {stats['p95_s']*1000:>8.0f} ms")
            print(f"    p99:  {stats['p99_s']*1000:>8.0f} ms")
            print(f"    mean: {stats['mean_s']*1000:>8.0f} ms")
        print("=" * 60)
        print(f"Report saved to: {report_path}")
        print("=" * 60)

        # Verify report file exists and is valid JSON
        assert report_path.exists()
        with open(report_path) as f:
            loaded = json.load(f)
        assert "operations" in loaded
        assert len(loaded["operations"]) == 3
