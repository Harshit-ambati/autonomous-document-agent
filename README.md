# Autonomous Document Agent

A Python API that turns a natural language business request into a plan, executes the plan with allowlisted tools, checks the result, and returns a downloadable Word document.

Built for the **Python AI Engineer Autonomous Agents assessment**. The primary engineering improvement is **reflection and self-check with one bounded revision**. Planning, execution traces, validation, and provider retries support the core workflow.

## Quick start

Python 3.11 or newer is required. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

If `.env` already exists, edit it instead of overwriting it. Set `GEMINI_API_KEY` locally. Do not commit the file or display it during the recording.

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

Use a Google AI Studio project with no billing enabled to keep usage within available free-tier access. The code cannot determine whether an account has billing enabled. Quotas and model availability are account-dependent; do not buy credits for this assessment. Check [Google's pricing](https://ai.google.dev/gemini-api/docs/pricing) and [get a key](https://aistudio.google.com/apikey).

```powershell
.\.venv\Scripts\python.exe scripts/check_model.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ for the frontend. Enter a request or choose an example, click **Generate document**, inspect the plan and requirement checks, then download the Word file. The page and API use the same local server; no frontend build or separate development server is needed. The API is also available at http://127.0.0.1:8000/docs. In another terminal:

```powershell
.\.venv\Scripts\python.exe scripts/demo.py --case standard
.\.venv\Scripts\python.exe scripts/demo.py --case complex
```

The demo makes real HTTP requests, prints the generated plan, assumptions, decisions and trace, and saves each downloaded Word document and JSON result under `outputs/demo/`. It exits with an error on failure. There is no runtime mock mode.

## API

`POST /agent`

```json
{"request":"Create a four week employee onboarding proposal with responsibilities and measurable success criteria."}
```

Success returns JSON containing:

- `run_id`, `summary`, `model`, and `elapsed_ms`.
- `plan`: document type, extracted requirements, assumptions, conflicts, and ordered tasks with tool arguments and dependencies.
- `document`: the structured content used to render Word.
- `reviews`: requirement checks and any issues before and after revision.
- `trace`: tools executed, statuses, and elapsed time per step.
- `download_url`: relative URL for `GET /documents/{run_id}`, returning the actual `.docx` attachment.
- `trace_url`: relative URL for `GET /runs/{run_id}`, returning the persisted successful response.

Returning JSON plus a download endpoint keeps the response inspectable and the binary downloadable without base64 encoding. `GET /health` reports process health and whether a key is configured; it does not establish upstream model reachability. Use `check_model.py` for that.

Errors use ordinary HTTP status codes: `422` for invalid input or a failed quality gate, `502` for rejected/invalid model output, `503` for missing credentials, rate limiting or availability, and `504` for the run deadline. Agent errors include a safe message, run ID and partial execution trace. Standard FastAPI input validation errors retain FastAPI's `detail` format. A busy response has no run ID because the request was not accepted.

## Workflow and autonomy

```text
POST /agent
    -> LLM creates a typed plan specific to the request
    -> validate tools, arguments, task IDs and dependency order
    -> execute tasks in order
         draft_section    -> LLM writes one section using dependency results
         calculate_budget -> Decimal arithmetic, no LLM arithmetic or eval
    -> assemble structured draft
    -> LLM checks original request and plan requirements
         pass -> render
         fail -> one revision -> check again -> render or return quality error
    -> python-docx renders Word
    -> persist run JSON and return download link
```

The model decides the document type, section tasks, dependencies, whether a calculation is needed, assumptions, and responses to conflicting constraints. Python controls execution boundaries, typed contracts, the tool allowlist, the revision budget, and file writes. This is **application-level tool orchestration**, not provider-native function calling. No generated Python code is executed.

For the complex example, the agent should recognize that two engineers cannot credibly guarantee all enterprise features and zero defects in two weeks, propose a narrower pilot plus follow-up phases, identify provisional ownership and approval decisions, and disclose the engineering cost estimate. The deterministic tool should calculate `2 engineers × 10 days × INR 6000 = INR 120,000`. There is no hardcoded keyword router for these requests.

## Engineering improvement

**Reflection/self-check** compares the draft with both the original user request and the extracted plan, providing evidence for each requirement. Checks reference stable 1-based requirement indices (0 means an additional check), so coverage validation accepts paraphrases but rejects omitted or nonexistent requirements. A failed review triggers one full revision and a second check. Calculated sections are restored from the deterministic tool after revision. If quality still fails, no Word file is released, and the error response includes both reviews so the caller can inspect the issues.

Why this choice: format-valid text can still omit a deadline, budget qualification, owner or acceptance criterion. The explicit check gives a visible opportunity to catch those omissions before rendering. It adds model calls and latency. A model reviewing its own output is not an independent factual verifier; schema validation and deterministic arithmetic cover only narrower guarantees.

## Frontend and guardrails

The single-page frontend is served at `/`. It offers the two assessment examples, request length feedback, model configuration status, a progress indicator, the generated plan, requirement checks, decisions, execution trace, and direct Word/JSON links. Progress shows elapsed time rather than claiming live task updates. Dynamic result text is inserted as text, not HTML.

The API applies these deterministic guardrails in addition to its existing typed contracts and self-check:

- Before any model call, reject control characters, recognizable API keys/private keys/bearer tokens, and direct requests to reveal internal instructions or credentials. The user receives an actionable `422` error.
- Keep plan tools limited to `draft_section` and `calculate_budget`, with bounded tasks and ordered dependencies. The model cannot select a filesystem path or run generated code.
- Require the review to check each planned requirement exactly once. Missing, repeated, or nonexistent indices trigger the bounded revision path; a second failure withholds the document.
- Scan the generated plan, document, and reviews for recognizable credentials before writing the Word file. A match withholds the artifact.

These pattern checks cover common credential formats, not every possible secret. The model's semantic review is useful but cannot prove factual accuracy. Review the document before sharing it. Keep the server on `127.0.0.1`; it has no login or multi-user access control.

## Project structure

| File | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI routes, lifecycle, run deadline, errors and single-run admission |
| `app/config.py` | Environment configuration; API key excluded from repr |
| `app/models.py` | Pydantic contracts and semantic validators |
| `app/llm.py` | Async Gemini REST adapter, JSON schemas and bounded retries |
| `app/agent.py` | Planner, tool orchestration, reflection and revision |
| `app/documents.py` | Deterministic Word styles, tables, pagination and atomic save |
| `app/guardrails.py` | Input, review coverage, and output credential checks |
| `app/static/` | Local frontend; no Node build step or CDN |
| `examples/` | Standard and complex assessment inputs |
| `scripts/demo.py` | Real HTTP demonstration and artifact downloads |
| `tests/test_agent.py` | Offline contract, API, tool and failure-path tests |

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app scripts tests
```

Offline tests inject scripted model responses or use an HTTP mock transport. They verify orchestration, rendering structure and failure behavior; they do **not** prove live Gemini behavior or semantic quality. The two real demo runs and visual document inspection are separate acceptance steps. Consult `docs/VALIDATION.md` for observed results, not inferred completion.

## Deliberate tradeoffs

- A single agent with a bounded loop keeps orchestration understandable within the assessment scope. A multi-agent framework is unnecessary for this task.
- Sequential execution lets later tasks use earlier results and makes the trace easy to follow. Independent tasks could run concurrently with a semaphore in a larger system.
- Synchronous HTTP completion is simpler to demonstrate. A production service would accept a job, queue work and expose job status or streaming events.
- One active generation per process limits free-tier pressure. This is not a distributed lock; run one Uvicorn worker for the assessment. Additional requests get an actionable busy response.
- UUID paths and atomic Word writes prevent model-selected paths and partial Word downloads. Successful artifacts are kept locally; failed requests return their trace but are not persisted.
- This local demo has no authentication, multi-tenant authorization, retention job or distributed storage. Bind to `127.0.0.1`. Add these before publishing it as a service. Generated documents and traces contain user-provided content.
- The agent has no browsing, external integrations or knowledge retrieval. It uses the request and labeled assumptions rather than presenting invented research as fact.

## Troubleshooting

- **Missing key:** save `.env` and restart the server. The key is read on startup.
- **Model rejected:** check that the model ID and API key are valid for your project. Credentials and raw upstream errors are never echoed to the client.
- **Quota exhausted:** check AI Studio quota, wait, or use an available free-tier model by editing `GEMINI_MODEL`. The code never silently switches to a paid model.
- **Free-tier request pacing:** model calls are spaced at least 13 seconds apart by default, including across runs. `LLM_MIN_INTERVAL_SECONDS` controls this. Retry delays honor a provider hint up to 60 seconds, within the overall deadline. Daily/token quota exhaustion still requires waiting or account configuration; pacing cannot create quota.
- **TLS certificate errors:** the client uses the operating system's certificate trust through `ssl.create_default_context()`. If needed, configure your organization's trusted CA bundle through the standard `SSL_CERT_FILE` environment variable. Keep certificate verification enabled.
- **Run deadline:** reduce the request scope or increase `AGENT_TIMEOUT_SECONDS` consciously; all retries share the outer deadline.
- **Quality check failed:** inspect the partial tool trace and clarify conflicting instructions. The service intentionally withholds a document that failed its second check.

## Submission

See `docs/ASSESSMENT.md` for requirement coverage. Record both live inputs, show actual Word downloads, and discuss a real debugging issue. This development and verification session exceeded the 60-minute assessment limit; treat it as a prepared implementation, not a compliant timed attempt. Report actual build/recording time honestly. The video itself must be recorded by the candidate.

After both live runs and document inspection, `python scripts/package_submission.py` builds `submission.zip` from an explicit file allowlist. It includes source, instructions and actual samples under `sample_outputs/`, and excludes `.env`, the virtual environment and internal QA files. Sample JSON files record the model used for each actual run; they are not a mock runtime.

Technical references: [FastAPI](https://fastapi.tiangolo.com/), [Gemini structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output), [python-docx](https://python-docx.readthedocs.io/).
