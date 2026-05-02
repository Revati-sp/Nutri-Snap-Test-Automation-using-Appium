"""Summary statistics over a batch of test results.

Provides three views the deliverable asks for:
  * `RunSummary`         — total/pass/fail/errors + pass rate (high-level scoreboard).
  * `ExecutionTimeStats` — min/max/avg/total seconds per test (test automation cost proxy).
  * `BreakdownGroup`     — pass/fail counts grouped by an arbitrary categorical column
                            (section, dimension_type, sub_dimension, app_name, ...).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class RunSummary:
    total: int
    passed: int
    failed: int
    errors: int
    pass_rate: float

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "pass_rate": round(self.pass_rate, 2),
        }


@dataclass(frozen=True)
class ExecutionTimeStats:
    """Per-test wall-clock cost. All values in seconds."""

    samples: int
    total: float
    average: float
    minimum: float
    maximum: float

    def as_dict(self) -> dict:
        return {
            "samples": self.samples,
            "total": round(self.total, 3),
            "average": round(self.average, 3),
            "minimum": round(self.minimum, 3),
            "maximum": round(self.maximum, 3),
        }


@dataclass(frozen=True)
class BreakdownGroup:
    """One row of a categorical breakdown (e.g. {"section": "Context"} -> 5 PASS / 2 FAIL)."""

    label: str
    total: int
    passed: int
    failed: int
    errors: int
    pass_rate: float

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "pass_rate": round(self.pass_rate, 2),
        }


@dataclass(frozen=True)
class BatchStatistics:
    """Convenience bundle of every metric the HTML/CLI/report tooling consumes."""

    summary: RunSummary
    execution: ExecutionTimeStats
    by_section: tuple[BreakdownGroup, ...] = field(default_factory=tuple)
    by_dimension: tuple[BreakdownGroup, ...] = field(default_factory=tuple)
    by_sub_dimension: tuple[BreakdownGroup, ...] = field(default_factory=tuple)
    by_app: tuple[BreakdownGroup, ...] = field(default_factory=tuple)


def _result_code(row: Mapping[str, object]) -> str:
    r = str(row.get("result", row.get("status", ""))).strip().upper()
    return r


def _coerce_float(val: object) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def summarize_results(rows: Iterable[Mapping[str, object]]) -> RunSummary:
    total = 0
    passed = 0
    failed = 0
    errors = 0
    for r in rows:
        total += 1
        code = _result_code(r)
        if code == "PASS":
            passed += 1
        elif code == "FAIL":
            failed += 1
        elif code == "ERROR":
            errors += 1
        else:
            failed += 1
    rate = (100.0 * passed / total) if total else 0.0
    return RunSummary(total=total, passed=passed, failed=failed, errors=errors, pass_rate=rate)


def execution_time_stats(rows: Iterable[Mapping[str, object]]) -> ExecutionTimeStats:
    """Compute per-test runtime stats from `duration_seconds` cells (skips empty/non-numeric)."""
    durations: list[float] = []
    for r in rows:
        d = _coerce_float(r.get("duration_seconds"))
        if d is not None and d >= 0:
            durations.append(d)
    if not durations:
        return ExecutionTimeStats(samples=0, total=0.0, average=0.0, minimum=0.0, maximum=0.0)
    total = sum(durations)
    return ExecutionTimeStats(
        samples=len(durations),
        total=total,
        average=total / len(durations),
        minimum=min(durations),
        maximum=max(durations),
    )


def breakdown_by(rows: Sequence[Mapping[str, object]], column: str) -> tuple[BreakdownGroup, ...]:
    """Group rows by `column` value, then count PASS/FAIL/ERROR per group.

    Useful for the deliverable's per-dimension scorecards (e.g. how Lose It! scores on
    "Illumination" rows vs "Composition" rows). Empty/missing values are bucketed as "(unset)".
    """
    buckets: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for r in rows:
        key = str(r.get(column, "")).strip() or "(unset)"
        buckets[key].append(r)
    groups: list[BreakdownGroup] = []
    for label, group_rows in sorted(buckets.items()):
        s = summarize_results(group_rows)
        groups.append(
            BreakdownGroup(
                label=label,
                total=s.total,
                passed=s.passed,
                failed=s.failed,
                errors=s.errors,
                pass_rate=s.pass_rate,
            )
        )
    return tuple(groups)


def compute_batch_statistics(rows: Sequence[Mapping[str, object]]) -> BatchStatistics:
    """One-call helper that returns every stat the report needs."""
    return BatchStatistics(
        summary=summarize_results(rows),
        execution=execution_time_stats(rows),
        by_section=breakdown_by(rows, "section"),
        by_dimension=breakdown_by(rows, "dimension_type"),
        by_sub_dimension=breakdown_by(rows, "sub_dimension"),
        by_app=breakdown_by(rows, "app_name"),
    )


def format_summary(summary: RunSummary) -> str:
    d = summary.as_dict()
    return (
        f"Total: {d['total']} | Pass: {d['passed']} | Fail: {d['failed']} | "
        f"Errors: {d['errors']} | Pass %: {d['pass_rate']}"
    )


def format_execution(exec_stats: ExecutionTimeStats) -> str:
    d = exec_stats.as_dict()
    return (
        f"Runtime (s): total={d['total']:.1f}  avg={d['average']:.1f}  "
        f"min={d['minimum']:.1f}  max={d['maximum']:.1f}  (n={d['samples']})"
    )
