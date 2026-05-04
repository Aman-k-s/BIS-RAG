const form = document.getElementById("query-form");
const queryInput = document.getElementById("query");
const expectedInput = document.getElementById("expected_standard");
const expectedWrap = document.getElementById("expected-wrap");
const toggleExpectedBtn = document.getElementById("toggle-expected");
const submitBtn = document.getElementById("submit-btn");
const submitLabel = submitBtn.querySelector(".btn-label");
const statusLine = document.getElementById("status-line");

const resultCard = document.getElementById("result-card");
const resultEmpty = document.getElementById("result-empty");
const resultBody = document.getElementById("result-body");
const resultMetaRow = document.getElementById("result-meta-row");
const matchDecision = document.getElementById("match-decision");
const latencyPill = document.getElementById("latency-pill");
const modelPill = document.getElementById("model-pill");
const topHitId = document.getElementById("top-hit-id");
const topHitTitle = document.getElementById("top-hit-title");
const topHitCopyBtn = resultBody.querySelector('.copy-btn[data-copy-target="top-hit-id"]');
const rationale = document.getElementById("rationale");
const standardsList = document.getElementById("standards-list");
const timingGrid = document.getElementById("timing-grid");
const metricsGrid = document.getElementById("metrics-grid");
const metricsSection = document.getElementById("metrics-section");

const historyBtn = document.getElementById("history-btn");
const historyCount = document.getElementById("history-count");
const historyDrawer = document.getElementById("history-drawer");
const historyScrim = document.getElementById("history-scrim");
const historyClose = document.getElementById("history-close");
const historyList = document.getElementById("history-list");
const historyClear = document.getElementById("history-clear");

const HISTORY_KEY = "nn:history";
const HISTORY_MAX = 50;

function formatProvider(provider) {
  if (provider === "groq") return "Groq";
  if (provider === "google") return "Gemini";
  if (provider === "fallback") return "Local Safe Mode";
  if (provider === "disabled") return "Disabled";
  return provider || "—";
}

function formatMetricLabel(label) {
  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function setStatus(text, variant) {
  if (!text) {
    statusLine.hidden = true;
    statusLine.textContent = "";
    return;
  }
  statusLine.hidden = false;
  statusLine.textContent = text;
  statusLine.classList.remove("is-error", "is-success");
  if (variant === "error") statusLine.classList.add("is-error");
  if (variant === "success") statusLine.classList.add("is-success");
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.classList.toggle("is-loading", isLoading);
  submitLabel.textContent = isLoading ? "Finding…" : "Find standard";
}

function createTile(label, value) {
  const tile = document.createElement("div");
  tile.className = "tile";
  const labelNode = document.createElement("p");
  labelNode.className = "tile-label";
  labelNode.textContent = label;
  const valueNode = document.createElement("p");
  valueNode.className = "tile-value";
  valueNode.textContent = value;
  tile.append(labelNode, valueNode);
  return tile;
}

function updateBadge(text, variant) {
  matchDecision.textContent = text;
  matchDecision.className = `badge ${variant}`;
}

function setPill(node, text) {
  if (!text) {
    node.hidden = true;
    node.textContent = "";
    return;
  }
  node.hidden = false;
  node.textContent = text;
}

function renderStandards(candidates) {
  standardsList.replaceChildren();
  if (!candidates || candidates.length === 0) return;

  const fragment = document.createDocumentFragment();
  candidates.forEach((candidate, index) => {
    const item = document.createElement("li");
    item.className = "standards-item";

    const rank = document.createElement("span");
    rank.className = "standards-rank";
    rank.textContent = String(index + 1);

    const id = document.createElement("strong");
    id.className = "standards-id";
    id.textContent = candidate.full_id;

    item.append(rank, id);
    fragment.append(item);
  });
  standardsList.append(fragment);
}

function renderResult(payload) {
  const { result, metrics } = payload;

  resultEmpty.hidden = true;
  resultBody.hidden = false;
  resultMetaRow.hidden = false;

  if (result.match_decision === "confident-match") {
    updateBadge("Confident match", "success");
  } else {
    updateBadge("No confident match", "warning");
  }

  const latency = result.latency_seconds;
  setPill(latencyPill, typeof latency === "number" ? `${latency.toFixed(2)}s` : "");

  const providerName = formatProvider(result.llm.provider);
  const modelName = result.llm.model_name;
  const modelText = modelName ? `${providerName} · ${modelName}` : providerName;
  setPill(modelPill, providerName && providerName !== "—" ? modelText : "");

  const top = result.top_candidates && result.top_candidates[0];
  if (top) {
    topHitId.textContent = top.full_id;
    topHitTitle.textContent = top.title || "";
    topHitTitle.hidden = !top.title;
    topHitCopyBtn.hidden = false;
  } else {
    topHitId.textContent = "No candidates returned";
    topHitTitle.textContent = "";
    topHitTitle.hidden = true;
    topHitCopyBtn.hidden = true;
  }

  rationale.textContent = result.rationale || "—";

  renderStandards(result.top_candidates);

  timingGrid.replaceChildren();
  const timingFragment = document.createDocumentFragment();
  Object.entries(result.timing_breakdown_seconds || {}).forEach(([key, value]) => {
    timingFragment.append(createTile(formatMetricLabel(key), `${value} sec`));
  });
  timingGrid.append(timingFragment);

  metricsGrid.replaceChildren();
  if (metrics && Object.keys(metrics).length > 0) {
    metricsSection.hidden = false;
    const metricsFragment = document.createDocumentFragment();
    Object.entries(metrics).forEach(([key, value]) => {
      metricsFragment.append(createTile(formatMetricLabel(key), String(value)));
    });
    metricsGrid.append(metricsFragment);
  } else {
    metricsSection.hidden = true;
  }
}

async function submitQuery() {
  const query = queryInput.value.trim();
  const expectedStandard = expectedInput.value.trim();

  if (!query) {
    setStatus("Please enter a query.", "error");
    queryInput.focus();
    return;
  }

  setLoading(true);
  setStatus("Running…");

  try {
    const response = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
    setStatus("");
    addHistoryEntry({
      query,
      expected_standard: expectedStandard,
      payload,
    });
    renderHistoryList();
  } catch (error) {
    setStatus(`Request failed: ${error.message}`, "error");
    resultEmpty.hidden = true;
    resultBody.hidden = false;
    resultMetaRow.hidden = false;
    updateBadge("Request failed", "warning");
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitQuery();
});

queryInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    submitQuery();
  }
});

function setExpectedOpen(open) {
  expectedWrap.hidden = !open;
  toggleExpectedBtn.setAttribute("aria-expanded", String(open));
  toggleExpectedBtn.textContent = open ? "− Hide scoring" : "+ Score this query";
}

toggleExpectedBtn.addEventListener("click", () => {
  const willOpen = expectedWrap.hidden;
  setExpectedOpen(willOpen);
  if (willOpen) {
    expectedInput.focus();
  } else {
    expectedInput.value = "";
  }
});

/* ---------- Copy ---------- */

async function copyToClipboard(text) {
  if (!text) return false;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (_) {
    // fall through
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch (_) {
    return false;
  }
}

function flashCopied(btn) {
  const labelNode = btn.querySelector(".copy-label");
  const original = labelNode ? labelNode.textContent : null;
  btn.classList.add("is-copied");
  if (labelNode) labelNode.textContent = "Copied";
  setTimeout(() => {
    btn.classList.remove("is-copied");
    if (labelNode && original !== null) labelNode.textContent = original;
  }, 1200);
}

document.addEventListener("click", async (event) => {
  const btn = event.target.closest(".copy-btn");
  if (!btn) return;

  let value = btn.dataset.copyValue;
  if (!value && btn.dataset.copyTarget) {
    const target = document.getElementById(btn.dataset.copyTarget);
    if (target) value = target.textContent.trim();
  }
  if (!value || value === "—") return;

  const ok = await copyToClipboard(value);
  if (ok) flashCopied(btn);
});

/* ---------- History ---------- */

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

function saveHistory(list) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
  } catch (_) {
    // quota or disabled storage; ignore silently
  }
}

function makeId() {
  return `h_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function addHistoryEntry({ query, expected_standard, payload }) {
  const list = loadHistory();
  const filtered = list.filter(
    (e) => !(e.query === query && (e.expected_standard || "") === (expected_standard || ""))
  );
  filtered.unshift({
    id: makeId(),
    ts: Date.now(),
    query,
    expected_standard: expected_standard || "",
    payload,
  });
  if (filtered.length > HISTORY_MAX) filtered.length = HISTORY_MAX;
  saveHistory(filtered);
}

function removeHistoryEntry(id) {
  const list = loadHistory().filter((e) => e.id !== id);
  saveHistory(list);
}

function clearHistory() {
  saveHistory([]);
}

function formatRelativeTime(ts) {
  const diff = Date.now() - ts;
  const sec = Math.floor(diff / 1000);
  if (sec < 45) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}d ago`;
  return new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function renderHistoryList() {
  const list = loadHistory();

  if (list.length === 0) {
    historyCount.hidden = true;
    historyCount.textContent = "0";
    historyClear.hidden = true;
    historyList.replaceChildren();
    const empty = document.createElement("li");
    empty.className = "history-empty";
    empty.textContent = "No searches yet. Run a query to start your history.";
    historyList.append(empty);
    return;
  }

  historyCount.hidden = false;
  historyCount.textContent = String(list.length);
  historyClear.hidden = false;

  historyList.replaceChildren();
  const fragment = document.createDocumentFragment();
  list.forEach((entry) => {
    const item = document.createElement("li");
    item.className = "history-item";
    item.dataset.id = entry.id;

    const main = document.createElement("button");
    main.type = "button";
    main.className = "history-item-main";
    main.dataset.action = "replay";

    const top = document.createElement("div");
    top.className = "history-item-top";

    const dot = document.createElement("span");
    dot.className = "history-status-dot";
    const decision = entry.payload?.result?.match_decision;
    if (decision === "confident-match") dot.classList.add("is-success");
    else if (decision) dot.classList.add("is-warning");
    top.append(dot);

    const topHit = entry.payload?.result?.top_candidates?.[0];
    const hitText = topHit ? topHit.full_id : "No top match";
    const hitNode = document.createElement("span");
    hitNode.className = "history-item-hit";
    hitNode.textContent = hitText;
    top.append(hitNode);

    const time = document.createElement("span");
    time.className = "history-item-time";
    time.textContent = formatRelativeTime(entry.ts);
    top.append(time);

    const queryLine = document.createElement("p");
    queryLine.className = "history-item-query";
    queryLine.textContent = entry.query;

    main.append(top, queryLine);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "history-item-remove";
    remove.dataset.action = "remove";
    remove.setAttribute("aria-label", "Remove this entry");
    remove.innerHTML = `
      <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
        <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>`;

    item.append(main, remove);
    fragment.append(item);
  });
  historyList.append(fragment);
}

function replayHistoryEntry(id) {
  const entry = loadHistory().find((e) => e.id === id);
  if (!entry) return;

  queryInput.value = entry.query || "";
  expectedInput.value = entry.expected_standard || "";
  setExpectedOpen(Boolean(entry.expected_standard));

  if (entry.payload) {
    renderResult(entry.payload);
    setStatus("");
  }
  closeHistoryDrawer();
}

historyList.addEventListener("click", (event) => {
  const removeBtn = event.target.closest('[data-action="remove"]');
  if (removeBtn) {
    event.stopPropagation();
    const item = removeBtn.closest(".history-item");
    if (item && item.dataset.id) {
      removeHistoryEntry(item.dataset.id);
      renderHistoryList();
    }
    return;
  }
  const main = event.target.closest('[data-action="replay"]');
  if (main) {
    const item = main.closest(".history-item");
    if (item && item.dataset.id) replayHistoryEntry(item.dataset.id);
  }
});

historyClear.addEventListener("click", () => {
  clearHistory();
  renderHistoryList();
});

/* ---------- Drawer (accessibility) ---------- */

let lastFocusedBeforeDrawer = null;
const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

function getDrawerFocusables() {
  return Array.from(historyDrawer.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.hasAttribute("disabled") && !el.hidden && el.offsetParent !== null
  );
}

function openHistoryDrawer() {
  lastFocusedBeforeDrawer = document.activeElement;
  renderHistoryList();
  historyScrim.hidden = false;
  historyDrawer.hidden = false;
  // force reflow so the transition runs from translateX(100%)
  void historyDrawer.offsetWidth;
  historyScrim.classList.add("is-open");
  historyDrawer.classList.add("is-open");
  historyBtn.setAttribute("aria-expanded", "true");
  const focusables = getDrawerFocusables();
  if (focusables.length > 0) focusables[0].focus();
}

function closeHistoryDrawer() {
  historyScrim.classList.remove("is-open");
  historyDrawer.classList.remove("is-open");
  historyBtn.setAttribute("aria-expanded", "false");
  setTimeout(() => {
    historyScrim.hidden = true;
    historyDrawer.hidden = true;
  }, 220);
  if (lastFocusedBeforeDrawer && typeof lastFocusedBeforeDrawer.focus === "function") {
    lastFocusedBeforeDrawer.focus();
  } else {
    historyBtn.focus();
  }
}

function isDrawerOpen() {
  return !historyDrawer.hidden;
}

historyBtn.addEventListener("click", () => {
  if (isDrawerOpen()) closeHistoryDrawer();
  else openHistoryDrawer();
});

historyClose.addEventListener("click", () => closeHistoryDrawer());
historyScrim.addEventListener("click", () => closeHistoryDrawer());

document.addEventListener("keydown", (event) => {
  if (!isDrawerOpen()) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeHistoryDrawer();
    return;
  }
  if (event.key === "Tab") {
    const focusables = getDrawerFocusables();
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
});

/* ---------- Init ---------- */

renderHistoryList();