# Evaluation guide

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m evals.run
```

This uses the two recorded live Gemini responses in `evals/fixtures/`. It makes no network or model calls. The command prints each case's pass count, writes `outputs/evals/report.json`, and returns exit code 1 when any check fails.

For fresh end-to-end runs, start the API and execute:

```powershell
.\.venv\Scripts\python.exe -m evals.run --source live --base-url http://127.0.0.1:8000
```

Live mode sends the unchanged requests from `examples/`, downloads the Word files, requires the output guardrail step in each trace, and saves the response and Word artifact to `outputs/evals/live_artifacts/`. It uses the configured model and may consume quota. Do not treat a recorded pass as a live pass.

The automated checks cover:

| Area | Failure it can catch |
| --- | --- |
| Typed response and task count | Malformed JSON, invalid task contracts, missing sections |
| Execution trace | Skipped or failed tools and missing review/render steps |
| Review coverage | Missing, duplicate, or unsatisfied planned requirements |
| Word artifact and parity | Corrupt or mismatched `.docx`, missing rendered paragraphs/table values |
| Standard case | Missing weeks, roles, outcomes, or an unrequested budget calculation |
| Complex case | Missing feature/scope/approval terms, incorrect engineer-days, rate, or INR 120,000 total; an obvious absolute zero-defect guarantee |

These checks use selected exact concepts and structural invariants. A passing self-review or keyword match does not establish that the document is factually correct, feasible, or well written. Before submission, inspect both Word files and answer this human rubric for each case: Does the document cover the original request? Are assumptions distinguishable from known facts? Are dates, owners, scope, and numbers consistent? Are risks and approval decisions actionable? Does the complex case avoid presenting an estimate as an approved budget or a defect-free release as guaranteed?

The regression tests in `tests/test_evals.py` deliberately remove a review check, alter the budget, and pair a JSON result with the wrong Word file. Each mutation must fail the relevant evaluation. This guards against an evaluator that always reports success.
