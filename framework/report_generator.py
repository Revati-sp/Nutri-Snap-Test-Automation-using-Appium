"""Generate an HTML summary report from batch results.

Sections (deliverable-aligned):
  1. Run metadata          (config / data / app / batch start-finish times)
  2. Top-line statistics   (total / pass / fail / errors / pass rate)
  3. Test automation cost  (per-test wall-clock min / avg / max / total runtime)
  4. Result breakdowns     (by section, dimension, sub-dimension, app)
  5. Test script complexity (LOC / function / class / import counts per file + totals)
  6. Per-test detail table (with screenshots inline)
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Mapping, Sequence

from framework.complexity import ComplexityReport
from framework.stats import (
    BatchStatistics,
    BreakdownGroup,
    ExecutionTimeStats,
    RunSummary,
)


def _esc(val: object) -> str:
    return html.escape(str(val), quote=True)


def _summary_kv_table(summary: RunSummary) -> str:
    d = summary.as_dict()
    rows = [
        ("Total tests", d["total"]),
        ("Passed", f"<span class='PASS'>{d['passed']}</span>"),
        ("Failed", f"<span class='FAIL'>{d['failed']}</span>"),
        ("Errors", f"<span class='ERROR'>{d['errors']}</span>"),
        ("Pass rate (%)", f"{d['pass_rate']:.2f}"),
    ]
    body = "".join(f"<tr><th>{_esc(k)}</th><td>{v}</td></tr>" for k, v in rows)
    return f"<table class='kv'>{body}</table>"


def _exec_kv_table(exec_stats: ExecutionTimeStats) -> str:
    d = exec_stats.as_dict()
    rows = [
        ("Tests timed", d["samples"]),
        ("Total runtime (s)", f"{d['total']:.2f}"),
        ("Average per test (s)", f"{d['average']:.2f}"),
        ("Min (s)", f"{d['minimum']:.2f}"),
        ("Max (s)", f"{d['maximum']:.2f}"),
    ]
    body = "".join(f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>" for k, v in rows)
    return f"<table class='kv'>{body}</table>"


def _breakdown_table(title: str, groups: Sequence[BreakdownGroup]) -> str:
    if not groups:
        return ""
    head = (
        f"<h3>{_esc(title)}</h3>"
        "<table>"
        "<thead><tr>"
        "<th>Group</th><th>Total</th><th>Pass</th><th>Fail</th><th>Error</th><th>Pass %</th>"
        "</tr></thead><tbody>"
    )
    body_parts = []
    for g in groups:
        d = g.as_dict()
        body_parts.append(
            "<tr>"
            f"<td>{_esc(d['label'])}</td>"
            f"<td>{d['total']}</td>"
            f"<td class='PASS'>{d['passed']}</td>"
            f"<td class='FAIL'>{d['failed']}</td>"
            f"<td class='ERROR'>{d['errors']}</td>"
            f"<td>{d['pass_rate']:.2f}</td>"
            "</tr>"
        )
    return head + "".join(body_parts) + "</tbody></table>"


def _complexity_section(report: ComplexityReport | None) -> str:
    if report is None:
        return ""
    d = report.as_dict()
    totals = (
        "<table class='kv'>"
        f"<tr><th>Files (.py)</th><td>{d['file_count']}</td></tr>"
        f"<tr><th>Code lines</th><td>{d['total_code_lines']}</td></tr>"
        f"<tr><th>Comment lines</th><td>{d['total_comment_lines']}</td></tr>"
        f"<tr><th>Blank lines</th><td>{d['total_blank_lines']}</td></tr>"
        f"<tr><th>Physical lines (total)</th><td>{d['total_physical_lines']}</td></tr>"
        f"<tr><th>Functions</th><td>{d['total_function_count']}</td></tr>"
        f"<tr><th>Classes</th><td>{d['total_class_count']}</td></tr>"
        f"<tr><th>Imports</th><td>{d['total_import_count']}</td></tr>"
        f"<tr><th>Avg code lines / file</th><td>{d['avg_code_lines_per_file']}</td></tr>"
        "</table>"
    )
    file_rows = "".join(
        "<tr>"
        f"<td>{_esc(m.path)}</td>"
        f"<td>{m.code_lines}</td>"
        f"<td>{m.comment_lines}</td>"
        f"<td>{m.blank_lines}</td>"
        f"<td>{m.function_count}</td>"
        f"<td>{m.class_count}</td>"
        f"<td>{m.import_count}</td>"
        "</tr>"
        for m in report.files
    )
    file_table = (
        "<details><summary>Per-file breakdown ("
        f"{report.file_count} files, sorted by code lines desc)</summary>"
        "<table>"
        "<thead><tr>"
        "<th>File</th><th>Code</th><th>Comments</th><th>Blank</th>"
        "<th>Functions</th><th>Classes</th><th>Imports</th>"
        "</tr></thead><tbody>"
        f"{file_rows}"
        "</tbody></table></details>"
    )
    return totals + file_table


def _detail_table(rows: list[Mapping[str, Any]]) -> str:
    body_parts: list[str] = []
    for r in rows:
        raw_result = str(r.get("result", "")).strip().upper()
        css = raw_result if raw_result in {"PASS", "FAIL", "ERROR"} else ""
        shot = str(r.get("screenshot_path", "") or "").strip()
        shot_cell = ""
        if shot:
            shot_esc = _esc(shot)
            shot_cell = f'<a href="{shot_esc}">{shot_esc}</a><br/><img src="{shot_esc}" alt=""/>'
        dur = r.get("duration_seconds", "")
        dur_cell = f"{float(dur):.2f}" if str(dur).strip() else ""
        body_parts.append(
            "<tr>"
            f"<td>{_esc(r.get('test_id', ''))}</td>"
            f"<td>{_esc(r.get('app_name', ''))}</td>"
            f"<td>{_esc(r.get('section', ''))}</td>"
            f"<td>{_esc(r.get('dimension_type', ''))}</td>"
            f'<td class="{css}">{_esc(r.get("result", ""))}</td>'
            f"<td>{_esc(r.get('expected_output', ''))}</td>"
            f"<td>{_esc(r.get('actual_output', ''))}</td>"
            f"<td>{_esc(dur_cell)}</td>"
            f"<td>{_esc(r.get('error_message', ''))}</td>"
            f"<td>{shot_cell}</td>"
            f"<td>{_esc(r.get('timestamp', ''))}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr>"
        "<th>test_id</th><th>app</th><th>section</th><th>dimension</th><th>result</th>"
        "<th>expected_output</th><th>actual_output</th><th>duration (s)</th>"
        "<th>error_message</th><th>screenshot</th><th>timestamp</th>"
        "</tr></thead><tbody>"
        f"{''.join(body_parts)}"
        "</tbody></table>"
    )


def write_html_report(
    *,
    output_path: Path,
    rows: list[Mapping[str, Any]],
    summary: RunSummary,
    app_filter: str,
    config_path: Path,
    data_path: Path,
    started_iso: str,
    finished_iso: str,
    statistics: BatchStatistics | None = None,
    complexity: ComplexityReport | None = None,
) -> Path:
    """Write a self-contained HTML file next to ``reports/results.csv`` (typical).

    `summary` remains for backward compat; `statistics` (if provided) supersedes it for
    the breakdown / runtime sections. `complexity` is rendered only if provided.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    style = (
        "body{font-family:system-ui,sans-serif;margin:24px;line-height:1.45;color:#222;}"
        "h1{font-size:1.4rem;margin-bottom:4px;}"
        "h2{font-size:1.1rem;margin-top:28px;border-bottom:1px solid #ddd;padding-bottom:4px;}"
        "h3{font-size:0.95rem;margin-top:18px;color:#444;}"
        "table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px;}"
        "table.kv{width:auto;min-width:280px;}"
        "th,td{border:1px solid #ccc;padding:6px 10px;text-align:left;vertical-align:top;}"
        "th{background:#f4f4f4;font-weight:600;}"
        ".PASS{color:#0a7d12;font-weight:600;}"
        ".FAIL{color:#b00020;font-weight:600;}"
        ".ERROR{color:#a65f00;font-weight:600;}"
        ".meta{color:#444;font-size:13px;margin-bottom:12px;}"
        "img{max-width:240px;height:auto;border:1px solid #ddd;margin-top:4px;display:block;}"
        "details{margin-top:12px;}"
        "details summary{cursor:pointer;font-size:13px;color:#555;}"
        "section{margin-top:14px;}"
    )

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8"/>',
        "<title>Automation test report</title>",
        f"<style>{style}</style>",
        "</head>",
        "<body>",
        "<h1>Test automation report</h1>",
        '<p class="meta">'
        f"App filter: <strong>{_esc(app_filter)}</strong><br/>"
        f"Config: {_esc(config_path)}<br/>"
        f"Data: {_esc(data_path)}<br/>"
        f"Started: {_esc(started_iso)}<br/>"
        f"Finished: {_esc(finished_iso)}"
        "</p>",
        "<h2>1. Top-line statistics</h2>",
        _summary_kv_table(summary),
    ]

    if statistics is not None:
        parts.append("<h2>2. Test automation cost (execution time)</h2>")
        parts.append(_exec_kv_table(statistics.execution))

        parts.append("<h2>3. Result breakdowns</h2>")
        parts.append(_breakdown_table("By section", statistics.by_section))
        parts.append(_breakdown_table("By dimension", statistics.by_dimension))
        parts.append(_breakdown_table("By sub-dimension", statistics.by_sub_dimension))
        parts.append(_breakdown_table("By app", statistics.by_app))

    if complexity is not None:
        parts.append("<h2>4. Test script complexity</h2>")
        parts.append(_complexity_section(complexity))

    parts.append("<h2>5. Per-test detail</h2>")
    parts.append(_detail_table(rows))

    parts.extend(["</body>", "</html>"])
    output_path.write_text("\n".join(parts), encoding="utf-8")
    return output_path
