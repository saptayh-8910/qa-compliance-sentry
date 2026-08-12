"""Safe standalone dashboard for claim-level faithfulness validation."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from html import escape
from math import isfinite
from pathlib import Path
from typing import Any

from qa_assistant.faithfulness_reporting import FAITHFULNESS_REPORT_SCHEMA_VERSION

_LABELS = ("supported", "contradicted", "unsupported")


class FaithfulnessDashboardDataError(ValueError):
    """Raised when faithfulness evidence cannot be safely rendered."""


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FaithfulnessDashboardDataError(f"{location} must be an object")
    return value


def _list(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise FaithfulnessDashboardDataError(f"{location} must be an array")
    return value


def _required(value: Mapping[str, Any], fields: tuple[str, ...], location: str) -> None:
    missing = tuple(field for field in fields if field not in value)
    if missing:
        raise FaithfulnessDashboardDataError(
            f"{location} is missing required fields: {', '.join(missing)}"
        )


def _string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FaithfulnessDashboardDataError(f"{location} must be a non-empty string")
    return value


def _integer(value: object, location: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise FaithfulnessDashboardDataError(
            f"{location} must be an integer greater than or equal to {minimum}"
        )
    return value


def _rate(value: object, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FaithfulnessDashboardDataError(f"{location} must be a number")
    number = float(value)
    if not isfinite(number) or not 0 <= number <= 1:
        raise FaithfulnessDashboardDataError(f"{location} must be between 0 and 1")
    return number


def _boolean(value: object, location: str) -> bool:
    if not isinstance(value, bool):
        raise FaithfulnessDashboardDataError(f"{location} must be a boolean")
    return value


def validate_faithfulness_report(report: object) -> Mapping[str, Any]:
    """Validate every report field used by the HTML renderer."""
    data = _mapping(report, "report")
    if data.get("schema_version") != FAITHFULNESS_REPORT_SCHEMA_VERSION:
        raise FaithfulnessDashboardDataError(
            "unsupported faithfulness report schema_version "
            f"{data.get('schema_version')!r}; expected "
            f"{FAITHFULNESS_REPORT_SCHEMA_VERSION!r}"
        )
    _required(data, ("schema_version", "run", "summary", "policy", "claims"), "report")
    run = _mapping(data.get("run"), "run")
    _required(
        run,
        ("run_id", "created_at", "dataset", "judge", "label_source"),
        "run",
    )
    for field in ("run_id", "created_at", "dataset", "judge", "label_source"):
        _string(run.get(field), f"run.{field}")

    summary = _mapping(data.get("summary"), "summary")
    summary_fields = (
        "validated",
        "example_count",
        "human_supported_count",
        "human_faithfulness_rate",
        "exact_match_count",
        "accuracy",
        "unfaithful_precision",
        "unfaithful_recall",
        "unfaithful_f1",
        "false_positive_count",
        "false_negative_count",
        "confusion_matrix",
    )
    _required(summary, summary_fields, "summary")
    validated = _boolean(summary.get("validated"), "summary.validated")
    example_count = _integer(summary.get("example_count"), "summary.example_count", 1)
    human_supported = _integer(
        summary.get("human_supported_count"), "summary.human_supported_count"
    )
    exact = _integer(summary.get("exact_match_count"), "summary.exact_match_count")
    false_positive = _integer(
        summary.get("false_positive_count"), "summary.false_positive_count"
    )
    false_negative = _integer(
        summary.get("false_negative_count"), "summary.false_negative_count"
    )
    rates = {
        field: _rate(summary.get(field), f"summary.{field}")
        for field in (
            "human_faithfulness_rate",
            "accuracy",
            "unfaithful_precision",
            "unfaithful_recall",
            "unfaithful_f1",
        )
    }
    if human_supported > example_count or exact > example_count:
        raise FaithfulnessDashboardDataError("faithfulness summary counts conflict")
    if abs(rates["human_faithfulness_rate"] - human_supported / example_count) > 1e-12:
        raise FaithfulnessDashboardDataError(
            "summary.human_faithfulness_rate does not match counts"
        )
    if abs(rates["accuracy"] - exact / example_count) > 1e-12:
        raise FaithfulnessDashboardDataError("summary.accuracy does not match counts")

    matrix = _mapping(summary.get("confusion_matrix"), "summary.confusion_matrix")
    _required(matrix, _LABELS, "summary.confusion_matrix")
    matrix_total = 0
    matrix_exact = 0
    for human in _LABELS:
        row = _mapping(matrix.get(human), f"summary.confusion_matrix.{human}")
        _required(row, _LABELS, f"summary.confusion_matrix.{human}")
        for predicted in _LABELS:
            count = _integer(
                row.get(predicted),
                f"summary.confusion_matrix.{human}.{predicted}",
            )
            matrix_total += count
            if human == predicted:
                matrix_exact += count
    if matrix_total != example_count or matrix_exact != exact:
        raise FaithfulnessDashboardDataError(
            "summary.confusion_matrix does not match summary counts"
        )

    policy = _mapping(data.get("policy"), "policy")
    _required(
        policy,
        (
            "minimum_accuracy",
            "minimum_unfaithful_recall",
            "maximum_false_negatives",
        ),
        "policy",
    )
    minimum_accuracy = _rate(policy.get("minimum_accuracy"), "policy.minimum_accuracy")
    minimum_recall = _rate(
        policy.get("minimum_unfaithful_recall"),
        "policy.minimum_unfaithful_recall",
    )
    maximum_false_negatives = _integer(
        policy.get("maximum_false_negatives"),
        "policy.maximum_false_negatives",
    )
    expected_validated = (
        rates["accuracy"] >= minimum_accuracy
        and rates["unfaithful_recall"] >= minimum_recall
        and false_negative <= maximum_false_negatives
    )
    if validated != expected_validated:
        raise FaithfulnessDashboardDataError(
            "summary.validated does not match validation policy"
        )

    claims = _list(data.get("claims"), "claims")
    if len(claims) != example_count:
        raise FaithfulnessDashboardDataError(
            "summary.example_count does not match claims"
        )
    actual_exact = 0
    actual_supported = 0
    actual_false_positive = 0
    actual_false_negative = 0
    actual_true_positive = 0
    actual_matrix = {
        human: {predicted: 0 for predicted in _LABELS} for human in _LABELS
    }
    claim_ids: set[str] = set()
    for index, value in enumerate(claims):
        location = f"claims[{index}]"
        claim = _mapping(value, location)
        _required(
            claim,
            (
                "claim_id",
                "evidence",
                "claim",
                "human_label",
                "judge_label",
                "correct",
                "human_explanation",
            ),
            location,
        )
        claim_id = _string(claim.get("claim_id"), f"{location}.claim_id")
        if claim_id in claim_ids:
            raise FaithfulnessDashboardDataError(f"duplicate claim_id {claim_id!r}")
        claim_ids.add(claim_id)
        for field in ("evidence", "claim", "human_explanation"):
            _string(claim.get(field), f"{location}.{field}")
        human = claim.get("human_label")
        predicted = claim.get("judge_label")
        if human not in _LABELS or predicted not in _LABELS:
            raise FaithfulnessDashboardDataError(
                f"{location} labels must be supported, contradicted, or unsupported"
            )
        correct = _boolean(claim.get("correct"), f"{location}.correct")
        if correct != (human == predicted):
            raise FaithfulnessDashboardDataError(
                f"{location}.correct does not match its labels"
            )
        actual_exact += int(correct)
        actual_supported += int(human == "supported")
        actual_false_positive += int(human == "supported" and predicted != "supported")
        actual_false_negative += int(human != "supported" and predicted == "supported")
        actual_true_positive += int(human != "supported" and predicted != "supported")
        actual_matrix[human][predicted] += 1
    if (
        actual_exact != exact
        or actual_supported != human_supported
        or actual_false_positive != false_positive
        or actual_false_negative != false_negative
    ):
        raise FaithfulnessDashboardDataError("claim totals do not match summary")
    if actual_matrix != matrix:
        raise FaithfulnessDashboardDataError(
            "summary.confusion_matrix does not match claim labels"
        )
    predicted_unfaithful = actual_true_positive + actual_false_positive
    human_unfaithful = actual_true_positive + actual_false_negative
    expected_precision = (
        actual_true_positive / predicted_unfaithful if predicted_unfaithful else 0.0
    )
    expected_recall = (
        actual_true_positive / human_unfaithful if human_unfaithful else 0.0
    )
    expected_f1 = (
        2
        * expected_precision
        * expected_recall
        / (expected_precision + expected_recall)
        if expected_precision + expected_recall
        else 0.0
    )
    expected_rates = {
        "unfaithful_precision": expected_precision,
        "unfaithful_recall": expected_recall,
        "unfaithful_f1": expected_f1,
    }
    for field, expected in expected_rates.items():
        if abs(rates[field] - expected) > 1e-12:
            raise FaithfulnessDashboardDataError(
                f"summary.{field} does not match claim labels"
            )
    return data


def load_faithfulness_report(path: Path) -> Mapping[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FaithfulnessDashboardDataError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
    return validate_faithfulness_report(data)


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _percent(value: object) -> str:
    return f"{float(value):.0%}"


def _claim_card(claim: Mapping[str, Any]) -> str:
    correct = bool(claim["correct"])
    status = "correct" if correct else "incorrect"
    return f"""
    <article class="claim {status}" data-status="{status}"
      data-human-label="{_text(claim["human_label"])}">
      <header><div><p class="eyebrow">Human-labelled claim</p>
        <h2>{_text(claim["claim_id"])}</h2></div>
        <span class="pill">{"Agreement" if correct else "Disagreement"}</span></header>
      <div class="claim-grid">
        <section><h3>Evidence</h3><blockquote>{_text(claim["evidence"])}</blockquote></section>
        <section><h3>Claim being judged</h3><blockquote>{_text(claim["claim"])}</blockquote></section>
      </div>
      <div class="labels">
        <span>Human label <strong>{_text(claim["human_label"])}</strong></span>
        <span>Judge label <strong>{_text(claim["judge_label"])}</strong></span>
      </div>
      <p class="explanation"><strong>Why the human labelled it this way:</strong>
        {_text(claim["human_explanation"])}</p>
    </article>"""


def render_faithfulness_dashboard(report: object) -> str:
    """Render validated faithfulness evidence as standalone HTML."""
    data = validate_faithfulness_report(report)
    run = data["run"]
    summary = data["summary"]
    policy = data["policy"]
    claims = data["claims"]
    cards = "".join(_claim_card(claim) for claim in claims)
    validation_label = (
        "Validated on this dataset" if summary["validated"] else "Not validated"
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Faithfulness Validation · QA Compliance Sentry</title>
<style>
:root{{--night:#071017;--panel:#101923;--line:#293644;--ink:#f4f1e8;--muted:#9eabb5;
--mint:#65d6ad;--coral:#ff7d6e;--blue:#78a8ff;--amber:#f1b85b}}
*{{box-sizing:border-box}}html{{background:var(--night)}}body{{margin:0;color:var(--ink);
font:15px/1.5 system-ui,sans-serif;background:radial-gradient(circle at 82% -8%,#193b51,transparent 32rem),var(--night)}}
main{{width:min(1160px,calc(100% - 32px));margin:auto;padding:60px 0 80px}}
.hero{{display:grid;grid-template-columns:1.55fr 1fr;gap:42px;align-items:end}}
.eyebrow{{margin:0 0 8px;color:var(--mint);font:700 12px/1.2 ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase}}
h1{{margin:0;font-size:clamp(43px,7vw,78px);line-height:.97;letter-spacing:-.05em}}
.lede{{max-width:720px;color:#c7d0d6;font-size:18px}}dl{{margin:0;display:grid;grid-template-columns:1fr 1fr;gap:15px;border-left:1px solid var(--line);padding-left:25px}}
dt,.metric span,.labels span{{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.07em}}dd{{margin:2px 0 0;font-weight:700;overflow-wrap:anywhere}}
.summary{{display:grid;grid-template-columns:repeat(5,1fr);gap:13px;margin:46px 0 20px}}
.metric,.guide,.claim{{border:1px solid var(--line);border-radius:17px;background:#101923ed}}
.metric{{padding:20px}}.metric strong{{display:block;margin:7px 0;font-size:31px}}small,.muted{{color:var(--muted)}}
.guide{{padding:24px;margin-bottom:42px;border-color:#78a8ff55}}.guide h2{{margin:0 0 14px}}.criteria{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}.criteria strong,.criteria small{{display:block}}.criteria small{{margin-top:5px}}
.toolbar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:15px}}.toolbar h2{{margin:0}}.filters{{display:flex;gap:5px;flex-wrap:wrap}}
button{{color:var(--muted);background:#0b151e;border:1px solid var(--line);border-radius:999px;padding:8px 12px;cursor:pointer}}button[aria-pressed="true"]{{color:var(--night);background:var(--ink)}}
.claims{{display:grid;gap:16px}}.claim{{padding:25px;border-left:3px solid var(--mint)}}.claim.incorrect{{border-left-color:var(--coral)}}.claim header{{display:flex;justify-content:space-between;gap:18px}}.claim h2{{margin:0;overflow-wrap:anywhere}}.pill{{align-self:start;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px}}
.claim-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px}}h3{{margin:0 0 8px;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}}blockquote{{margin:0;padding:15px 17px;background:#0a131b;border-left:2px solid var(--blue);border-radius:0 9px 9px 0;white-space:pre-wrap;overflow-wrap:anywhere}}
.labels{{display:flex;gap:20px;margin-top:16px}}.labels strong{{display:block;color:var(--ink);font-size:14px;text-transform:none;letter-spacing:0}}.explanation{{margin:14px 0 0;color:var(--muted)}}
footer{{margin-top:35px;color:var(--muted);text-align:center;font-size:12px}}[hidden]{{display:none!important}}
@media(max-width:900px){{.hero,.claim-grid{{grid-template-columns:1fr}}dl{{border-left:0;border-top:1px solid var(--line);padding:22px 0 0}}.summary{{grid-template-columns:1fr 1fr}}.criteria{{grid-template-columns:1fr}}}}
@media(max-width:560px){{main{{width:calc(100% - 20px);padding-top:35px}}.summary,dl{{grid-template-columns:1fr}}.toolbar,.claim header{{align-items:flex-start;flex-direction:column}}.labels{{flex-direction:column}}}}
</style></head><body><main>
<section class="hero"><div><p class="eyebrow">QA Compliance Sentry · Human ground truth</p>
<h1>Can this judge detect unsupported claims?</h1>
<p class="lede">A candidate judge is compared with human-labelled claims before its scores are trusted. Supported, contradicted, and unsupported are separate labels; dangerous misses stay visible.</p></div>
<dl><div><dt>Status</dt><dd>{_text(validation_label)}</dd></div><div><dt>Judge</dt><dd>{_text(run["judge"])}</dd></div><div><dt>Dataset</dt><dd>{_text(run["dataset"])}</dd></div><div><dt>Human labels</dt><dd>{summary["example_count"]} claims</dd></div><div><dt>Label source</dt><dd>Human-authored</dd></div><div><dt>Created</dt><dd>{_text(run["created_at"])}</dd></div></dl></section>
<section class="summary" aria-label="Faithfulness validation summary">
<article class="metric"><span>Exact label accuracy</span><strong>{_percent(summary["accuracy"])}</strong><small>{summary["exact_match_count"]} of {summary["example_count"]} three-way labels matched humans.</small></article>
<article class="metric"><span>Unfaithful precision</span><strong>{_percent(summary["unfaithful_precision"])}</strong><small>When flagged, how often was the claim truly contradicted or unsupported?</small></article>
<article class="metric"><span>Unfaithful recall</span><strong>{_percent(summary["unfaithful_recall"])}</strong><small>Of all human-labelled unfaithful claims, how many were caught?</small></article>
<article class="metric"><span>Unfaithful F1</span><strong>{_percent(summary["unfaithful_f1"])}</strong><small>One balance of unfaithful precision and recall.</small></article>
<article class="metric"><span>False negatives</span><strong>{summary["false_negative_count"]}</strong><small>Dangerous misses: unfaithful claims incorrectly called supported.</small></article>
</section>
<section class="guide"><p class="eyebrow">Evaluation criteria</p><h2>What must be true before this judge is accepted?</h2>
<div class="criteria"><div><strong>Accuracy ≥ {_percent(policy["minimum_accuracy"])}</strong><small>The exact supported, contradicted, or unsupported label must agree with humans.</small></div><div><strong>Unfaithful recall ≥ {_percent(policy["minimum_unfaithful_recall"])}</strong><small>The judge must catch nearly every contradicted or unsupported claim.</small></div><div><strong>False negatives ≤ {policy["maximum_false_negatives"]}</strong><small>No dangerous unfaithful claim may be accepted as supported in this dataset.</small></div></div>
<p class="muted"><strong>Scope:</strong> “Validated” means this candidate passed these thresholds on this small, version-controlled dataset. It does not prove universal semantic understanding.</p></section>
<section><div class="toolbar"><div><h2>Claim-by-claim evidence</h2><small id="count">Showing {len(claims)} of {len(claims)}</small></div><div class="filters" role="group" aria-label="Filter claims">
<button data-filter="all" aria-pressed="true">All</button><button data-filter="supported" aria-pressed="false">Human: supported</button><button data-filter="contradicted" aria-pressed="false">Human: contradicted</button><button data-filter="unsupported" aria-pressed="false">Human: unsupported</button><button data-filter="incorrect" aria-pressed="false">Judge errors</button></div></div><div class="claims">{cards}</div></section>
<footer>Faithfulness schema v{_text(data["schema_version"])} · {_text(run["run_id"])} · Human labels remain the authority</footer>
</main><script>(()=>{{const buttons=[...document.querySelectorAll('[data-filter]')];const cards=[...document.querySelectorAll('[data-status]')];const count=document.querySelector('#count');for(const button of buttons){{button.addEventListener('click',()=>{{let visible=0;const filter=button.dataset.filter;for(const card of cards){{const show=filter==='all'||card.dataset.status===filter||card.dataset.humanLabel===filter;card.hidden=!show;visible+=Number(show)}}for(const candidate of buttons)candidate.setAttribute('aria-pressed',String(candidate===button));count.textContent=`Showing ${{visible}} of ${{cards.length}}`}})}}}})();</script></body></html>"""


def write_faithfulness_dashboard(report_path: Path, output: Path) -> None:
    report = load_faithfulness_report(report_path)
    rendered = render_faithfulness_dashboard(report)
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
