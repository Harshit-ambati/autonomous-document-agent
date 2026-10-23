"""Evaluate saved real runs or make fresh calls to a running local API.

Recorded mode makes no model calls. Live mode calls /agent for each case and
downloads the resulting Word file; it may consume provider quota.
"""

import argparse
import io
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

import httpx
from docx import Document
from pydantic import ValidationError

from app.models import AgentResponse

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))


@dataclass
class Check:
    name: str
    passed: bool
    evidence: str


def add(checks: list[Check], name: str, passed: bool, evidence: str) -> None:
    checks.append(Check(name, bool(passed), evidence))


def document_text(response: AgentResponse) -> str:
    draft = response.document
    values = [draft.title, draft.summary, *draft.assumptions, *draft.conflicts]
    for section in draft.sections:
        values.extend([section.heading, *section.paragraphs, *section.bullets])
        for table in section.tables:
            values.extend([table.caption, *table.columns])
            values.extend(cell for row in table.rows for cell in row)
    return " ".join(values).lower()


def evaluate(case: dict, payload: dict, docx_bytes: bytes, *, require_output_guardrail: bool = False) -> list[Check]:
    checks: list[Check] = []
    try:
        response = AgentResponse.model_validate(payload)
        UUID(response.run_id)
    except (ValidationError, ValueError, TypeError) as exc:
        add(checks, "response contract", False, f"Invalid structured response: {type(exc).__name__}")
        return checks
    add(checks, "response contract", True, "Typed response and UUID are valid")

    plan = response.plan
    add(
        checks,
        "task outputs",
        len(response.document.sections) == len(plan.tasks),
        f"{len(response.document.sections)} sections for {len(plan.tasks)} tasks",
    )
    add(
        checks,
        "request decomposition",
        len(plan.requirements) >= case["minimum_requirements"],
        f"{len(plan.requirements)} requirements and {len(plan.tasks)} ordered tasks",
    )
    task_tools = [task.tool for task in plan.tasks]
    trace_tools = [event.tool for event in response.trace]
    task_cursor = iter(trace_tools)
    tasks_in_order = all(any(tool == task_tool for tool in task_cursor) for task_tool in task_tools)
    trace_ok = (
        tasks_in_order
        and "planner" in trace_tools
        and "self_check" in trace_tools
        and "render_docx" in trace_tools
        and all(event.status == "completed" for event in response.trace)
    )
    if require_output_guardrail:
        trace_ok = trace_ok and "output_guardrail" in trace_tools
    add(checks, "completed execution trace", trace_ok, ", ".join(trace_tools))

    final_review = response.reviews[-1] if response.reviews else None
    indices = [item.requirement_index for item in final_review.checks if item.requirement_index > 0] if final_review else []
    review_ok = bool(
        final_review
        and final_review.passed
        and not final_review.issues
        and all(item.satisfied for item in final_review.checks)
        and sorted(indices) == list(range(1, len(plan.requirements) + 1))
    )
    add(checks, "self-check coverage", review_ok, f"{len(indices)}/{len(plan.requirements)} indexed checks")

    try:
        word = Document(io.BytesIO(docx_bytes))
        paragraph_text = " ".join(paragraph.text for paragraph in word.paragraphs)
        word_count = len(paragraph_text.split())
        headings = [re.sub(r"[^\w\s]", " ", section.heading).strip().lower() for section in response.document.sections]
        rendered = " ".join(paragraph_text.lower().split())
        heading_count = sum(" ".join(heading.split()) in rendered for heading in headings)
        add(
            checks,
            "Word artifact",
            word_count >= case["minimum_document_words"] and heading_count == len(headings),
            f"{word_count} paragraph words; {heading_count}/{len(headings)} section headings found",
        )
        expected_paragraphs = [
            response.document.summary,
            *response.document.assumptions,
            *response.document.conflicts,
            *(text for section in response.document.sections for text in [*section.paragraphs, *section.bullets]),
        ]
        rendered_paragraphs = {paragraph.text for paragraph in word.paragraphs}
        matched_paragraphs = sum(text in rendered_paragraphs for text in expected_paragraphs)
        expected_cells = [
            cell
            for section in response.document.sections
            for table in section.tables
            for row in table.rows
            for cell in row
        ]
        rendered_cells = {cell.text for table in word.tables for row in table.rows for cell in row.cells}
        matched_cells = sum(cell in rendered_cells for cell in expected_cells)
        parity = matched_paragraphs == len(expected_paragraphs) and matched_cells == len(expected_cells)
        add(
            checks,
            "JSON/Word content parity",
            parity,
            f"{matched_paragraphs}/{len(expected_paragraphs)} paragraphs; {matched_cells}/{len(expected_cells)} table cells",
        )
    except Exception as exc:
        add(checks, "Word artifact", False, f"Cannot read .docx: {type(exc).__name__}")

    content = document_text(response)
    for concept in case["required_concepts"]:
        all_terms = concept.get("all", [])
        any_terms = concept.get("any", [])
        present = all(term.lower() in content for term in all_terms) and (
            not any_terms or any(term.lower() in content for term in any_terms)
        )
        add(checks, concept["name"], present, "Concept terms present" if present else "Required concept terms missing")

    expected_budget = case["budget"]
    budget_tasks = [task for task in plan.tasks if task.tool == "calculate_budget"]
    if expected_budget is None:
        add(checks, "no unrequested budget", not budget_tasks, f"{len(budget_tasks)} budget tasks")
    else:
        try:
            budget_task = budget_tasks[0]
            quantities = [Decimal(item.quantity) for item in budget_task.cost_items]
            rates = [Decimal(item.unit_cost) for item in budget_task.cost_items]
            computed = sum(quantity * rate for quantity, rate in zip(quantities, rates))
            budget_sections = [
                section for task, section in zip(plan.tasks, response.document.sections) if task.tool == "calculate_budget"
            ]
            total_cell = budget_sections[0].tables[0].rows[-1][-1].replace(",", "")
            passed = (
                len(budget_tasks) == 1
                and budget_task.currency == expected_budget["currency"]
                and sum(quantities) == Decimal(expected_budget["engineer_days"])
                and all(rate == Decimal(expected_budget["daily_rate"]) for rate in rates)
                and computed == Decimal(expected_budget["total"])
                and Decimal(total_cell) == computed
            )
            add(checks, "exact engineering estimate", passed, f"{budget_task.currency} {total_cell} from {sum(quantities)} engineer-days")
        except (IndexError, InvalidOperation, AttributeError, TypeError):
            add(checks, "exact engineering estimate", False, "Missing or invalid budget calculation")
        absolute_guarantee = bool(re.search(r"(?:guarantee[ds]?|promise[ds]?)\s+(?:of\s+)?zero defects", content))
        add(checks, "no absolute defect guarantee", not absolute_guarantee, "No unqualified zero-defect promise found")
    return checks


def load_recorded(case: dict, fixture_dir: Path) -> tuple[dict, bytes]:
    stem = case["id"]
    return (
        json.loads((fixture_dir / f"{stem}.json").read_text(encoding="utf-8")),
        (fixture_dir / f"{stem}.docx").read_bytes(),
    )


def run_live(case: dict, base_url: str) -> tuple[dict, bytes]:
    request = json.loads((ROOT / case["request_file"]).read_text(encoding="utf-8"))
    with httpx.Client(base_url=base_url, timeout=360) as client:
        result = client.post("/agent", json=request)
        result.raise_for_status()
        payload = result.json()
        artifact = client.get(payload["download_url"])
        artifact.raise_for_status()
    return payload, artifact.content


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("recorded", "live"), default="recorded")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "evals" / "fixtures")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", type=Path, default=ROOT / "outputs" / "evals" / "report.json")
    args = parser.parse_args()
    report = {"source": args.source, "created_utc": datetime.now(timezone.utc).isoformat(), "cases": []}
    for case in CASES:
        try:
            payload, docx_bytes = (
                load_recorded(case, args.fixtures) if args.source == "recorded" else run_live(case, args.base_url)
            )
            checks = evaluate(case, payload, docx_bytes, require_output_guardrail=args.source == "live")
            if args.source == "live":
                artifacts = args.report.parent / "live_artifacts"
                artifacts.mkdir(parents=True, exist_ok=True)
                (artifacts / f"{case['id']}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
                (artifacts / f"{case['id']}.docx").write_bytes(docx_bytes)
        except (OSError, ValueError, httpx.HTTPError, KeyError) as exc:
            checks = [Check("case execution", False, f"{type(exc).__name__}: {str(exc)[:180]}")]
        passed = all(check.passed for check in checks)
        report["cases"].append({"id": case["id"], "passed": passed, "checks": [asdict(check) for check in checks]})
        print(f"{case['id']}: {'PASS' if passed else 'FAIL'} ({sum(check.passed for check in checks)}/{len(checks)} checks)")
        for check in checks:
            if not check.passed:
                print(f"  - {check.name}: {check.evidence}")
    report["passed"] = all(case["passed"] for case in report["cases"])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {args.report}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
