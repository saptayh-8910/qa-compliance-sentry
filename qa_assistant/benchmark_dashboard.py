"""Safe standalone dashboard for repeated RAG benchmark evidence."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from html import escape
from math import isfinite
from pathlib import Path
from typing import Any

from qa_assistant.benchmarking import BENCHMARK_REPORT_SCHEMA_VERSION


class BenchmarkDashboardDataError(ValueError):
    """Raised when benchmark evidence cannot be safely rendered."""


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkDashboardDataError(f"{location} must be an object")
    return value


def _list(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise BenchmarkDashboardDataError(f"{location} must be an array")
    return value


def _required(value: Mapping[str, Any], fields: tuple[str, ...], location: str) -> None:
    missing = tuple(field for field in fields if field not in value)
    if missing:
        raise BenchmarkDashboardDataError(
            f"{location} is missing required fields: {', '.join(missing)}"
        )


def _string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkDashboardDataError(f"{location} must be a non-empty string")
    return value


def _nullable_string(value: object, location: str) -> str | None:
    if value is None:
        return None
    return _string(value, location)


def _integer(value: object, location: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise BenchmarkDashboardDataError(
            f"{location} must be an integer greater than or equal to {minimum}"
        )
    return value


def _number(value: object, location: str, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenchmarkDashboardDataError(f"{location} must be a number")
    number = float(value)
    if not isfinite(number):
        raise BenchmarkDashboardDataError(f"{location} must be finite")
    if number < 0 or (maximum is not None and number > maximum):
        upper = f" and {maximum:g}" if maximum is not None else ""
        raise BenchmarkDashboardDataError(f"{location} must be between 0{upper}")
    return number


def _validate_latency(value: object, location: str, sample_count: int) -> None:
    latency = _mapping(value, location)
    fields = (
        "sample_count",
        "minimum_seconds",
        "p50_seconds",
        "p95_seconds",
        "maximum_seconds",
        "mean_seconds",
    )
    _required(latency, fields, location)
    if (
        _integer(latency.get("sample_count"), f"{location}.sample_count", 1)
        != sample_count
    ):
        raise BenchmarkDashboardDataError(
            f"{location}.sample_count does not match its parent"
        )
    values = {
        field: _number(latency.get(field), f"{location}.{field}")
        for field in fields[1:]
    }
    if not (
        values["minimum_seconds"]
        <= values["p50_seconds"]
        <= values["p95_seconds"]
        <= values["maximum_seconds"]
    ):
        raise BenchmarkDashboardDataError(
            f"{location} percentiles must be ordered from minimum to maximum"
        )


def _validate_tokens(value: object, location: str, maximum_samples: int) -> None:
    if value is None:
        return
    tokens = _mapping(value, location)
    fields = (
        "sample_count",
        "total_input_tokens",
        "total_output_tokens",
        "total_tokens",
        "total_reasoning_tokens",
        "mean_total_tokens",
        "p50_total_tokens",
        "p95_total_tokens",
    )
    _required(tokens, fields, location)
    sample_count = _integer(tokens.get("sample_count"), f"{location}.sample_count", 1)
    if sample_count > maximum_samples:
        raise BenchmarkDashboardDataError(
            f"{location}.sample_count cannot exceed benchmark samples"
        )
    for field in ("total_input_tokens", "total_output_tokens", "total_tokens"):
        _integer(tokens.get(field), f"{location}.{field}")
    reasoning = tokens.get("total_reasoning_tokens")
    if reasoning is not None:
        _integer(reasoning, f"{location}.total_reasoning_tokens")
    mean = _number(tokens.get("mean_total_tokens"), f"{location}.mean_total_tokens")
    p50 = _number(tokens.get("p50_total_tokens"), f"{location}.p50_total_tokens")
    p95 = _number(tokens.get("p95_total_tokens"), f"{location}.p95_total_tokens")
    if p50 > p95:
        raise BenchmarkDashboardDataError(
            f"{location} p50_total_tokens cannot exceed p95_total_tokens"
        )
    if mean > tokens["total_tokens"]:
        raise BenchmarkDashboardDataError(
            f"{location}.mean_total_tokens cannot exceed total_tokens"
        )


def validate_benchmark_report(report: object) -> Mapping[str, Any]:
    """Validate every benchmark field consumed by the renderer."""
    data = _mapping(report, "report")
    if data.get("schema_version") != BENCHMARK_REPORT_SCHEMA_VERSION:
        raise BenchmarkDashboardDataError(
            "unsupported benchmark report schema_version "
            f"{data.get('schema_version')!r}; expected "
            f"{BENCHMARK_REPORT_SCHEMA_VERSION!r}"
        )
    _required(data, ("schema_version", "run", "summary", "cases"), "report")
    run = _mapping(data.get("run"), "run")
    _required(
        run,
        (
            "benchmark_id",
            "created_at",
            "dataset",
            "grader",
            "provider",
            "model",
            "reasoning_effort",
            "repetitions",
        ),
        "run",
    )
    for field in ("benchmark_id", "created_at", "dataset", "grader", "provider"):
        _string(run.get(field), f"run.{field}")
    for field in ("model", "reasoning_effort"):
        _nullable_string(run.get(field), f"run.{field}")
    repetitions = _integer(run.get("repetitions"), "run.repetitions", 2)

    summary = _mapping(data.get("summary"), "summary")
    _required(
        summary,
        (
            "case_count",
            "sample_count",
            "passed_sample_count",
            "sample_pass_rate",
            "stable_case_count",
            "stability_rate",
            "response_stable_case_count",
            "response_stability_rate",
            "latency",
            "tokens",
        ),
        "summary",
    )
    case_count = _integer(summary.get("case_count"), "summary.case_count", 1)
    sample_count = _integer(summary.get("sample_count"), "summary.sample_count", 1)
    passed_count = _integer(
        summary.get("passed_sample_count"), "summary.passed_sample_count"
    )
    stable_count = _integer(
        summary.get("stable_case_count"), "summary.stable_case_count"
    )
    response_stable_count = _integer(
        summary.get("response_stable_case_count"),
        "summary.response_stable_case_count",
    )
    pass_rate = _number(summary.get("sample_pass_rate"), "summary.sample_pass_rate", 1)
    stability_rate = _number(summary.get("stability_rate"), "summary.stability_rate", 1)
    response_stability_rate = _number(
        summary.get("response_stability_rate"),
        "summary.response_stability_rate",
        1,
    )
    if sample_count != case_count * repetitions:
        raise BenchmarkDashboardDataError(
            "summary.sample_count must equal case_count multiplied by repetitions"
        )
    if (
        passed_count > sample_count
        or stable_count > case_count
        or response_stable_count > case_count
    ):
        raise BenchmarkDashboardDataError("benchmark summary counts are inconsistent")
    if abs(pass_rate - passed_count / sample_count) > 1e-12:
        raise BenchmarkDashboardDataError(
            "summary.sample_pass_rate does not match counts"
        )
    if abs(stability_rate - stable_count / case_count) > 1e-12:
        raise BenchmarkDashboardDataError(
            "summary.stability_rate does not match counts"
        )
    if abs(response_stability_rate - response_stable_count / case_count) > 1e-12:
        raise BenchmarkDashboardDataError(
            "summary.response_stability_rate does not match counts"
        )
    _validate_latency(summary.get("latency"), "summary.latency", sample_count)
    _validate_tokens(summary.get("tokens"), "summary.tokens", sample_count)

    cases = _list(data.get("cases"), "cases")
    if len(cases) != case_count:
        raise BenchmarkDashboardDataError("summary.case_count does not match cases")
    case_ids: set[str] = set()
    actual_passed = 0
    actual_stable = 0
    actual_response_stable = 0
    allowed_verdicts = {"consistently-passed", "consistently-failed", "variable"}
    for index, value in enumerate(cases):
        location = f"cases[{index}]"
        case = _mapping(value, location)
        _required(
            case,
            (
                "case_id",
                "question",
                "expected_behavior",
                "sample_count",
                "passed_count",
                "pass_rate",
                "stable",
                "verdict",
                "answer_variant_count",
                "citation_variant_count",
                "response_stable",
                "latency",
                "tokens",
            ),
            location,
        )
        case_id = _string(case.get("case_id"), f"{location}.case_id")
        if case_id in case_ids:
            raise BenchmarkDashboardDataError(f"duplicate case_id {case_id!r}")
        case_ids.add(case_id)
        _string(case.get("question"), f"{location}.question")
        if case.get("expected_behavior") not in {"supported", "abstain"}:
            raise BenchmarkDashboardDataError(
                f"{location}.expected_behavior must be supported or abstain"
            )
        if (
            _integer(case.get("sample_count"), f"{location}.sample_count", 1)
            != repetitions
        ):
            raise BenchmarkDashboardDataError(
                f"{location}.sample_count must equal repetitions"
            )
        case_passed = _integer(case.get("passed_count"), f"{location}.passed_count")
        if case_passed > repetitions:
            raise BenchmarkDashboardDataError(
                f"{location}.passed_count cannot exceed sample_count"
            )
        case_rate = _number(case.get("pass_rate"), f"{location}.pass_rate", 1)
        if abs(case_rate - case_passed / repetitions) > 1e-12:
            raise BenchmarkDashboardDataError(
                f"{location}.pass_rate does not match counts"
            )
        stable = case.get("stable")
        if not isinstance(stable, bool):
            raise BenchmarkDashboardDataError(f"{location}.stable must be a boolean")
        verdict = case.get("verdict")
        if verdict not in allowed_verdicts:
            raise BenchmarkDashboardDataError(f"{location}.verdict is invalid")
        expected_verdict = (
            "variable"
            if not stable
            else "consistently-passed"
            if case_passed == repetitions
            else "consistently-failed"
        )
        if verdict != expected_verdict:
            raise BenchmarkDashboardDataError(
                f"{location}.verdict does not match its outcomes"
            )
        answer_variants = _integer(
            case.get("answer_variant_count"),
            f"{location}.answer_variant_count",
            1,
        )
        citation_variants = _integer(
            case.get("citation_variant_count"),
            f"{location}.citation_variant_count",
            1,
        )
        response_stable = case.get("response_stable")
        if not isinstance(response_stable, bool):
            raise BenchmarkDashboardDataError(
                f"{location}.response_stable must be a boolean"
            )
        if response_stable != (answer_variants == citation_variants == 1):
            raise BenchmarkDashboardDataError(
                f"{location}.response_stable does not match variant counts"
            )
        _validate_latency(case.get("latency"), f"{location}.latency", repetitions)
        _validate_tokens(case.get("tokens"), f"{location}.tokens", repetitions)
        actual_passed += case_passed
        actual_stable += int(stable)
        actual_response_stable += int(response_stable)
    if (
        actual_passed != passed_count
        or actual_stable != stable_count
        or actual_response_stable != response_stable_count
    ):
        raise BenchmarkDashboardDataError("case totals do not match benchmark summary")
    return data


def load_benchmark_report(path: Path) -> Mapping[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkDashboardDataError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
    return validate_benchmark_report(report)


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _percent(value: object) -> str:
    return f"{float(value):.0%}"


def _milliseconds(value: object) -> str:
    return f"{float(value) * 1000:.2f} ms"


def _token_label(tokens: object) -> str:
    if tokens is None:
        return "N/A · offline run"
    token_data = _mapping(tokens, "tokens")
    return f"{float(token_data['mean_total_tokens']):.1f} average total tokens"


def _case_card(case: Mapping[str, Any], repetitions: int) -> str:
    verdict = str(case["verdict"])
    labels = {
        "consistently-passed": "Consistently passed",
        "consistently-failed": "Consistently failed",
        "variable": "Variable result",
    }
    explanations = {
        "consistently-passed": (
            f"All {repetitions} repetitions passed the quality rubric."
        ),
        "consistently-failed": (
            f"All {repetitions} repetitions failed. The behavior is repeatable, "
            "but it is still wrong."
        ),
        "variable": (
            f"The pass/fail verdict changed across {repetitions} repetitions."
        ),
    }
    expected = (
        "Answer from evidence and cite the source."
        if case["expected_behavior"] == "supported"
        else "Decline because safe supporting evidence is unavailable."
    )
    latency = case["latency"]
    return f"""
    <article class="case {verdict}" data-verdict="{verdict}">
      <header><div><p class="eyebrow">Benchmark case</p>
        <h2>{_text(case["case_id"])}</h2></div>
        <span class="pill">{labels[verdict]}</span></header>
      <p><strong>Question:</strong> {_text(case["question"])}</p>
      <p class="muted"><strong>Expected:</strong> {_text(expected)}</p>
      <div class="case-metrics">
        <div><span>Pass rate</span><strong>{_percent(case["pass_rate"])}</strong>
          <small>{case["passed_count"]} of {case["sample_count"]} repetitions passed.</small></div>
        <div><span>Verdict stability</span><strong>{"Stable" if case["stable"] else "Variable"}</strong>
          <small>{_text(explanations[verdict])}</small></div>
        <div><span>Response consistency</span><strong>{"Stable" if case["response_stable"] else "Variable"}</strong>
          <small>{case["answer_variant_count"]} answer and {case["citation_variant_count"]} citation variants.</small></div>
        <div><span>Typical latency (p50)</span><strong>{_milliseconds(latency["p50_seconds"])}</strong>
          <small>Half of this case's runs finished at or below this time.</small></div>
        <div><span>Slower-end latency (p95)</span><strong>{_milliseconds(latency["p95_seconds"])}</strong>
          <small>At least 95% finished at or below this time in this sample.</small></div>
        <div><span>Token usage</span><strong>{_text(_token_label(case["tokens"]))}</strong>
          <small>Tokens are reported only when the provider returns usage.</small></div>
      </div>
    </article>"""


def render_benchmark_dashboard(report: object) -> str:
    """Render validated repeated-run evidence as standalone HTML."""
    data = validate_benchmark_report(report)
    run = data["run"]
    summary = data["summary"]
    latency = summary["latency"]
    repetitions = int(run["repetitions"])
    cases = data["cases"]
    cards = "".join(_case_card(case, repetitions) for case in cases)
    model = run["model"] or "Offline extractive baseline"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>RAG Stability Benchmark · QA Compliance Sentry</title>
  <style>
    :root {{ --night:#071017; --panel:#101923; --line:#293644; --ink:#f4f1e8;
      --muted:#9eabb5; --mint:#65d6ad; --amber:#f1b85b; --coral:#ff7d6e; --blue:#78a8ff; }}
    * {{ box-sizing:border-box; }} html {{ background:var(--night); }}
    body {{ margin:0; color:var(--ink); font:15px/1.5 system-ui,sans-serif;
      background:radial-gradient(circle at 80% -10%,#193a50,transparent 32rem),var(--night); }}
    main {{ width:min(1160px,calc(100% - 32px)); margin:auto; padding:60px 0 80px; }}
    .hero {{ display:grid; grid-template-columns:1.5fr 1fr; gap:42px; align-items:end; }}
    .eyebrow {{ margin:0 0 8px; color:var(--mint); font:700 12px/1.2 ui-monospace,monospace;
      letter-spacing:.12em; text-transform:uppercase; }}
    h1 {{ margin:0; font-size:clamp(42px,7vw,76px); line-height:.98; letter-spacing:-.05em; }}
    .lede {{ max-width:700px; color:#c7d0d6; font-size:18px; }}
    dl {{ margin:0; display:grid; grid-template-columns:1fr 1fr; gap:15px; border-left:1px solid var(--line); padding-left:25px; }}
    dt,.metric span,.case-metrics span {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.07em; }}
    dd {{ margin:2px 0 0; font-weight:700; overflow-wrap:anywhere; }}
    .summary {{ display:grid; grid-template-columns:repeat(5,1fr); gap:13px; margin:46px 0 20px; }}
    .metric,.guide,.case {{ border:1px solid var(--line); border-radius:17px; background:#101923ed; }}
    .metric {{ padding:21px; }} .metric strong {{ display:block; margin:8px 0; font-size:32px; }}
    small,.muted {{ color:var(--muted); }}
    .guide {{ padding:24px; margin:0 0 42px; border-color:#78a8ff55; }}
    .guide h2 {{ margin:0 0 14px; }} .criteria {{ display:grid; grid-template-columns:repeat(4,1fr); gap:18px; }}
    .criteria strong,.criteria small {{ display:block; }} .criteria small {{ margin-top:5px; }}
    .toolbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; }}
    .toolbar h2 {{ margin:0; }} .filters {{ display:flex; gap:5px; }}
    button {{ color:var(--muted); background:#0b151e; border:1px solid var(--line); border-radius:999px; padding:8px 12px; cursor:pointer; }}
    button[aria-pressed="true"] {{ color:var(--night); background:var(--ink); }}
    .cases {{ display:grid; gap:16px; }} .case {{ padding:25px; border-left:3px solid var(--mint); }}
    .case.consistently-failed {{ border-left-color:var(--coral); }} .case.variable {{ border-left-color:var(--amber); }}
    .case header {{ display:flex; justify-content:space-between; gap:18px; }} .case h2 {{ margin:0; overflow-wrap:anywhere; }}
    .pill {{ align-self:start; border:1px solid var(--line); border-radius:999px; padding:6px 10px; font-size:12px; }}
    .case-metrics {{ display:grid; grid-template-columns:repeat(6,1fr); gap:1px; margin-top:20px; background:var(--line); border:1px solid var(--line); border-radius:11px; overflow:hidden; }}
    .case-metrics div {{ padding:14px; background:#0b151e; }} .case-metrics strong,.case-metrics small {{ display:block; }}
    .case-metrics strong {{ margin:5px 0; }} footer {{ margin-top:35px; color:var(--muted); text-align:center; font-size:12px; }}
    [hidden] {{ display:none!important; }}
    @media(max-width:900px) {{ .hero {{ grid-template-columns:1fr; }} dl {{ border-left:0; border-top:1px solid var(--line); padding:22px 0 0; }} .summary,.criteria {{ grid-template-columns:1fr 1fr; }} .case-metrics {{ grid-template-columns:1fr 1fr; }} }}
    @media(max-width:560px) {{ main {{ width:calc(100% - 20px); padding-top:35px; }} .summary,.criteria,.case-metrics,dl {{ grid-template-columns:1fr; }} .toolbar,.case header {{ align-items:flex-start; flex-direction:column; }} .filters {{ flex-wrap:wrap; }} }}
  </style>
</head>
<body><main>
  <section class="hero"><div><p class="eyebrow">QA Compliance Sentry · Repeated evidence</p>
    <h1>Is the result fast—and repeatable?</h1>
    <p class="lede">This benchmark repeats the same quality cases. It keeps correctness,
      consistency, latency, and token usage separate so a fast or stable failure is never called good.</p></div>
    <dl><div><dt>Provider</dt><dd>{_text(run["provider"])}</dd></div>
      <div><dt>Model</dt><dd>{_text(model)}</dd></div>
      <div><dt>Repetitions</dt><dd>{repetitions} per case</dd></div>
      <div><dt>Total samples</dt><dd>{summary["sample_count"]}</dd></div>
      <div><dt>Dataset</dt><dd>{_text(run["dataset"])}</dd></div>
      <div><dt>Created</dt><dd>{_text(run["created_at"])}</dd></div></dl></section>
  <section class="summary" aria-label="Benchmark summary">
    <article class="metric"><span>Sample pass rate</span><strong>{_percent(summary["sample_pass_rate"])}</strong><small>{summary["passed_sample_count"]} of {summary["sample_count"]} repeated case runs passed.</small></article>
    <article class="metric"><span>Verdict stability</span><strong>{_percent(summary["stability_rate"])}</strong><small>{summary["stable_case_count"]} of {summary["case_count"]} cases kept the same pass/fail result.</small></article>
    <article class="metric"><span>Response consistency</span><strong>{_percent(summary["response_stability_rate"])}</strong><small>{summary["response_stable_case_count"]} of {summary["case_count"]} cases kept the same answer text and citations.</small></article>
    <article class="metric"><span>Typical latency · p50</span><strong>{_milliseconds(latency["p50_seconds"])}</strong><small>Half of all samples completed at or below this time.</small></article>
    <article class="metric"><span>Slower-end latency · p95</span><strong>{_milliseconds(latency["p95_seconds"])}</strong><small>At least 95% completed at or below this time in this sample.</small></article>
  </section>
  <section class="guide"><p class="eyebrow">Evaluation criteria</p><h2>How to read these results</h2>
    <div class="criteria">
      <div><strong>Correctness</strong><small>A repetition passes only when every retrieval, behavior, fact, safety, and citation check passes.</small></div>
      <div><strong>Verdict stability</strong><small>A case is verdict-stable only when all {repetitions} repetitions produce the same pass/fail result. Stable does not mean correct.</small></div>
      <div><strong>Response consistency</strong><small>Exact answer text and canonical citation sets are checked separately, so hidden response changes remain visible.</small></div>
      <div><strong>Latency</strong><small>p50 describes a typical run; p95 describes the slower end. This learning baseline sets no production SLA.</small></div>
      <div><strong>Tokens</strong><small>{_text(_token_label(summary["tokens"]))}. Offline runs have no provider token bill.</small></div>
    </div></section>
  <section><div class="toolbar"><div><h2>Case-by-case stability</h2><small id="count">Showing {len(cases)} of {len(cases)}</small></div>
    <div class="filters" role="group" aria-label="Filter benchmark cases">
      <button data-filter="all" aria-pressed="true">All</button><button data-filter="consistently-passed" aria-pressed="false">Passed</button>
      <button data-filter="consistently-failed" aria-pressed="false">Failed</button><button data-filter="variable" aria-pressed="false">Variable</button>
    </div></div><div class="cases">{cards}</div></section>
  <footer>Benchmark schema v{_text(data["schema_version"])} · {_text(run["benchmark_id"])} · Nearest-rank percentiles</footer>
</main><script>(()=>{{const buttons=[...document.querySelectorAll('[data-filter]')];const cards=[...document.querySelectorAll('[data-verdict]')];const count=document.querySelector('#count');for(const button of buttons){{button.addEventListener('click',()=>{{let visible=0;for(const card of cards){{const show=button.dataset.filter==='all'||card.dataset.verdict===button.dataset.filter;card.hidden=!show;visible+=Number(show);}}for(const candidate of buttons)candidate.setAttribute('aria-pressed',String(candidate===button));count.textContent=`Showing ${{visible}} of ${{cards.length}}`;}});}}}})();</script></body></html>"""


def write_benchmark_dashboard(report_path: Path, output: Path) -> None:
    report = load_benchmark_report(report_path)
    rendered = render_benchmark_dashboard(report)
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
