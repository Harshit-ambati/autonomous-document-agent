const examples = {
  standard: "Create an employee onboarding proposal for a 30-person software company hiring five engineers next month. Include objectives, a four-week onboarding timeline, responsibilities for HR, the engineering manager and mentors, and measurable success criteria. No budget estimate is needed. Use relative weeks because the start date is not confirmed.",
  complex: "Write a project plan to launch a customer support chatbot in two weeks with two engineers, while also requiring enterprise SSO, multilingual support, CRM integration and zero defects. There is no product owner and no confirmed budget. Do not ask follow-up questions. Decide what can realistically be delivered, explain conflicts and assumptions, propose a phased scope, assign provisional owners, include a risk matrix and acceptance criteria, and identify decisions needing approval. For an illustrative engineering-only cost estimate, assume each engineer works 10 days at INR 6000 per day; use these figures and clearly distinguish this estimate from an approved budget."
};

const byId = (id) => document.getElementById(id);
const requestInput = byId("request");

function textNode(tag, value, className) {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}

function replaceList(id, values, makeItem) {
  const list = byId(id);
  list.replaceChildren(...values.map(makeItem));
}

function showState(state) {
  byId("empty-state").classList.toggle("hidden", state !== "empty");
  byId("progress").classList.toggle("hidden", state !== "progress");
  byId("error").classList.toggle("hidden", state !== "error");
  byId("output").classList.toggle("hidden", state !== "output");
  byId("result-state").textContent = {empty:"Waiting",progress:"Working",error:"Needs attention",output:"Complete"}[state];
}

function showError(message) {
  byId("error").textContent = message;
  showState("error");
}

function renderResult(data) {
  byId("document-title").textContent = data.document.title;
  byId("summary").textContent = data.summary;
  byId("task-count").textContent = data.plan.tasks.length;
  byId("review-count").textContent = data.reviews.at(-1).checks.length;
  byId("duration").textContent = `${Math.round(data.elapsed_ms / 1000)}s`;
  byId("model-name").textContent = `Model: ${data.model}`;
  byId("download").href = data.download_url;
  byId("json-link").href = data.trace_url;

  replaceList("plan-list", data.plan.tasks, (task) => {
    const item = document.createElement("li");
    item.append(textNode("strong", task.title));
    item.append(textNode("small", `${task.tool.replaceAll("_", " ")}${task.depends_on.length ? ` · after ${task.depends_on.join(", ")}` : ""}`));
    return item;
  });
  replaceList("review-list", data.reviews.at(-1).checks, (check) => {
    const item = document.createElement("li");
    item.append(textNode("strong", `${check.satisfied ? "✓" : "!"} ${check.requirement}`));
    item.append(textNode("span", check.evidence));
    return item;
  });
  replaceList("trace-list", data.trace, (event) => {
    const item = document.createElement("li");
    item.append(textNode("span", `${event.status === "completed" ? "✓" : "!"} ${event.step}`));
    item.append(textNode("small", `${event.tool} · ${(event.duration_ms / 1000).toFixed(1)}s`));
    return item;
  });

  const decisions = byId("decisions");
  decisions.replaceChildren();
  for (const [heading, values] of [["Assumptions", data.document.assumptions], ["Conflicts", data.document.conflicts]]) {
    if (!values.length) continue;
    decisions.append(textNode("p", heading, "decision-title"));
    const list = textNode("ul", "", "decision-list");
    list.append(...values.map((value) => textNode("li", value)));
    decisions.append(list);
  }
  if (!decisions.childNodes.length) decisions.append(textNode("p", "None recorded."));
  showState("output");
}

async function refreshHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("Health check failed");
    const health = await response.json();
    byId("health-dot").classList.add(health.model_configured ? "ready" : "warning");
    byId("health-text").textContent = health.model_configured ? `Model ready · ${health.model}` : "Model key needed";
  } catch {
    byId("health-dot").classList.add("warning");
    byId("health-text").textContent = "Service unavailable";
  }
}

requestInput.addEventListener("input", () => {
  byId("character-count").textContent = `${requestInput.value.length.toLocaleString()} / 12,000`;
});
for (const button of document.querySelectorAll("[data-example]")) {
  button.addEventListener("click", () => {
    requestInput.value = examples[button.dataset.example];
    requestInput.dispatchEvent(new Event("input"));
    requestInput.focus();
  });
}

byId("agent-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = requestInput.value.trim();
  if (value.length < 10) return showError("Please enter at least 10 characters.");
  byId("generate").disabled = true;
  showState("progress");
  const started = Date.now();
  const timer = setInterval(() => {
    byId("elapsed").textContent = `Elapsed: ${Math.round((Date.now() - started) / 1000)}s`;
  }, 1000);
  try {
    const response = await fetch("/agent", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({request: value})
    });
    const data = await response.json();
    if (!response.ok) {
      const validation = Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join("; ") : "";
      throw new Error(data.error?.message || validation || `Request failed (${response.status}).`);
    }
    renderResult(data);
  } catch (error) {
    showError(error.message || "The request could not be completed. Please retry.");
  } finally {
    clearInterval(timer);
    byId("generate").disabled = false;
  }
});

refreshHealth();
