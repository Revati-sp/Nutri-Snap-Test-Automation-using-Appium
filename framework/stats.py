"""Summary statistics over a batch of test results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


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


def _result_code(row: Mapping[str, object]) -> str:
    r = str(row.get("result", row.get("status", ""))).strip().upper()
    return r


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


def format_summary(summary: RunSummary) -> str:
    d = summary.as_dict()
    return (
        f"Total: {d['total']} | Pass: {d['passed']} | Fail: {d['failed']} | "
        f"Errors: {d['errors']} | Pass %: {d['pass_rate']}"
    )
