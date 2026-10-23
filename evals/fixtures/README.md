# Recorded evaluation fixtures

`standard` and `complex` are snapshots of the two successful live Gemini runs described in `docs/VALIDATION.md`. They let reviewers run deterministic checks without an API key or model quota. These historical traces predate the later output credential guardrail; the optional `--source live` mode requires that step in fresh traces.

The fixtures are evidence of those particular runs, not proof that every future generation will pass. The evaluator checks structure, artifacts, selected request-specific concepts, and exact budget arithmetic. A human should still review factual accuracy, feasibility, clarity, and whether the proposed approvals and owners make sense.
