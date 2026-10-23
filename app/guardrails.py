"""Deterministic boundaries around untrusted requests and model output.

These checks are deliberately narrow. They prevent common credential leaks and
obvious attempts to extract the application's private instructions; they do not
claim to classify every unsafe or misleading business request.
"""

import re
import json

from app.llm import AgentError
from app.models import Draft, Plan, Review

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:GEMINI_API_KEY|GOOGLE_API_KEY|OPENAI_API_KEY)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,})\b"),
    re.compile(r"\bAuthorization\s*:\s*Bearer\s+\S+", re.IGNORECASE),
)
_INTERNAL_REQUEST = re.compile(
    r"\b(?:reveal|print|show|disclose|dump|extract|return)\b"
    r".{0,80}\b(?:system (?:prompt|instructions?)|developer (?:prompt|instructions?)|"
    r"hidden (?:prompt|instructions?)|api key|secret key)\b",
    re.IGNORECASE | re.DOTALL,
)


def check_request(request: str) -> None:
    """Reject requests that would send credentials or target private instructions."""
    if any(ord(char) < 32 and char not in "\n\r\t" for char in request):
        raise AgentError("invalid_request", "Remove control characters from the request.", 422)
    if any(pattern.search(request) for pattern in _SECRET_PATTERNS):
        raise AgentError(
            "sensitive_input",
            "The request appears to contain a credential. Remove it before generating a document.",
            422,
        )
    if _INTERNAL_REQUEST.search(request):
        raise AgentError(
            "internal_instruction_request",
            "The document agent cannot reveal internal instructions or credentials.",
            422,
        )


def check_review(plan: Plan, review: Review) -> list[str]:
    """Require one review check per planned requirement, with no duplicate indices."""
    indices = [check.requirement_index for check in review.checks if check.requirement_index > 0]
    expected = set(range(1, len(plan.requirements) + 1))
    missing = sorted(expected - set(indices))
    duplicates = sorted({index for index in indices if indices.count(index) > 1})
    unknown = sorted(set(indices) - expected)
    issues = []
    if missing:
        issues.append("Review omitted plan requirement indices: " + ", ".join(map(str, missing)))
    if duplicates:
        issues.append("Review repeated plan requirement indices: " + ", ".join(map(str, duplicates)))
    if unknown:
        issues.append("Review referred to nonexistent plan requirement indices: " + ", ".join(map(str, unknown)))
    return issues


def check_output(plan: Plan, draft: Draft, reviews: list[Review], api_key: str) -> None:
    """Fail closed if a known credential appears anywhere in the response content."""
    content = json.dumps(
        {"plan": plan.model_dump(), "document": draft.model_dump(), "reviews": [item.model_dump() for item in reviews]},
        ensure_ascii=False,
    )
    if (api_key and api_key in content) or any(pattern.search(content) for pattern in _SECRET_PATTERNS):
        raise AgentError("sensitive_output", "Generated content contains a credential and was withheld.", 422)
