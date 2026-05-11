"""
Modular output validation: expected_output vs actual_output (Food Detection + Classification).

Rules return a ValidationResult to stop the chain, or None to defer to the next rule.
Default order: reject scaffold placeholders → normalized exact → lenient substring → final FAIL.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

# Scaffold rows in data/testcases.csv use this until replaced from Deliverable 2B.
DELIVERABLE_2B_PLACEHOLDER = "__REPLACE_WITH_DELIVERABLE_2B__"


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    message: str


@dataclass(frozen=True)
class OutputValidationContext:
    """Everything a rule may need; extend fields here rather than changing rule signatures."""

    expected_output: str
    actual_output: str
    testcase: Mapping[str, str]


def normalize_output_text(value: Optional[str]) -> str:
    """Shared normalization for simple rules (trim, lower, collapse whitespace)."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    return re.sub(r"\s+", " ", s)


def _is_placeholder_expected(raw: str) -> bool:
    s = (raw or "").strip()
    if not s:
        return True
    return normalize_output_text(s) == normalize_output_text(DELIVERABLE_2B_PLACEHOLDER)


class OutputMatchRule(ABC):
    """
    Return ValidationResult to finish (PASS or FAIL).
    Return None to let the next rule run.
    """

    @abstractmethod
    def evaluate(self, ctx: OutputValidationContext) -> Optional[ValidationResult]:
        raise NotImplementedError


class PlaceholderExpectedRule(OutputMatchRule):
    """FAIL when expected_output was not yet pasted from Deliverable 2B."""

    def evaluate(self, ctx: OutputValidationContext) -> Optional[ValidationResult]:
        if _is_placeholder_expected(ctx.expected_output):
            return ValidationResult(
                False,
                "expected_output is empty or still the scaffold placeholder — paste values from Deliverable 2B.",
            )
        return None


class NormalizedExactOutputRule(OutputMatchRule):
    """PASS on normalized equality; otherwise defer."""

    def evaluate(self, ctx: OutputValidationContext) -> Optional[ValidationResult]:
        exp = normalize_output_text(ctx.expected_output)
        act = normalize_output_text(ctx.actual_output)
        if exp == act:
            return ValidationResult(True, "normalized exact match on combined output")
        return None


class CommaSeparatedPartsPresentRule(OutputMatchRule):
    """
    PASS when ``expected_output`` lists several comma-separated phrases and each phrase
    appears somewhere in ``actual_output`` (after normalization).

    Bridges UI that omits commas, e.g. expected \"Pomegranate, Juice\" vs actual
    \"pomegranate juice\".
    """

    def evaluate(self, ctx: OutputValidationContext) -> Optional[ValidationResult]:
        exp_raw = str(ctx.expected_output or "")
        if "," not in exp_raw:
            return None
        parts = [normalize_output_text(p) for p in exp_raw.split(",") if normalize_output_text(p)]
        if len(parts) < 2:
            return None
        act = normalize_output_text(ctx.actual_output)
        if len(act) < 3:
            return None
        if all(p in act for p in parts):
            return ValidationResult(True, "all comma-separated expected phrases appear in actual")
        return None


class CommaTokenSetRule(OutputMatchRule):
    """
    PASS when expected and actual share the same set of comma-separated tokens (order-insensitive).

    Handles the common case where the same food is described differently:
      expected="Pomegranate, Juice"  vs  actual="Juice, Pomegranate"  -> PASS
    Both sides must contain a comma to apply (single-token outputs defer to other rules).
    """

    def evaluate(self, ctx: OutputValidationContext) -> Optional[ValidationResult]:
        exp_raw = normalize_output_text(ctx.expected_output)
        act_raw = normalize_output_text(ctx.actual_output)
        if "," not in exp_raw or "," not in act_raw:
            return None
        exp_set = {t.strip() for t in exp_raw.split(",") if t.strip()}
        act_set = {t.strip() for t in act_raw.split(",") if t.strip()}
        if not exp_set or not act_set:
            return None
        if exp_set == act_set:
            return ValidationResult(True, "comma-token set match (order-insensitive)")
        return None


class NormalizedSubstringOutputRule(OutputMatchRule):
    """
    PASS when wording differs but one normalized string fully contains the other
    (min length gate reduces accidental passes).
    """

    def __init__(self, min_len: int = 4) -> None:
        self._min_len = min_len

    def evaluate(self, ctx: OutputValidationContext) -> Optional[ValidationResult]:
        exp = normalize_output_text(ctx.expected_output)
        act = normalize_output_text(ctx.actual_output)
        if len(exp) < self._min_len or len(act) < self._min_len:
            return None
        if exp in act:
            return ValidationResult(True, "substring match: expected contained in actual")
        if act in exp:
            return ValidationResult(True, "substring match: actual contained in expected")
        return None


class FinalMismatchRule(OutputMatchRule):
    """Terminal FAIL when no earlier rule passed."""

    def evaluate(self, ctx: OutputValidationContext) -> Optional[ValidationResult]:
        exp = normalize_output_text(ctx.expected_output)
        act = normalize_output_text(ctx.actual_output)
        return ValidationResult(False, f"no rule accepted output (expected={exp!r}, actual={act!r})")


class CompositeOutputValidator:
    """Runs rules in order until one returns a ValidationResult."""

    def __init__(self, rules: Sequence[OutputMatchRule]) -> None:
        self._rules = tuple(rules)

    def validate(self, ctx: OutputValidationContext) -> ValidationResult:
        for rule in self._rules:
            out = rule.evaluate(ctx)
            if out is not None:
                return out
        return ValidationResult(False, "no rule returned a decision")


def default_output_validator() -> CompositeOutputValidator:
    """Default CMPE287 pipeline; reorder or insert rules for stricter/looser behavior."""
    return CompositeOutputValidator(
        (
            PlaceholderExpectedRule(),
            NormalizedExactOutputRule(),
            CommaTokenSetRule(),
            CommaSeparatedPartsPresentRule(),
            NormalizedSubstringOutputRule(min_len=4),
            FinalMismatchRule(),
        )
    )


def validate_testcase_output(
    testcase: Mapping[str, str],
    actual_output: str,
    validator: Optional[CompositeOutputValidator] = None,
) -> ValidationResult:
    v = validator or default_output_validator()
    ctx = OutputValidationContext(
        expected_output=str(testcase.get("expected_output", "")),
        actual_output=str(actual_output or ""),
        testcase=dict(testcase),
    )
    return v.validate(ctx)


def validate_outputs(
    testcase: Mapping[str, str],
    actual_output: str,
    validator: Optional[CompositeOutputValidator] = None,
) -> ValidationResult:
    return validate_testcase_output(testcase, actual_output, validator=validator)
