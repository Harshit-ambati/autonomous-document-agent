"""Offline contract tests. Scripted model replies are NOT live agent evidence."""

import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from docx import Document
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agent import Agent, calculate_budget
from app.config import Settings
from app.llm import AgentError, GeminiModel, provider_schema
from app.main import create_app
from app.models import Draft, Plan, Review, Section, Task


def section(heading="Objectives"):
    return Section(
        heading=heading,
        paragraphs=["HR coordinates onboarding and tracks completion at the end of week four."],
        bullets=[],
        tables=[],
    )


def plan():
    return Plan(
        title="Employee onboarding proposal",
        document_type="Proposal",
        overview="Approve a four week onboarding programme.",
        requirements=["Include objectives"],
        assumptions=["The start date is unconfirmed"],
        conflicts=[],
        tasks=[
            Task(
                id="task_1",
                title="Objectives",
                tool="draft_section",
                instructions="Define measurable onboarding goals",
                depends_on=[],
                cost_items=[],
                currency="",
            )
        ],
    )


def review(passed=True):
    return Review(
        passed=passed,
        checks=[
            {
                "requirement_index": 1,
                "requirement": "Include objectives",
                "satisfied": passed,
                "evidence": "Objectives section reviewed",
            }
        ],
        issues=[] if passed else ["Add an explicit measurable objective"],
    )


class ScriptedModel:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def generate(self, instruction, context, schema):
        self.calls.append((instruction, context, schema))
        value = self.replies.pop(0)
        if isinstance(value, Exception):
            raise value
        assert isinstance(value, schema)
        return value


def test_end_to_end_api_and_docx(tmp_path):
    model = ScriptedModel([plan(), section(), review()])
    with TestClient(create_app(Settings(output_dir=tmp_path), model)) as client:
        response = client.post("/agent", json={"request": "Create an onboarding proposal"})
        assert response.status_code == 200
        data = response.json()
        assert [e["tool"] for e in data["trace"]] == ["planner", "draft_section", "self_check", "render_docx"]
        assert all(e["status"] == "completed" for e in data["trace"])
        artifact = client.get(data["download_url"])
        assert artifact.status_code == 200 and artifact.content.startswith(b"PK")
        assert "wordprocessingml" in artifact.headers["content-type"]
        assert client.get(data["trace_url"]).json()["run_id"] == data["run_id"]
    doc = Document(tmp_path / f"{data['run_id']}.docx")
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Employee onboarding proposal" in text and "start date is unconfirmed" in text
    assert "HR coordinates" in text
    assert not doc.styles.element.xpath(".//w:pBdr")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"request": " "},
        {"request": "short"},
        {"request": "x" * 12001},
        {"request": "A valid request", "extra": True},
    ],
)
def test_request_validation(tmp_path, body):
    model = ScriptedModel([])
    with TestClient(create_app(Settings(output_dir=tmp_path), model)) as client:
        assert client.post("/agent", json=body).status_code == 422
    assert not model.calls


@pytest.mark.parametrize(
    "change",
    [
        {"depends_on": ["task_2"]},
        {"tool": "execute_python"},
        {"tool": "calculate_budget", "cost_items": [], "currency": "INR"},
    ],
)
def test_bad_plan_is_rejected(change):
    data = plan().model_dump()
    data["tasks"][0].update(change)
    with pytest.raises(ValidationError):
        Plan.model_validate(data)


def test_budget_tool_exact_arithmetic():
    task = Task(
        id="task_1",
        title="Engineering cost",
        tool="calculate_budget",
        instructions="Calculate provided rates",
        depends_on=[],
        currency="INR",
        cost_items=[{"description": "Engineering days", "quantity": "20", "unit_cost": "6000"}],
    )
    result = calculate_budget(task)
    assert result.tables[0].rows[-1][-1] == "120,000.00"


def test_provider_schema_avoids_state_explosion_but_local_bounds_remain():
    schema = provider_schema(Plan)
    serialized = json.dumps(schema)
    assert "maxLength" not in serialized and "maxItems" not in serialized and '"pattern"' not in serialized
    assert schema["required"] and schema["$defs"]["Task"]["properties"]["tool"]["enum"]
    assert "title" in schema["properties"]
    data = plan().model_dump()
    data["title"] = "x" * 161
    with pytest.raises(ValidationError):
        Plan.model_validate(data)
    assert provider_schema(Review, retain_array_limits=True)["properties"]["checks"]["maxItems"] == 30


def test_self_check_repairs_once(tmp_path):
    original = plan()
    revised = Draft(
        title=original.title,
        summary=original.overview,
        assumptions=original.assumptions,
        conflicts=[],
        sections=[section("Measurable objectives")],
    )
    model = ScriptedModel([original, section(), review(False), revised, review()])
    result = asyncio.run(Agent(model, tmp_path, "test-only").run("Write an onboarding proposal", str(uuid4())))
    assert len(result.reviews) == 2 and result.reviews[-1].passed
    assert "revision" in [e.tool for e in result.trace]
    assert result.document.sections[0].heading == "Measurable objectives"


def test_quality_failure_does_not_release_document(tmp_path):
    p = plan()
    revised = Draft(title=p.title, summary=p.overview, assumptions=[], conflicts=[], sections=[section()])
    model = ScriptedModel([p, section(), review(False), revised, review(False)])
    with TestClient(create_app(Settings(output_dir=tmp_path), model)) as client:
        response = client.post("/agent", json={"request": "Create an onboarding proposal"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "quality_check_failed"
    assert response.json()["error"]["details"]["reviews"][-1]["issues"]
    assert not list(tmp_path.glob("*.docx"))


def test_requirement_coverage_uses_indices_instead_of_literal_wording(tmp_path):
    paraphrased = Review(
        passed=True,
        checks=[
            {
                "requirement_index": 1,
                "requirement": "Onboarding objectives are present",
                "satisfied": True,
                "evidence": "The objectives section defines the onboarding goal",
            }
        ],
        issues=[],
    )
    model = ScriptedModel([plan(), section(), paraphrased])
    result = asyncio.run(Agent(model, tmp_path, "test-only").run("Write an onboarding proposal", str(uuid4())))
    assert result.reviews[-1].passed


def test_dependency_outputs_and_authoritative_budget_survive_revision(tmp_path):
    p = plan()
    budget = Task(
        id="task_1",
        title="Engineering estimate",
        tool="calculate_budget",
        instructions="Calculate engineering-only costs",
        depends_on=[],
        cost_items=[{"description": "Engineering days", "quantity": "20", "unit_cost": "6000"}],
        currency="INR",
    )
    draft_task = p.tasks[0].model_copy(update={"id": "task_2", "depends_on": ["task_1"]})
    p.tasks = [budget, draft_task]
    modified_budget = section("Incorrect model-revised cost")
    revised = Draft(
        title=p.title,
        summary=p.overview,
        assumptions=p.assumptions,
        conflicts=[],
        sections=[modified_budget, section()],
    )
    model = ScriptedModel([p, section(), review(False), revised, review()])
    result = asyncio.run(
        Agent(model, tmp_path, "test-only").run("Estimate engineering costs and write a plan", str(uuid4()))
    )
    assert model.calls[1][1]["dependency_outputs"]["task_1"]["tables"][0]["rows"][-1][-1] == "120,000.00"
    assert result.document.sections[0].tables[0].rows[-1][-1] == "120,000.00"
    assert model.calls[-1][1]["draft"]["sections"][0]["heading"] == budget.title


def test_review_cannot_omit_a_plan_requirement(tmp_path):
    p = plan()
    incomplete = Review(
        passed=True,
        checks=[
            {"requirement_index": 0, "requirement": "Some other check", "satisfied": True, "evidence": "Looks good"}
        ],
        issues=[],
    )
    revised = Draft(title=p.title, summary=p.overview, assumptions=p.assumptions, conflicts=[], sections=[section()])
    model = ScriptedModel([p, section(), incomplete, revised, incomplete.model_copy(deep=True)])
    with pytest.raises(AgentError, match="did not pass"):
        asyncio.run(Agent(model, tmp_path, "test-only").run("Write an onboarding proposal", str(uuid4())))
    assert not list(tmp_path.glob("*.docx"))


def test_missing_key_is_actionable(tmp_path):
    with TestClient(create_app(Settings(output_dir=tmp_path))) as client:
        response = client.post("/agent", json={"request": "Create an onboarding proposal"})
        assert client.get("/health").json()["model_configured"] is False
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_not_configured"
    assert response.json()["trace"][0]["status"] == "failed"


def test_download_paths_are_uuid_only(tmp_path):
    with TestClient(create_app(Settings(output_dir=tmp_path), ScriptedModel([]))) as client:
        assert client.get("/documents/not-a-uuid").status_code == 422
        assert client.get(f"/documents/{uuid4()}").status_code == 404
        assert client.get(f"/runs/{uuid4()}").status_code == 404


def test_run_deadline(tmp_path):
    class SlowModel:
        async def generate(self, *args):
            await asyncio.sleep(1)

    with TestClient(create_app(Settings(output_dir=tmp_path, agent_timeout=0.01), SlowModel())) as client:
        response = client.post("/agent", json={"request": "Create an onboarding proposal"})
    assert response.status_code == 504
    assert not list(tmp_path.glob("*.docx"))


def test_table_rows_must_match_headers():
    from app.models import Table

    with pytest.raises(ValidationError):
        Table(caption="Timeline", columns=["Week", "Owner"], rows=[["Week one"]])


@pytest.mark.parametrize("status,expected_calls", [(200, 1), (429, 2), (401, 1)])
def test_gemini_adapter_status_handling(tmp_path, monkeypatch, status, expected_calls):
    calls = []

    async def no_sleep(*args):
        pass

    monkeypatch.setattr("app.llm.asyncio.sleep", no_sleep)

    def handle(request):
        calls.append(request)
        assert request.headers["x-goog-api-key"] == "test-secret"
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(
            status,
            json={
                "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": section().model_dump_json()}]}}]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await GeminiModel(client, Settings(api_key="test-secret", llm_min_interval=0)).generate(
                "Draft", {}, Section
            )

    if status == 200:
        assert asyncio.run(run()).heading == "Objectives"
    else:
        with pytest.raises(AgentError) as exc:
            asyncio.run(run())
        assert "test-secret" not in str(exc.value)
    assert len(calls) == expected_calls


def test_gemini_repairs_invalid_json_once():
    calls = []

    def handle(request):
        calls.append(request)
        content = "not json" if len(calls) == 1 else section().model_dump_json()
        return httpx.Response(
            200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": content}]}}]}
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await GeminiModel(client, Settings(api_key="test-secret", llm_min_interval=0)).generate(
                "Draft", {}, Section
            )

    assert asyncio.run(run()).heading == "Objectives"
    assert len(calls) == 2
