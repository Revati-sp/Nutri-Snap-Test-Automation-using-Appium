"""Static complexity metrics for the test automation scripts themselves.

Walks the framework/, apps/, tests/ source trees and reports:
  * file count
  * total / mean physical lines (LOC including blanks)
  * total / mean code lines (non-blank, non-comment)
  * function (`def`) count
  * class count
  * total ``import`` statement count

Plus per-file numbers, sortable by code lines.

Why this matters for the deliverable: the assignment asks for "test script complexity"
metrics. This module produces the table that feeds straight into the HTML report's
"Test Script Complexity" section without requiring an external tool like radon.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

# Directories whose .py files should be reported as part of the test automation.
# We deliberately exclude:
#   - virtualenv (.venv)
#   - reports/ (output)
#   - data/ (test inputs)
#   - any __pycache__
DEFAULT_INCLUDE = ("framework", "apps", "tests", "scripts")


@dataclass(frozen=True)
class FileMetrics:
    path: str
    physical_lines: int
    code_lines: int
    blank_lines: int
    comment_lines: int
    function_count: int
    class_count: int
    import_count: int

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "physical_lines": self.physical_lines,
            "code_lines": self.code_lines,
            "blank_lines": self.blank_lines,
            "comment_lines": self.comment_lines,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "import_count": self.import_count,
        }


@dataclass(frozen=True)
class ComplexityReport:
    file_count: int
    total_physical_lines: int
    total_code_lines: int
    total_blank_lines: int
    total_comment_lines: int
    total_function_count: int
    total_class_count: int
    total_import_count: int
    files: tuple[FileMetrics, ...]

    @property
    def avg_code_lines_per_file(self) -> float:
        return (self.total_code_lines / self.file_count) if self.file_count else 0.0

    def as_dict(self) -> dict:
        return {
            "file_count": self.file_count,
            "total_physical_lines": self.total_physical_lines,
            "total_code_lines": self.total_code_lines,
            "total_blank_lines": self.total_blank_lines,
            "total_comment_lines": self.total_comment_lines,
            "total_function_count": self.total_function_count,
            "total_class_count": self.total_class_count,
            "total_import_count": self.total_import_count,
            "avg_code_lines_per_file": round(self.avg_code_lines_per_file, 2),
        }


def _is_skipped_dir(p: Path) -> bool:
    parts = set(p.parts)
    return any(part in parts for part in (".venv", "__pycache__", ".git", "node_modules"))


def _iter_python_files(roots: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.py")):
            if _is_skipped_dir(p):
                continue
            out.append(p)
    return out


def _measure_file(path: Path, repo_root: Path) -> FileMetrics:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")

    lines = text.splitlines()
    physical = len(lines)
    blanks = 0
    comments = 0
    code = 0
    funcs = 0
    classes = 0
    imports = 0

    for raw in lines:
        s = raw.strip()
        if not s:
            blanks += 1
            continue
        if s.startswith("#"):
            comments += 1
            continue
        code += 1
        if s.startswith("def ") or s.startswith("async def "):
            funcs += 1
        elif s.startswith("class "):
            classes += 1
        elif s.startswith("import ") or s.startswith("from "):
            imports += 1

    rel = path.resolve()
    try:
        rel = rel.relative_to(repo_root.resolve())
    except ValueError:
        pass
    return FileMetrics(
        path=str(rel),
        physical_lines=physical,
        code_lines=code,
        blank_lines=blanks,
        comment_lines=comments,
        function_count=funcs,
        class_count=classes,
        import_count=imports,
    )


def measure_repository(
    repo_root: str | Path,
    include_dirs: Sequence[str] = DEFAULT_INCLUDE,
) -> ComplexityReport:
    """Walk `repo_root/<include_dirs>/**.py` and aggregate metrics."""
    root = Path(repo_root)
    roots = [root / d for d in include_dirs]
    files = _iter_python_files(roots)
    metrics = [_measure_file(p, root) for p in files]

    metrics_sorted = tuple(sorted(metrics, key=lambda m: (-m.code_lines, m.path)))

    return ComplexityReport(
        file_count=len(metrics_sorted),
        total_physical_lines=sum(m.physical_lines for m in metrics_sorted),
        total_code_lines=sum(m.code_lines for m in metrics_sorted),
        total_blank_lines=sum(m.blank_lines for m in metrics_sorted),
        total_comment_lines=sum(m.comment_lines for m in metrics_sorted),
        total_function_count=sum(m.function_count for m in metrics_sorted),
        total_class_count=sum(m.class_count for m in metrics_sorted),
        total_import_count=sum(m.import_count for m in metrics_sorted),
        files=metrics_sorted,
    )


def format_report(report: ComplexityReport) -> str:
    d = report.as_dict()
    return (
        f"Test scripts: files={d['file_count']}  "
        f"code_lines={d['total_code_lines']}  "
        f"functions={d['total_function_count']}  "
        f"classes={d['total_class_count']}  "
        f"imports={d['total_import_count']}  "
        f"avg_code_lines/file={d['avg_code_lines_per_file']}"
    )
