const form = document.getElementById("query-form");
const submitBtn = document.getElementById("submit-btn");
const statusLine = document.getElementById("status-line");
const matchDecision = document.getElementById("match-decision");
const llmProvider = document.getElementById("llm-provider");
const llmModel = document.getElementById("llm-model");
const llmMode = document.getElementById("llm-mode");
const rationale = document.getElementById("rationale");
const standardsList = document.getElementById("standards-list");
const timingGrid = document.getElementById("timing-grid");
const metricsGrid = document.getElementById("metrics-grid");

function formatProvider(provider) {
  if (provider === "groq") {
    return "Groq";
  }
  if (provider === "google") {
    return "Gemini";
  }
  if (provider === "fallback") {
    return "Local Safe Mode";
  }
  return provider || "-";
}

function formatMode(mode) {
  if (mode === "llm") {
    return "LLM Assisted";
  }
  if (mode === "fallback") {
    return "Deterministic Fallback";
  }
  return mode || "-";
}

function formatMetricLabel(label) {
  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function createTile(label, value, className) {
  const tile = document.createElement("div");
  tile.className = className;

  const labelNode = document.createElement("p");
  labelNode.className = "meta-label";
  labelNode.textContent = label;

  const valueNode = document.createElement("p");
  valueNode.className = className === "timing-tile" ? "timing-value" : "metric-value";
  valueNode.textContent = value;

  tile.append(labelNode, valueNode);
  return tile;
}

function updateBadge(text, variant) {
  matchDecision.textContent = text;
  matchDecision.className = `badge ${variant}`;
}

function renderResult(payload) {
  const { result, metrics } = payload;

  llmProvider.textContent = formatProvider(result.llm.provider);
  llmModel.textContent = result.llm.model_name;
  llmMode.textContent = formatMode(result.llm.last_generation_mode);
  rationale.textContent = result.rationale;

  if (result.match_decision === "confident-match") {
    updateBadge("Confident Match", "success");
  } else {
    updateBadge("No Confident Match", "warning");
  }

  standardsList.replaceChildren();
  result.top_candidates.forEach((candidate) => {
    const item = document.createElement("li");
    item.className = "standards-item";

    const title = document.createElement("strong");
    title.textContent = candidate.full_id;

    item.append(title);
    standardsList.append(item);
  });

  timingGrid.replaceChildren();
  Object.entries(result.timing_breakdown_seconds).forEach(([key, value]) => {
    timingGrid.append(createTile(formatMetricLabel(key), `${value} sec`, "timing-tile"));
  });

  metricsGrid.replaceChildren();
  if (metrics) {
    Object.entries(metrics).forEach(([key, value]) => {
      metricsGrid.append(createTile(formatMetricLabel(key), String(value), "metric-tile"));
    });
  } else {
    const empty = document.createElement("p");
    empty.className = "empty-text";
    empty.textContent = "Provide an expected standard to compute metrics.";
    metricsGrid.append(empty);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  statusLine.textContent = "Running retrieval and LLM reasoning...";

  const formData = new FormData(form);
  const query = String(formData.get("query") || "").trim();
  const expectedStandard = String(formData.get("expected_standard") || "").trim();

  if (!query) {
    statusLine.textContent = "Please enter a query.";
    submitBtn.disabled = false;
    return;
  }

  try {
    const response = await fetch("/api/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        expected_standard: expectedStandard || null,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const payload = await response.json();
    renderResult(payload);
    statusLine.textContent = "Completed.";
  } catch (error) {
    statusLine.textContent = `Request failed: ${error.message}`;
    updateBadge("Request Failed", "warning");
  } finally {
    submitBtn.disabled = false;
  }
});
