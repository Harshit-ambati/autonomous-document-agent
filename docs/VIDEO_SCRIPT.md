# Video submission script and preparation guide

Target length: 9 minutes 15 seconds, with a maximum of 10 minutes after rehearsal.

The spoken passages contain approximately 1,100 words. Aim for a natural 135–145 words per minute, with the request waiting time overlapping your demo explanation. The section times are targets, not a guarantee; rehearse with the actual provider latency and leave room to open the documents.

This script describes the implementation that exists. Adapt the greeting to your own voice, point to the output actually returned during recording, and avoid claiming that you personally performed work you did not perform. The development and verification session exceeded the assessment's 60-minute limit; do not claim a compliant timed build.

## Understand the project before recording

The project accepts a business request and produces two things: an inspectable JSON response and a downloadable Word document. The JSON explains what the agent planned, what it executed, what it assumed, and whether its review passed.

The model chooses the work; Python controls how that work can be executed.

```text
Natural language request
    -> FastAPI validates the input
    -> Gemini generates a structured plan
    -> Python validates tasks and dependencies
    -> Execute allowed tools in order
    -> Assemble the document content
    -> Check original requirements
         pass -> create Word file
         fail -> revise once -> check again
                   pass -> create Word file
                   fail -> return issues without a Word file
    -> Return JSON, download URL and saved run URL
```

### What makes it autonomous

The task list is not hardcoded for each document. Gemini chooses the document type, section tasks, dependencies, assumptions, conflict resolutions and whether a budget calculation is necessary. Python then executes those choices through a small, predefined tool interface.

For the onboarding input, the plan can consist entirely of drafting tasks. For the chatbot input, it can include a budget calculation before the sections that use the result. Task counts and wording can vary on a fresh run.

### What each part does

| File | Purpose | What you should be able to explain |
| --- | --- | --- |
| `app/main.py` | API routes and lifecycle | Accept requests, enforce the run deadline, reject overlapping generation per process, return downloads and errors |
| `app/models.py` | Pydantic contracts | Validate input, allowed tools, dependencies, tables, documents and reviews |
| `app/config.py` | Environment configuration | Read the Gemini key, model, timeouts and output directory without exposing credentials |
| `app/llm.py` | Gemini REST integration | Request JSON output, simplify complex decoding schemas, validate locally, pace calls and retry within limits |
| `app/agent.py` | Agent workflow | Plan, execute tasks, pass dependency outputs forward, assemble, check and revise once |
| `app/documents.py` | Word generation | Turn structured content into consistent titles, headings, paragraphs, lists and tables |
| `scripts/demo.py` | Live demonstration client | Submit real HTTP requests, print the returned plan/trace and download each actual Word file |

### The two tools

- `draft_section`: calls Gemini to write one structured section. A section contains a heading and some combination of paragraphs, bullets and tables.
- `calculate_budget`: uses Python `Decimal` arithmetic to calculate quantity multiplied by unit cost, round line amounts to two decimal places and sum them. It does not use an LLM to calculate or execute model-generated code.

Word rendering is a separate controlled step after the review passes. This is application-level tool orchestration, not Gemini-native function calling.

### The engineering improvement

Reflection/self-check asks Gemini to compare the assembled draft with the original request and extracted requirements. Each check records a requirement index, whether it is satisfied and supporting evidence. Python verifies that every plan requirement has a corresponding check. Index 0 is reserved for additional checks.

If the first review fails, the agent gets one complete revision and another review. Deterministic budget sections are restored after revision so the model cannot overwrite their calculated values. If the second review fails, the API returns HTTP 422 with the reviews and does not release a Word document.

This checks for omissions and inconsistencies. It does not guarantee factual correctness, independent verification or perfect business judgment.

## Preparation off camera

1. Rehearse the explanation, particularly the difference between the model's choices and Python's controls.
2. Confirm the configured key is usable. Keep `.env` off-screen.
3. Run the checks below. The development record reports 24 passing tests; confirm the result you get rather than assuming it.
4. Have two terminals, the API docs, and Word ready. Avoid displaying credentials or unrelated desktop content.
5. Make sure the API is running before starting the recording. If it is already running on port 8000, use that process rather than starting another one.
6. Rehearse the complete recording with a stopwatch. The recorded successful samples took approximately 83 and 121 seconds; fresh runs can differ or fail because of model availability or quota.
7. The script prints plans and execution traces after the API finishes. It does not stream task progress. Do not describe a current internal stage as observed while waiting.

From the project directory, run:

```powershell
.\.venv\Scripts\python.exe scripts/check_model.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app scripts tests
```

Start the server if needed:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`. The demonstration commands below belong in the other terminal. Open the named Word output only after that command reports success, because old files from previous runs may already exist.

## Spoken script

Stage directions in square brackets are actions, not words to read aloud. Timing marks are rehearsal targets. Do not manufacture a successful result or describe a prerecorded file as the output of a failed live request.

### 0:00–4:00 Live demonstration

[Show Swagger briefly, with POST /agent visible. Switch to the demo terminal and start the standard case immediately.]

```powershell
.\.venv\Scripts\python.exe -u scripts/demo.py --case standard
```

“Hello, I'm [your name]. This is a Python autonomous document agent. It accepts one natural language request, generates its own task list, executes that plan, checks the result, and returns a Microsoft Word document.

“The API entry point is POST slash agent. Its input is a JSON object with one request field. I'm submitting a standard business request: an onboarding proposal for five engineers joining a 30-person software company. It asks for objectives, a four-week timeline, responsibilities and measurable success criteria.

“The request does not supply a task list. The model decides how to divide the work. Python validates the resulting plan and executes its allowed tools. The API returns after the workflow finishes, so the plan and execution trace will appear here with the completed response.”

[While waiting, show examples/standard.json or the request printed by the command. Explain the input rather than inventing progress. When it finishes, point to the actual plan, completed trace, self-check result and Word path.]

“Here is the plan generated for this run. These task IDs identify the work, and the dependencies show which earlier outputs each task can use. The execution trace records the tools that actually ran, their completion status and duration. The self-check passed, and the client downloaded the Word document from the API.”

[Open outputs/demo/standard.docx. Show the timeline, responsibilities and success metrics quickly.]

“The Word document contains the requested business content with consistent headings, readable tables and relative weeks because the exact start date is unknown.”

[Switch to the terminal and launch the complex case immediately.]

```powershell
.\.venv\Scripts\python.exe -u scripts/demo.py --case complex
```

“The second request is deliberately difficult. It asks two engineers to launch a chatbot in two weeks with enterprise SSO, multiple languages, CRM integration and zero defects, without a confirmed budget or product owner.

“The agent should identify those conflicts, disclose assumptions and propose a feasible phased scope. It should not silently promise every feature. The request also supplies an illustrative rate of six thousand rupees per engineer per day for ten days.

“If the agent selects the budget tool, Python performs the arithmetic: two engineers multiplied by ten days multiplied by six thousand rupees equals one hundred and twenty thousand rupees. This is an engineering-only estimate, not an approved project budget.”

[When the request succeeds, point to its actual tool choices, assumptions, conflicts and review. Do not claim a calculation task was selected unless it is present in this run.]

“This result shows how the agent handled the conflicting requirements. Here are the phased scope decisions and provisional ownership. The trace confirms the completed actions, and the final review records requirement coverage.”

[Open outputs/demo/complex.docx. Show phased scope, the cost table, risk matrix, acceptance criteria and approval decisions.]

“The final document makes the delivery constraints visible. The estimate is clearly qualified, deferred work is identified, and the acceptance criteria use a defined test gate rather than an absolute guarantee of defect-free software.”

### 4:00–6:30 Architecture and implementation

[Show the project tree, then app/main.py.]

“The implementation has a small number of focused modules. FastAPI owns the HTTP interface. The POST endpoint validates input, starts the agent workflow and applies an overall deadline. Separate GET endpoints provide the Word attachment and the saved successful run response.

“The POST response is JSON rather than a binary file. This lets the caller inspect the summary, plan, assumptions, requirement checks and execution trace, while the download URL retrieves the actual document.”

[Show the Plan and Task models in app/models.py.]

“Pydantic defines the contracts between stages. A task must use an allowed tool, contain valid arguments and depend only on tasks that appeared earlier in the plan. This prevents unknown tool names, missing dependencies and cycles from entering execution. Table validation also checks that every row matches its columns.”

[Show Agent.run in app/agent.py.]

“The planner asks Gemini for a request-specific plan. The executor processes tasks in order and passes declared dependency outputs into later drafting calls. Drafting uses the model; cost calculations use deterministic Python arithmetic. The model never receives arbitrary code execution or filesystem access.

“My main engineering improvement is reflection with a bounded revision. After assembling the draft, the agent checks it against the original request and plan requirements. Checks use requirement indices, so coverage validation does not depend on identical wording.

“If the review fails, one revision is allowed, followed by another check. Calculated budget sections are restored from the tool output after revision. If the second check fails, the service returns the review issues and withholds the document.”

[Show app/llm.py and app/documents.py briefly.]

“The Gemini adapter handles structured output, local schema validation, paced requests and bounded retries for transient failures. The final model configuration is Gemini 3.5 Flash-Lite. The API key is read from environment configuration and is not included in the response.

“Once the review passes, python-docx builds the Word file from the structured content. Python controls the typography, headings, tables, repeated table headers and page numbering. This keeps document formatting separate from model-generated prose.”

### 6:30–7:45 A real debugging issue

[Show provider_schema in app/llm.py and the corresponding regression test in tests/test_agent.py.]

“One issue during development was that a tiny Gemini connection check succeeded, but the full planning request was rejected with HTTP 400.

“The provider reported that the supplied JSON schema created too many constrained-decoding states. The planning and document schemas combined nested arrays, string limits and patterns, which made them too complex for that decoding configuration.

“The correction was to separate generation constraints from application validation. The provider receives a simpler structural schema for the nested outputs. Python still applies the complete Pydantic schema after generation, including all bounds and semantic checks.

“That preserves strict acceptance of results without asking the provider to enforce every constraint during generation. For the shallow review schema, array limits remain enforced during decoding because oversized checklists were also observed.

“A regression test checks that provider schema simplification retains the required structure while local validation still rejects invalid content. The recorded verification completed with twenty-four passing tests and clean lint. Those tests use controlled model replies; the live demonstrations are separate evidence of real model integration.”

### 7:45–9:15 Tradeoff, limitations and close

[Show the README tradeoffs, and optionally one saved JSON review.]

“The main tradeoff is autonomous planning versus controlled execution. The model chooses the plan, tool arguments, assumptions and scope decisions. Python limits the available tools, validates their arguments, controls the revision budget and writes the files.

“I chose a single-agent loop because this task does not need the coordination overhead of a multi-agent framework. Sequential execution also makes dependency handling and debugging easier. The tradeoff is latency, because model calls and free-tier pacing add to the response time.

“Reflection is useful, but the reviewing model can share the original model's blind spots. During content review, an earlier passing draft was found to use inconsistent phase labels. That led to stronger planning and review instructions. I would not claim that self-checking guarantees correctness.

“This is a local assessment service. A production version would need authentication, per-user authorization, queued jobs, persistent job status, artifact retention and shared storage. Independent task execution and measured quality evaluations would also be useful next steps. Those are future improvements, not features I am claiming are already implemented.

“The implementation demonstrates planning, controlled tool execution, requirement checking and Word generation for both business scenarios. One submission limitation is that development and verification exceeded the sixty-minute build window, so I am not claiming a compliant timed attempt. Thank you.”

## If something fails during recording

- If Gemini is unavailable or quota-limited: say, “The provider rejected or could not complete this request. The API returned a structured error and partial trace rather than presenting a successful document.” Check the actual error before explaining its cause. Stop and retry the recording later if needed; do not fill the gap with a falsely labeled live result.
- If the quality gate fails: inspect `error.details.reviews`. Say, “The second review did not pass, so the service withheld the Word document and returned the issues.” Do not open a pre-existing file as though the failed run generated it.
- If a draft passes without revision: say it passed the first review. Explain that the revision path is covered by offline tests; do not imply it happened in that live run.
- If a generated plan differs from a saved example: explain the actual tools and decisions shown. Exact task titles and counts are model-generated.
- If asked about the timing requirement: acknowledge the recorded development limit was exceeded. Do not replace that admission with a claim about how fast the API runs; build duration and inference duration are different measurements.

## Questions to rehearse

**Why is this an agent rather than a single prompt?**

It creates a structured task plan, chooses between allowed tools, executes dependent tasks, checks the assembled result and can perform one corrective revision. The workflow controls more than a single text-generation call.

**What is deterministic?**

Input and schema validation, the tool allowlist, dependency rules, budget arithmetic, revision limits and Word rendering. The prose, plan and model review are probabilistic.

**Are you using native function calling?**

No. The model produces typed tool selections in a plan, and Python dispatches them. It is application-level orchestration.

**Why Decimal?**

It provides explicit decimal arithmetic and rounding for monetary amounts, avoiding binary floating-point representation surprises.

**What do the twenty-four tests prove?**

They verify the application's contracts, orchestration, arithmetic and failure behavior with scripted replies or mocked HTTP responses. They do not establish the semantic quality or availability of every live model response.

**Is it async and scalable?**

Model network calls are asynchronous. Tasks execute sequentially and admission permits one generation per process. Word rendering is synchronous. It is a deliberately limited local service, not a distributed job system.

**Does every request succeed?**

No. Invalid input, provider failures, exhausted quota, timeouts or a failed final quality check can return an error. A successful-looking document is not substituted for a failed run.

**Does it have memory, RAG or external research?**

No. Dependency outputs are maintained within a run, and successful traces are saved, but there is no cross-conversation memory, retrieval pipeline or web research capability.

**Where are the outputs?**

Successful runs save UUID-named Word and JSON files under the configured output directory. The demo client also saves convenient standard/complex copies under `outputs/demo/`.

**What is the strongest limitation?**

Semantic review is still model-based. It may miss errors or reject a usable draft. Human review and a measured evaluation set would be necessary before trusting this for consequential business documents.
