"""Validated contracts between the API, planner, tools, and reviewer."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Cell = Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentRequest(Contract):
    request: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=12000)]


class CostItem(Contract):
    description: Label
    quantity: Annotated[str, StringConstraints(pattern=r"^\d{1,9}(\.\d{1,4})?$")]
    unit_cost: Annotated[str, StringConstraints(pattern=r"^\d{1,9}(\.\d{1,4})?$")]


class Task(Contract):
    id: Annotated[str, StringConstraints(pattern=r"^task_[1-6]$")]
    title: Label
    tool: Literal["draft_section", "calculate_budget"]
    instructions: Text
    depends_on: list[str] = Field(max_length=5)
    cost_items: list[CostItem] = Field(max_length=10)
    currency: Annotated[str, StringConstraints(max_length=16)]

    @model_validator(mode="after")
    def valid_tool_arguments(self):
        if self.tool == "calculate_budget" and (not self.cost_items or not self.currency.strip()):
            raise ValueError("Budget tasks require cost_items and a currency")
        if self.tool == "draft_section" and self.cost_items:
            raise ValueError("Draft tasks cannot contain budget tool arguments")
        return self


class Plan(Contract):
    title: Label
    document_type: Label
    overview: Text
    requirements: list[Text] = Field(min_length=1, max_length=15)
    assumptions: list[Text] = Field(max_length=12)
    conflicts: list[Text] = Field(max_length=10)
    tasks: list[Task] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def ordered_dependencies(self):
        seen = set()
        for task in self.tasks:
            if task.id in seen or any(dep not in seen for dep in task.depends_on):
                raise ValueError("Task IDs must be unique; dependencies must refer to earlier tasks")
            seen.add(task.id)
        return self


class Table(Contract):
    caption: Label
    columns: list[Label] = Field(min_length=2, max_length=5)
    rows: list[list[Cell]] = Field(min_length=1, max_length=15)

    @model_validator(mode="after")
    def rectangular(self):
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("Every table row must match the column count")
        return self


class Section(Contract):
    heading: Label
    paragraphs: list[Text] = Field(max_length=5)
    bullets: list[Text] = Field(max_length=10)
    tables: list[Table] = Field(max_length=2)

    @model_validator(mode="after")
    def has_content(self):
        if not (self.paragraphs or self.bullets or self.tables):
            raise ValueError("A section must contain substantive content")
        return self


class Draft(Contract):
    title: Label
    summary: Text
    assumptions: list[Text] = Field(max_length=12)
    conflicts: list[Text] = Field(max_length=10)
    sections: list[Section] = Field(min_length=1, max_length=6)


class Check(Contract):
    requirement_index: int = Field(
        ge=0, le=15, description="1-based index in plan.requirements; 0 for an additional check"
    )
    requirement: Text
    satisfied: bool
    evidence: Text


class Review(Contract):
    passed: bool
    checks: list[Check] = Field(min_length=1, max_length=30)
    issues: list[Text] = Field(max_length=15)

    @model_validator(mode="after")
    def consistent(self):
        if self.passed and (self.issues or any(not check.satisfied for check in self.checks)):
            raise ValueError("A passing review cannot contain unmet checks or issues")
        if not self.passed and not self.issues:
            raise ValueError("A failed review must explain what to fix")
        return self


class Event(Contract):
    step: str
    tool: str
    status: Literal["running", "completed", "failed"]
    detail: str
    duration_ms: int = 0


class AgentResponse(Contract):
    run_id: str
    status: Literal["completed"] = "completed"
    summary: str
    plan: Plan
    document: Draft
    reviews: list[Review]
    trace: list[Event]
    download_url: str
    trace_url: str
    model: str
    elapsed_ms: int
