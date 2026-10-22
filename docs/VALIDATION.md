# Validation record

Validated locally on 22 October 2026 using Python 3.12.14. This record distinguishes offline tests, actual model calls and document visual inspection. It does not certify build duration or a recorded video.

## Offline checks

- 24 tests passed. Coverage includes API request validation, a successful HTTP-to-Word flow, document download and saved trace, forbidden tools and invalid dependencies, exact INR 120,000 arithmetic, dependency output propagation, preservation of calculated sections through revision, indexed coverage that accepts paraphrases, missing review coverage, bounded revision failure with actionable review details, missing credentials, unknown download IDs, timeouts, malformed tables, provider status handling and invalid JSON repair.
- Ruff lint passed and Python files were formatted.
- One upstream Starlette test-client deprecation warning is emitted for its httpx compatibility path. Tests pass; this is not an application failure. No warning suppression was added.
- These tests use scripted model replies or an HTTP mock transport; they are not live agent evidence.

## Actual standard demonstration

- Request: `examples/standard.json`.
- Model: `gemini-3.5-flash-lite`.
- Final run: `48bfcc9f-c1f3-47c8-9213-426bb9d8ca91`.
- End-to-end agent time: 82,733 ms.
- Four generated drafting tasks: objectives, a four-week timeline, roles and responsibilities, and measurable success criteria. Each later task used declared dependency outputs.
- The self-check passed; the HTTP response and actual Word download both returned 200.
- `outputs/demo/standard.json` preserves the final live response, including six indexed requirement checks. The Word document is the actual downloaded artifact from that run; model-generated content was not manually rewritten.
- Microsoft Word opened the document read-only and exported a local QA PDF. All three final page images were visually inspected. The inherited title border was removed, and table headers are kept with their first data rows.

## Actual complex demonstration

- Request: `examples/complex.json`.
- Model: `gemini-3.5-flash-lite`.
- Final run: `90c38da3-fc1b-4913-855a-169f1b80403f`; end-to-end agent time 120,905 ms.
- Five generated tasks: engineering cost calculation, scope realignment, risk/conflict analysis, acceptance criteria, and approval decisions.
- The deterministic budget tool calculated 20 engineer-days at INR 6,000, totaling INR 120,000. The document explicitly identifies this as illustrative and unapproved.
- The document proposes a two-week FAQ MVP, defers SSO, multilingual support and CRM integration, identifies provisional Engineer A/B roles, and replaces an absolute defect guarantee with a qualified acceptance gate requiring stakeholder approval.
- The final self-check passed with seven indexed requirement checks. The API response and actual Word download returned 200. Both final samples use the same selected model and indexed review contract.
- All four final page images were inspected after Microsoft Word export and Poppler rasterization. No clipping, broken tables or inherited title border was found.
- Prior actual attempts failed on provider availability, quota or review validation and correctly released no document. One earlier successful draft contained inconsistent phase labels missed by the model's own check; content review caught them, the planner/writer/reviewer instructions were strengthened, and the final example was regenerated through the API. This illustrates why model reflection is not an independent correctness guarantee.

## Real debugging observations

### Gemini rejected the planning schema

Symptom: the tiny credential/schema check succeeded, but the full planner returned HTTP 400. The redacted provider message reported that the schema had too many constrained-decoding states, with nested limits and matchers listed as typical causes.

Resolution: send a smaller structural schema for nested plan/document outputs, while preserving all Pydantic bounds, patterns and semantic validators locally. A regression test checks both the simplified provider schema and retained local validation. Real subsequent planning calls succeeded.

The review schema is shallow enough to retain its array bounds at the provider. This matters because live review calls exceeded the checklist limit despite textual feedback. The adapter now enforces that flat-array limit during decoding and sends precise validation errors on the single repair attempt.

### Budget total row failed validation

Symptom: `test_budget_tool_exact_arithmetic` failed because the total row contained two blank cells, while all cells reused a nonempty label type.

Resolution: separate optional table-cell text from mandatory labels. Headers remain nonempty; rows remain rectangular and length-bounded. The original failing test and the dependency/revision regression pass, including the exact INR 120,000 total.

### Word inherited formatting and pagination

Symptom: visual inspection revealed a blue border inherited from the bundled Word Title style and a table header alone at the foot of a page.

Resolution: strip paragraph borders from the template styles and keep header paragraphs with the first data row. Re-rendered standard pages passed inspection. OOXML-only inspection would not have caught the pagination issue.

## Environment observations

Dependency installation initially failed under sandbox DNS restrictions, then under the network's certificate chain. It succeeded using the machine's trusted certificate authorities, with verification enabled. No TLS bypass was used. Localhost HTTP and Windows test-client operations required execution outside the sandbox.

The final application and connection-check script use `ssl.create_default_context()` so the operating system's trusted certificates are available. A live Gemini connection check and both final Gemini 3.5 Flash-Lite API runs passed without the temporary CA-file environment setting. The temporary CA file is excluded from the submission.

The packaged LibreOffice renderer could not run because LibreOffice is not available. Microsoft Word's native PDF export plus bundled Poppler rasterization was used for visual QA instead. QA PDFs and page images are internal files under `tmp/`; they are not submission artifacts.

Repeated HTTP 503 responses were observed from Gemini 2.5 Flash, HTTP 429 responses eventually occurred on 2.5 Flash-Lite, and 3.1 Flash-Lite also experienced intermittent connection/availability failures. After checking model access and the provider's free-tier documentation, Gemini 3.5 Flash-Lite was explicitly selected and is the final configured default. Both final example requests succeeded on it. The application does not silently fail over to a paid provider. Model-call pacing and bounded retry delays reduce pressure but do not guarantee upstream availability or create account quota.

## Human submission steps

The candidate must record the 8–10 minute video, verify its duration, explain decisions in their own words, report actual build time honestly and submit through the hiring team's channel. No video has been recorded by this project.

## Timing limitation

This development and verification session exceeded the assessment's 60-minute limit. The first project files were created at 10:49:03 UTC; verification was still ongoing at 11:50:23 UTC, already more than 61 minutes later, excluding earlier PDF review and planning. Treat this as a prepared implementation, not evidence of a compliant timed attempt. Do not claim that all assessment conditions, including time and video submission, have been satisfied.
