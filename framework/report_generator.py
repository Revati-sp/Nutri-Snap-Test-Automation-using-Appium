"""Generate an HTML summary report from batch results (readable alongside CSV)."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Mapping

from framework.stats import RunSummary


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
) -> Path:
    """Write a self-contained HTML file next to ``reports/results.csv`` (typical)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def esc(val: object) -> str:
        return html.escape(str(val), quote=True)

    summary_html = esc(summary.as_dict())

    head_lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8"/>',
        "<title>Automation test report</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:24px;line-height:1.45;}",
        "h1{font-size:1.25rem;}",
        "table{border-collapse:collapse;width:100%;font-size:13px;}",
        "th,td{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:top;}",
        "th{background:#f4f4f4;}",
        ".PASS{color:#0a7d12;font-weight:600;}",
        ".FAIL{color:#b00020;font-weight:600;}",
        ".ERROR{color:#a65f00;font-weight:600;}",
        ".meta{color:#444;font-size:14px;margin-bottom:16px;}",
        "img{max-width:240px;height:auto;border:1px solid #ddd;margin-top:4px;}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Test automation report</h1>",
        f'<p class="meta">App filter: <strong>{esc(app_filter)}</strong><br/>'
        f"Config: {esc(config_path)}<br/>"
        f"Data: {esc(data_path)}<br/>"
        f"Started: {esc(started_iso)} — Finished: {esc(finished_iso)}<br/>"
        f"Summary: {summary_html}</p>",
        "<table>",
        "<thead><tr>",
        "<th>test_id</th><th>app</th><th>result</th>",
        "<th>expected_output</th><th>actual_output</th>",
        "<th>error_message</th><th>screenshot</th><th>timestamp</th>",
        "</tr></thead>",
        "<tbody>",
    ]

    body_parts: list[str] = []
    for r in rows:
        raw_result = str(r.get("result", "")).strip().upper()
        css = raw_result if raw_result in {"PASS", "FAIL", "ERROR"} else ""
        shot = str(r.get("screenshot_path", "") or "").strip()
        shot_cell = ""
        if shot:
            shot_esc = esc(shot)
            # Paths are stored relative to the report directory (e.g. screenshots/...)
            shot_cell = f'<a href="{shot_esc}">{shot_esc}</a><br/><img src="{shot_esc}" alt=""/>'
        body_parts.append(
            "<tr>"
            f"<td>{esc(r.get('test_id', ''))}</td>"
            f"<td>{esc(r.get('app_name', ''))}</td>"
            f'<td class="{css}">{esc(r.get("result", ""))}</td>'
            f"<td>{esc(r.get('expected_output', ''))}</td>"
            f"<td>{esc(r.get('actual_output', ''))}</td>"
            f"<td>{esc(r.get('error_message', ''))}</td>"
            f"<td>{shot_cell}</td>"
            f"<td>{esc(r.get('timestamp', ''))}</td>"
            "</tr>"
        )

    tail = ["</tbody>", "</table>", "</body>", "</html>"]

    output_path.write_text("\n".join(head_lines + body_parts + tail), encoding="utf-8")
    return output_path
