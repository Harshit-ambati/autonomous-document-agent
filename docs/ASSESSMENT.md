# Assessment acceptance checklist

This maps the supplied two-page assessment to the implementation and acceptance evidence. A code path or scripted test alone is not a live demonstration.

| Requirement | Implementation | Acceptance evidence |
| --- | --- | --- |
| Python API; FastAPI preferred | `app/main.py` | `/docs`, automated HTTP tests, live API calls |
| `POST /agent` with request JSON | `AgentRequest` and route | Both `examples/*.json` submitted unchanged |
| Understand natural language | Gemini planner extracts requirements and document type | Inspect live plans for both requests |
| Create its own task list | Typed `Plan.tasks` | Display task titles, tool choices and dependencies |
| Autonomous decision-making | Dynamic plans, assumptions, conflict decisions | Complex case's phased alternative and provisional owners |
| Execute each step | Allowlisted section and budget tools | Ordered trace and resulting sections |
| Meaningful response and Word output | JSON summary, plan, checks and Word download | Download, open and inspect both `.docx` files |
| Free or locally runnable LLM | Configurable Gemini model and external free-tier key | Successful live calls from a project without billing |
| One engineering improvement | Reflection, one revision, second check | Explain why checking covers semantic omissions; show reviews and test revision path |
| Standard request | `examples/standard.json` | Live onboarding proposal run |
| Complex request | `examples/complex.json` | Live scope conflict, missing owner/budget, risks and estimate run |
| No managed no-code platform | Python source controls workflow and tools | Source walkthrough |
| Code quality and fundamentals | Typed contracts, separated modules, tests, bounded failures | Tests and architecture explanation |
| Debugging insight | Document an actual observed issue | `docs/VALIDATION.md` and honest explanation |
| Scalability thinking and tradeoff | Single-process admission, sequential flow, future queue/storage | README tradeoffs and video discussion |
| 8–10 minute video | Nine-minute outline | Candidate records and checks actual duration |
| 60-minute build challenge | This development session exceeded the limit | Not met in this iteration; see the timing record in `VALIDATION.md` |

## Inspect the generated documents

Check readability, headings, tables, page breaks, assumptions, request coverage and internal consistency. For the complex example, confirm that INR 120,000 is an illustrative engineering-only estimate, not an approved total budget, and that zero defects is handled as an infeasible guarantee rather than promised.

## Remaining human submission steps

Record the video with actual successful runs, open the downloaded Word documents, explain the implementation in your own words, and submit through the hiring team's requested channel. Do not show `.env`, claim mock tests are live output, invent a debugging story, or claim a build duration without timing evidence.
