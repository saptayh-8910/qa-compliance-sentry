"""Safe, dependency-free HTML dashboards for evaluation report v1."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from html import escape
from math import isfinite
from pathlib import Path
from typing import Any

from qa_assistant.reporting import EVALUATION_REPORT_SCHEMA_VERSION


class DashboardDataError(ValueError):
    """Raised when an evaluation report cannot be safely rendered."""


def _required_fields(
    value: Mapping[str, Any], fields: tuple[str, ...], location: str
) -> None:
    missing = tuple(field for field in fields if field not in value)
    if missing:
        raise DashboardDataError(
            f"{location} is missing required fields: {', '.join(missing)}"
        )


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DashboardDataError(f"{location} must be an object")
    return value


def _list(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise DashboardDataError(f"{location} must be an array")
    return value


def _string(value: object, location: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        qualifier = "a string" if empty else "a non-empty string"
        raise DashboardDataError(f"{location} must be {qualifier}")
    return value


def _boolean(value: object, location: str) -> bool:
    if not isinstance(value, bool):
        raise DashboardDataError(f"{location} must be a boolean")
    return value


def _integer(value: object, location: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DashboardDataError(
            f"{location} must be an integer greater than or equal to {minimum}"
        )
    return value


def _number(
    value: object,
    location: str,
    *,
    nullable: bool = False,
    maximum: float | None = None,
) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DashboardDataError(f"{location} must be a number")
    number = float(value)
    if not isfinite(number):
        raise DashboardDataError(f"{location} must be finite")
    if number < 0 or (maximum is not None and number > maximum):
        upper = f" and {maximum:g}" if maximum is not None else ""
        raise DashboardDataError(f"{location} must be between 0{upper}")
    return number


def _nullable_string(value: object, location: str) -> str | None:
    if value is None:
        return None
    return _string(value, location)


def _validate_run(report: Mapping[str, Any]) -> None:
    run = _mapping(report.get("run"), "run")
    _required_fields(
        run,
        (
            "run_id",
            "created_at",
            "dataset",
            "grader",
            "provider",
            "model",
            "reasoning_effort",
        ),
        "run",
    )
    for field in ("run_id", "created_at", "dataset", "grader", "provider"):
        _string(run.get(field), f"run.{field}")
    for field in ("model", "reasoning_effort"):
        _nullable_string(run.get(field), f"run.{field}")


def _validate_summary(report: Mapping[str, Any]) -> tuple[int, int]:
    summary = _mapping(report.get("summary"), "summary")
    _required_fields(
        summary,
        (
            "case_count",
            "passed_count",
            "pass_rate",
            "mean_context_precision",
            "mean_context_recall",
            "hit_rate_at_k",
            "mean_reciprocal_rank",
            "mean_citation_precision",
            "mean_citation_recall",
        ),
        "summary",
    )
    case_count = _integer(summary.get("case_count"), "summary.case_count", minimum=1)
    passed_count = _integer(summary.get("passed_count"), "summary.passed_count")
    if passed_count > case_count:
        raise DashboardDataError("summary.passed_count cannot exceed case_count")
    for field in (
        "pass_rate",
        "mean_context_precision",
        "mean_context_recall",
    ):
        _number(summary.get(field), f"summary.{field}", maximum=1)
    for field in (
        "hit_rate_at_k",
        "mean_reciprocal_rank",
        "mean_citation_precision",
        "mean_citation_recall",
    ):
        _number(
            summary.get(field),
            f"summary.{field}",
            nullable=True,
            maximum=1,
        )
    return case_count, passed_count


def _validate_answer(answer: object, location: str) -> None:
    if answer is None:
        return
    answer_data = _mapping(answer, location)
    _required_fields(answer_data, ("text", "citations"), location)
    _string(answer_data.get("text"), f"{location}.text")
    for index, citation_value in enumerate(
        _list(answer_data.get("citations"), f"{location}.citations")
    ):
        citation = _mapping(citation_value, f"{location}.citations[{index}]")
        _required_fields(
            citation,
            ("identifier", "source", "heading"),
            f"{location}.citations[{index}]",
        )
        _integer(
            citation.get("identifier"),
            f"{location}.citations[{index}].identifier",
            minimum=1,
        )
        for field in ("source", "heading"):
            _string(citation.get(field), f"{location}.citations[{index}].{field}")


def _validate_metrics(case: Mapping[str, Any], location: str) -> None:
    metrics = _mapping(case.get("metrics"), f"{location}.metrics")
    _required_fields(
        metrics,
        (
            "context_precision",
            "context_recall",
            "hit_at_k",
            "reciprocal_rank",
            "citation_precision",
            "citation_recall",
        ),
        f"{location}.metrics",
    )
    for field in ("context_precision", "context_recall"):
        _number(metrics.get(field), f"{location}.metrics.{field}", maximum=1)
    hit_at_k = metrics.get("hit_at_k")
    if hit_at_k is not None:
        _boolean(hit_at_k, f"{location}.metrics.hit_at_k")
    for field in ("reciprocal_rank", "citation_precision", "citation_recall"):
        _number(
            metrics.get(field),
            f"{location}.metrics.{field}",
            nullable=True,
            maximum=1,
        )


def _validate_checks(case: Mapping[str, Any], location: str) -> None:
    for index, check_value in enumerate(
        _list(case.get("checks"), f"{location}.checks")
    ):
        check = _mapping(check_value, f"{location}.checks[{index}]")
        _required_fields(
            check,
            ("name", "passed", "detail"),
            f"{location}.checks[{index}]",
        )
        _string(check.get("name"), f"{location}.checks[{index}].name")
        _boolean(check.get("passed"), f"{location}.checks[{index}].passed")
        _string(
            check.get("detail"),
            f"{location}.checks[{index}].detail",
            empty=True,
        )


def _validate_telemetry(case: Mapping[str, Any], location: str) -> None:
    telemetry = _mapping(case.get("telemetry"), f"{location}.telemetry")
    _required_fields(telemetry, ("duration_seconds", "usage"), f"{location}.telemetry")
    _number(
        telemetry.get("duration_seconds"),
        f"{location}.telemetry.duration_seconds",
    )
    usage_value = telemetry.get("usage")
    if usage_value is None:
        return
    usage = _mapping(usage_value, f"{location}.telemetry.usage")
    _required_fields(
        usage,
        ("input_tokens", "output_tokens", "total_tokens", "reasoning_tokens"),
        f"{location}.telemetry.usage",
    )
    for field in ("input_tokens", "output_tokens", "total_tokens"):
        _integer(usage.get(field), f"{location}.telemetry.usage.{field}")
    reasoning_tokens = usage.get("reasoning_tokens")
    if reasoning_tokens is not None:
        _integer(
            reasoning_tokens,
            f"{location}.telemetry.usage.reasoning_tokens",
        )


def validate_dashboard_report(report: object) -> Mapping[str, Any]:
    """Validate the v1 fields consumed by the HTML renderer."""
    data = _mapping(report, "report")
    version = data.get("schema_version")
    if version != EVALUATION_REPORT_SCHEMA_VERSION:
        raise DashboardDataError(
            "unsupported evaluation report schema_version "
            f"{version!r}; expected {EVALUATION_REPORT_SCHEMA_VERSION!r}"
        )
    _required_fields(data, ("schema_version", "run", "summary", "cases"), "report")
    _validate_run(data)
    expected_cases, expected_passed = _validate_summary(data)
    cases = _list(data.get("cases"), "cases")
    if len(cases) != expected_cases:
        raise DashboardDataError("summary.case_count does not match cases")

    case_ids: set[str] = set()
    actual_passed = 0
    for index, case_value in enumerate(cases):
        location = f"cases[{index}]"
        case = _mapping(case_value, location)
        _required_fields(
            case,
            (
                "case_id",
                "passed",
                "failure_summary",
                "error",
                "answer",
                "metrics",
                "checks",
                "telemetry",
            ),
            location,
        )
        case_id = _string(case.get("case_id"), f"{location}.case_id")
        if case_id in case_ids:
            raise DashboardDataError(f"duplicate case_id {case_id!r}")
        case_ids.add(case_id)
        passed = _boolean(case.get("passed"), f"{location}.passed")
        actual_passed += int(passed)
        _string(case.get("failure_summary"), f"{location}.failure_summary", empty=True)
        _nullable_string(case.get("error"), f"{location}.error")
        _validate_answer(case.get("answer"), f"{location}.answer")
        _validate_metrics(case, location)
        _validate_checks(case, location)
        _validate_telemetry(case, location)
    if actual_passed != expected_passed:
        raise DashboardDataError("summary.passed_count does not match cases")
    return data


def load_dashboard_report(report_path: Path) -> Mapping[str, Any]:
    """Load and validate a v1 evaluation report from disk."""
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DashboardDataError(
            f"invalid JSON in {report_path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
    return validate_dashboard_report(report)


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _metric(value: float | int | None) -> tuple[str, str]:
    if value is None:
        return "N/A", "0"
    percentage = float(value) * 100
    return f"{percentage:.0f}%", f"{percentage:.6g}"


def _metric_card(label: str, value: float | int | None, note: str) -> str:
    display, width = _metric(value)
    unavailable = " is-na" if value is None else ""
    return f"""
      <article class="metric-card{unavailable}">
        <p class="eyebrow">{_text(label)}</p>
        <p class="metric-value">{display}</p>
        <div class="metric-track" aria-hidden="true">
          <span style="width: {width}%"></span>
        </div>
        <p class="metric-note">{_text(note)}</p>
      </article>"""


def _metric_interpretation(label: str, value: object) -> str:
    if value is None:
        if label == "Hit@K":
            return "No supporting evidence was expected, so this does not apply."
        return "This score was not needed for this case; it is not a failure."
    if label == "Hit@K":
        if bool(value):
            return "Needed evidence appeared in the retrieved results."
        return "Needed evidence did not appear in the retrieved results."

    percentage = _metric(float(value))[0]
    if label == "Context precision":
        return f"{percentage} of the retrieved evidence was relevant."
    if label == "Context recall":
        return f"{percentage} of the needed evidence was found."
    if label == "Citation precision":
        return f"{percentage} of the cited sources were relevant."
    if label == "Citation recall":
        return f"{percentage} of the expected sources were cited."
    if label == "MRR":
        reciprocal_rank = float(value)
        if reciprocal_rank == 0:
            return "No useful result appeared in the ranked results."
        rank = round(1 / reciprocal_rank)
        if rank == 1:
            return "The first retrieved result was useful."
        return f"The first useful result appeared around position {rank}."
    raise ValueError(f"unknown dashboard metric {label!r}")


def _case_metric(label: str, value: object) -> str:
    if isinstance(value, bool):
        display = "Hit" if value else "Miss"
    elif value is None:
        display = "N/A"
    else:
        display = _metric(float(value))[0]
    interpretation = _metric_interpretation(label, value)
    return f"""<div class="case-metric">
      <span>{_text(label)}</span><strong>{display}</strong>
      <small>{_text(interpretation)}</small>
    </div>"""


def _reading_guide() -> str:
    criteria = (
        (
            "Context precision",
            "Of everything retrieved, how much was actually useful?",
        ),
        (
            "Context recall",
            "Of all evidence needed for the answer, how much did retrieval find?",
        ),
        (
            "Hit@K",
            "Did at least one needed piece of evidence appear in the top results?",
        ),
        (
            "MRR",
            "How early did the first useful result appear? 100% means it was first.",
        ),
        (
            "Citation precision",
            "Of the sources the answer cited, how many were relevant?",
        ),
        (
            "Citation recall",
            "Of the sources the answer should cite, how many did it include?",
        ),
    )
    items = "".join(
        f"""<div class="guide-item"><dt>{_text(label)}</dt>
          <dd>{_text(explanation)}</dd></div>"""
        for label, explanation in criteria
    )
    return f"""
    <section class="reading-guide" aria-labelledby="reading-guide-title">
      <div class="guide-heading">
        <div><p class="eyebrow">Plain-English guide</p>
          <h2 id="reading-guide-title">How to read this evaluation</h2></div>
        <p><strong>Higher percentages are better.</strong> “N/A” means a score
          does not apply to that scenario—it does not mean the scenario failed.</p>
      </div>
      <dl class="guide-grid">{items}</dl>
    </section>"""


def _checks_markup(checks: Sequence[Mapping[str, Any]]) -> str:
    items = []
    for check in checks:
        passed = bool(check["passed"])
        status = "pass" if passed else "fail"
        symbol = "✓" if passed else "×"
        items.append(
            f"""<li class="check {status}">
              <span class="check-icon" aria-hidden="true">{symbol}</span>
              <span><strong>{_text(check["name"])}</strong>
              <small>{_text(check["detail"])}</small></span>
            </li>"""
        )
    return "".join(items) or '<li class="empty">No checks recorded</li>'


def _citations_markup(answer: Mapping[str, Any] | None) -> str:
    if answer is None or not answer["citations"]:
        return '<p class="empty">No citations</p>'
    return "".join(
        f"""<div class="citation">
          <span>[{citation["identifier"]}]</span>
          <div><strong>{_text(citation["source"])}</strong>
          <small>{_text(citation["heading"])}</small></div>
        </div>"""
        for citation in answer["citations"]
    )


def _usage_markup(telemetry: Mapping[str, Any]) -> str:
    usage = telemetry["usage"]
    duration = float(telemetry["duration_seconds"])
    items = [f"<span><strong>{duration * 1000:.2f}</strong> ms</span>"]
    if usage is not None:
        items.append(
            f"<span><strong>{usage['total_tokens']}</strong> total tokens</span>"
        )
        if usage["reasoning_tokens"] is not None:
            items.append(
                f"<span><strong>{usage['reasoning_tokens']}</strong> reasoning</span>"
            )
    else:
        items.append("<span>Offline run · no token usage</span>")
    return "".join(items)


def _case_card(case: Mapping[str, Any], index: int) -> str:
    passed = bool(case["passed"])
    status = "passed" if passed else "failed"
    status_label = "Passed" if passed else "Failed"
    metrics = case["metrics"]
    answer = case["answer"]
    answer_text = answer["text"] if answer is not None else "No answer was produced."
    error = case["error"]
    error_markup = (
        f'<p class="error"><strong>Error:</strong> {_text(error)}</p>'
        if error is not None
        else ""
    )
    return f"""
    <article class="case-card {status}" data-status="{status}">
      <header class="case-header">
        <div>
          <p class="eyebrow">Case {index:02d}</p>
          <h2>{_text(case["case_id"])}</h2>
        </div>
        <span class="status-pill {status}">{status_label}</span>
      </header>
      <div class="case-metrics" aria-label="Case metrics">
        {_case_metric("Context precision", metrics["context_precision"])}
        {_case_metric("Context recall", metrics["context_recall"])}
        {_case_metric("Hit@K", metrics["hit_at_k"])}
        {_case_metric("MRR", metrics["reciprocal_rank"])}
        {_case_metric("Citation precision", metrics["citation_precision"])}
        {_case_metric("Citation recall", metrics["citation_recall"])}
      </div>
      <div class="case-grid">
        <section>
          <h3>Observed answer</h3>
          <blockquote>{_text(answer_text)}</blockquote>
          {error_markup}
          <p class="failure-summary"><strong>Verdict:</strong>
            {_text(case["failure_summary"])}</p>
        </section>
        <section>
          <h3>Evidence</h3>
          {_citations_markup(answer)}
        </section>
      </div>
      <section class="criteria" aria-label="Evaluation criteria">
        <div class="criteria-heading">
          <h3>Evaluation criteria</h3>
          <p>Every check below must pass for this case to pass.</p>
        </div>
        <ul class="checks">{_checks_markup(case["checks"])}</ul>
      </section>
      <footer class="telemetry">{_usage_markup(case["telemetry"])}</footer>
    </article>"""


def render_dashboard(report: object) -> str:
    """Render a validated evaluation report as a standalone HTML document."""
    data = validate_dashboard_report(report)
    run = data["run"]
    summary = data["summary"]
    cases = data["cases"]
    model = run["model"] or "Offline extractive baseline"
    effort = run["reasoning_effort"] or "Not applicable"
    cards = "".join(
        (
            _metric_card(
                "Pass rate",
                summary["pass_rate"],
                f"Every required check passed in {summary['passed_count']} "
                f"of {summary['case_count']} scenarios",
            ),
            _metric_card(
                "Context recall",
                summary["mean_context_recall"],
                "100% means all needed evidence was found",
            ),
            _metric_card(
                "Citation precision",
                summary["mean_citation_precision"],
                "100% means every cited source was relevant",
            ),
            _metric_card(
                "Mean reciprocal rank",
                summary["mean_reciprocal_rank"],
                "100% means the first retrieved result was useful",
            ),
        )
    )
    case_markup = "".join(
        _case_card(case, index) for index, case in enumerate(cases, start=1)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>RAG Evaluation · QA Compliance Sentry</title>
  <style>
    :root {{
      --ink: #f4f1e8; --muted: #9ea9b3; --panel: #101923;
      --line: #273442; --night: #071017; --mint: #65d6ad;
      --amber: #f1b85b; --coral: #ff7d6e; --blue: #78a8ff;
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ background: var(--night); scroll-behavior: smooth; }}
    body {{
      margin: 0; color: var(--ink); background:
        radial-gradient(circle at 82% -5%, #16334a 0, transparent 30rem),
        linear-gradient(180deg, #09131b 0%, var(--night) 100%);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif; line-height: 1.5;
    }}
    body::before {{
      content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .18;
      background-image: linear-gradient(#ffffff08 1px, transparent 1px),
        linear-gradient(90deg, #ffffff08 1px, transparent 1px);
      background-size: 32px 32px; mask-image: linear-gradient(to bottom, #000, transparent 65%);
    }}
    main {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 64px 0 80px; }}
    .hero {{ display: grid; grid-template-columns: 1.5fr 1fr; gap: 48px; align-items: end; }}
    .kicker, .eyebrow {{
      margin: 0 0 8px; color: var(--mint); font: 700 12px/1.2 ui-monospace,
        SFMono-Regular, Menlo, monospace; letter-spacing: .13em; text-transform: uppercase;
    }}
    h1 {{ margin: 0; max-width: 760px; font-size: clamp(42px, 7vw, 82px); line-height: .96;
      letter-spacing: -.055em; font-weight: 760; }}
    .lede {{ max-width: 650px; margin: 24px 0 0; color: #c5ccd2; font-size: 18px; }}
    .run-card {{ border-left: 1px solid var(--line); padding-left: 28px; }}
    .run-card dl {{ margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    dt {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    dd {{ margin: 3px 0 0; overflow-wrap: anywhere; font-weight: 650; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 52px 0; }}
    .metric-card, .case-card {{
      background: color-mix(in srgb, var(--panel) 92%, transparent); border: 1px solid var(--line);
      border-radius: var(--radius); box-shadow: 0 18px 50px #0000002b;
    }}
    .metric-card {{ padding: 22px; }}
    .metric-value {{ margin: 8px 0 15px; font-size: 40px; line-height: 1; letter-spacing: -.04em; }}
    .metric-track {{ height: 5px; border-radius: 10px; background: #26313a; overflow: hidden; }}
    .metric-track span {{ display: block; height: 100%; border-radius: inherit; background: var(--mint); }}
    .metric-card:nth-child(1) .metric-track span {{ background: var(--amber); }}
    .metric-card.is-na .metric-track {{ opacity: .35; }}
    .metric-note {{ margin: 13px 0 0; min-height: 40px; color: var(--muted); font-size: 13px; }}
    .reading-guide {{ margin: -24px 0 52px; padding: 26px; border: 1px solid #78a8ff45;
      border-radius: var(--radius); background: linear-gradient(135deg, #101d2a, #0d171f); }}
    .guide-heading {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; align-items: end;
      padding-bottom: 20px; border-bottom: 1px solid var(--line); }}
    .guide-heading h2 {{ margin: 0; font-size: 24px; }}
    .guide-heading > p {{ margin: 0; color: #c7d0d7; font-size: 14px; }}
    .guide-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; margin: 18px 0 0; }}
    .guide-item {{ padding: 13px 18px 13px 0; }}
    .guide-item dt {{ color: var(--ink); font-weight: 750; text-transform: none; letter-spacing: 0; }}
    .guide-item dd {{ color: var(--muted); font-size: 13px; font-weight: 400; }}
    .toolbar {{ display: flex; align-items: center; justify-content: space-between; gap: 20px;
      margin: 0 0 18px; }}
    .toolbar h2 {{ margin: 0; font-size: 24px; }}
    .filters {{ display: flex; padding: 4px; border: 1px solid var(--line); border-radius: 999px; }}
    .filters button {{ border: 0; border-radius: 999px; padding: 8px 15px; color: var(--muted);
      background: transparent; font: inherit; font-size: 13px; cursor: pointer; }}
    .filters button:hover {{ color: var(--ink); }}
    .filters button[aria-pressed="true"] {{ color: #071017; background: var(--ink); font-weight: 700; }}
    #case-count {{ color: var(--muted); font-size: 13px; }}
    .cases {{ display: grid; gap: 18px; }}
    .case-card {{ position: relative; overflow: hidden; padding: 28px; }}
    .case-card::before {{ content: ""; position: absolute; inset: 0 auto 0 0; width: 3px; background: var(--mint); }}
    .case-card.failed::before {{ background: var(--coral); }}
    .case-header {{ display: flex; justify-content: space-between; gap: 16px; align-items: start; }}
    .case-header h2 {{ margin: 0; font: 650 22px/1.25 ui-monospace, SFMono-Regular, Menlo, monospace;
      letter-spacing: -.03em; overflow-wrap: anywhere; }}
    .status-pill {{ padding: 6px 11px; border-radius: 999px; font-size: 12px; font-weight: 750; }}
    .status-pill.passed {{ color: var(--mint); background: #65d6ad18; border: 1px solid #65d6ad42; }}
    .status-pill.failed {{ color: var(--coral); background: #ff7d6e18; border: 1px solid #ff7d6e42; }}
    .case-metrics {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 1px; margin: 24px 0;
      overflow: hidden; border: 1px solid var(--line); border-radius: 12px; background: var(--line); }}
    .case-metric {{ display: grid; gap: 5px; padding: 13px; background: #0b151e; }}
    .case-metric span {{ color: var(--muted); font-size: 11px; }}
    .case-metric strong {{ font-size: 18px; }}
    .case-metric small {{ color: var(--muted); font-size: 11px; line-height: 1.4; }}
    .case-grid {{ display: grid; grid-template-columns: 1.7fr 1fr; gap: 28px; }}
    h3 {{ margin: 0 0 10px; color: var(--muted); font-size: 12px; text-transform: uppercase;
      letter-spacing: .09em; }}
    blockquote {{ margin: 0; padding: 17px 19px; color: #dce2e6; background: #0a131b;
      border-left: 2px solid var(--blue); border-radius: 0 10px 10px 0; white-space: pre-wrap; overflow-wrap: anywhere; }}
    .failure-summary, .error {{ margin: 12px 0 0; color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }}
    .failed .failure-summary {{ color: #ffc2bb; }}
    .error {{ color: var(--coral); }}
    .citation {{ display: flex; gap: 11px; align-items: start; padding: 12px 0; border-bottom: 1px solid var(--line); }}
    .citation > span {{ color: var(--blue); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .citation strong, .citation small {{ display: block; overflow-wrap: anywhere; }}
    .citation small {{ margin-top: 3px; color: var(--muted); }}
    .empty {{ color: var(--muted); font-style: italic; }}
    .criteria {{ margin-top: 22px; border-top: 1px solid var(--line); padding-top: 16px; }}
    .criteria-heading {{ display: flex; justify-content: space-between; gap: 18px; align-items: baseline; }}
    .criteria-heading h3, .criteria-heading p {{ margin: 0; }}
    .criteria-heading p {{ color: var(--muted); font-size: 12px; }}
    .checks {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9px; list-style: none; padding: 14px 0 0; margin: 0; }}
    .check {{ display: flex; gap: 10px; align-items: start; padding: 11px; border-radius: 10px; background: #0b151e; }}
    .check-icon {{ display: grid; place-items: center; flex: 0 0 22px; height: 22px; border-radius: 50%;
      color: #071017; background: var(--mint); font-weight: 900; }}
    .check.fail .check-icon {{ background: var(--coral); }}
    .check strong, .check small {{ display: block; }}
    .check small {{ margin-top: 3px; color: var(--muted); overflow-wrap: anywhere; }}
    .telemetry {{ display: flex; flex-wrap: wrap; gap: 18px; margin-top: 18px; color: var(--muted); font-size: 12px; }}
    .telemetry strong {{ color: var(--ink); }}
    .page-footer {{ margin-top: 40px; color: var(--muted); font-size: 12px; text-align: center; }}
    [hidden] {{ display: none !important; }}
    @media (max-width: 900px) {{
      .hero, .case-grid, .guide-heading {{ grid-template-columns: 1fr; }} .run-card {{ border-left: 0; border-top: 1px solid var(--line); padding: 24px 0 0; }}
      .metrics {{ grid-template-columns: 1fr 1fr; }} .case-metrics, .guide-grid {{ grid-template-columns: repeat(3, 1fr); }}
    }}
    @media (max-width: 580px) {{
      main {{ width: min(100% - 20px, 1180px); padding-top: 38px; }} h1 {{ font-size: 43px; }}
      .metrics {{ grid-template-columns: 1fr; margin: 36px 0; }} .toolbar {{ align-items: start; flex-direction: column; }}
      .case-card {{ padding: 21px 18px; }} .case-header {{ align-items: start; flex-direction: column; }}
      .case-metrics {{ grid-template-columns: 1fr 1fr; }} .checks, .guide-grid {{ grid-template-columns: 1fr; }}
      .criteria-heading {{ align-items: start; flex-direction: column; }}
      .run-card dl {{ grid-template-columns: 1fr; }}
    }}
    @media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior: auto; }} }}
  </style>
</head>
<body>
  <main>
    <section class="hero" aria-labelledby="page-title">
      <div>
        <p class="kicker">QA Compliance Sentry · Evaluation evidence</p>
        <h1 id="page-title">Grounded RAG quality, made visible.</h1>
        <p class="lede">A deterministic view of retrieval, citations, safety,
          and answer behavior. Failed cases stay visible so the baseline remains
          useful for diagnosis—not just presentation.</p>
      </div>
      <aside class="run-card" aria-label="Evaluation run metadata">
        <dl>
          <div><dt>Provider</dt><dd>{_text(run["provider"])}</dd></div>
          <div><dt>Model</dt><dd>{_text(model)}</dd></div>
          <div><dt>Dataset</dt><dd>{_text(run["dataset"])}</dd></div>
          <div><dt>Grader</dt><dd>{_text(run["grader"])}</dd></div>
          <div><dt>Reasoning</dt><dd>{_text(effort)}</dd></div>
          <div><dt>Created</dt><dd>{_text(run["created_at"])}</dd></div>
        </dl>
      </aside>
    </section>
    <section class="metrics" aria-label="Aggregate quality metrics">{cards}</section>
    {_reading_guide()}
    <section aria-labelledby="cases-heading">
      <div class="toolbar">
        <div><h2 id="cases-heading">Evaluation cases</h2>
          <span id="case-count">Showing {len(cases)} of {len(cases)}</span></div>
        <div class="filters" role="group" aria-label="Filter evaluation cases">
          <button type="button" data-filter="all" aria-pressed="true">All</button>
          <button type="button" data-filter="passed" aria-pressed="false">Passed</button>
          <button type="button" data-filter="failed" aria-pressed="false">Failed</button>
        </div>
      </div>
      <div class="cases">{case_markup}</div>
    </section>
    <footer class="page-footer">Schema v{_text(data["schema_version"])} ·
      Run {_text(run["run_id"])} · Generated locally from versioned evidence</footer>
  </main>
  <script>
    (() => {{
      const buttons = [...document.querySelectorAll("[data-filter]")];
      const cards = [...document.querySelectorAll("[data-status]")];
      const count = document.querySelector("#case-count");
      for (const button of buttons) {{
        button.addEventListener("click", () => {{
          const filter = button.dataset.filter;
          let visible = 0;
          for (const card of cards) {{
            const show = filter === "all" || card.dataset.status === filter;
            card.hidden = !show;
            visible += Number(show);
          }}
          for (const candidate of buttons) {{
            candidate.setAttribute("aria-pressed", String(candidate === button));
          }}
          count.textContent = `Showing ${{visible}} of ${{cards.length}}`;
        }});
      }}
    }})();
  </script>
</body>
</html>
"""


def write_dashboard(report_path: Path, output: Path) -> None:
    """Load a report and atomically write its standalone HTML dashboard."""
    report = load_dashboard_report(report_path)
    rendered = render_dashboard(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(rendered)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(output)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
