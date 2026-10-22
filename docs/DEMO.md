# Nine minute recording outline

Use the code and observed run results to explain decisions in your own words. This is an outline, not evidence that the video has been recorded.

## Before recording

1. Configure `.env` with a free-tier Gemini key, then keep it off-screen.
2. Run `scripts/check_model.py`, tests, and lint.
3. Start one Uvicorn worker on localhost and open `/docs`.
4. Keep both example JSON inputs and the output folder ready. Use real runs for the demo.
5. Keep Word or a compatible viewer ready to inspect the actual downloads.
6. Check free-tier quota and leave enough time for both requests. If a run fails, explain it honestly rather than presenting canned output as live.

## 0:00–3:30 Live demo

- Show `POST /agent` accepting a single natural language request.
- Submit the standard example through Swagger or `scripts/demo.py --case standard`.
- Explain the agent-generated task list and completed trace; point out the assumptions and requirement checks.
- Open the downloaded Word document and show its timeline, responsibilities and success criteria.
- Submit the complex example. Explain the chosen plan, how the agent handles impossible guarantees and missing information, and whether it selects the budget tool.
- Open its Word document. Show phased scope, provisional owners, risks, acceptance criteria, approval decisions, and the clearly qualified INR 120,000 estimate.
- While a request runs, explain what the current stage does. Do not imply a pre-existing file came from a still-running request.

## 3:30–6:00 What was built

- FastAPI owns the HTTP contract; Pydantic validates input and inter-step contracts.
- Gemini creates a request-specific plan and drafts sections; it does not receive arbitrary code execution or filesystem access.
- The executor accepts only two tools: section drafting and Decimal-based budget calculation.
- Dependency outputs feed later tasks. Python assembles the draft deterministically.
- The self-check compares the draft with the original request and plan. One revision is allowed, then the system checks again. It fails closed if quality still fails.
- `python-docx` produces the final artifact with consistent styles and tables. The API returns JSON plus a download URL.
- Show one review record and a focused source excerpt rather than reading every file.

## 6:00–7:30 Debugging insight

Choose an issue actually observed and recorded in `VALIDATION.md`. Explain:

1. The reproducible symptom.
2. The specific root cause.
3. The correction and test proving it.

If discussing an offline regression, explicitly call it a test failure. Do not describe it as a live production outage. Do not invent a model failure or successful recovery.

## 7:30–9:00 Tradeoff and architecture thinking

Discuss autonomous planning versus controlled execution: the model can choose sections and tool arguments, while typed schemas, ordered dependencies, an allowlist and revision limits bound its behavior. The tradeoff is narrower autonomy in exchange for easier debugging and predictable completion.

Explain that reflection adds latency and may share the original model's blind spots. Deterministic calculations and schema checks provide stronger guarantees for their limited domains. For a larger service, move runs to a queue, add job status, authentication, per-user authorization, object storage, retention and measured evaluations. These are future work, not implemented features.
