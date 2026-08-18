const sampleSelect = document.getElementById("sample-select");
const submissionText = document.getElementById("submission-text");
const analyzeBtn = document.getElementById("analyze-btn");
const statusMsg = document.getElementById("status-msg");
const resultsPanel = document.getElementById("results-panel");

let samples = [];

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

async function loadSamples() {
  const res = await fetch("/api/samples");
  const data = await res.json();
  samples = data.samples;
  sampleSelect.innerHTML = samples.map(([label], i) => `<option value="${i}">${escapeHtml(label)}</option>`).join("");
  submissionText.value = samples[0][1];
}

sampleSelect.addEventListener("change", () => {
  const idx = Number(sampleSelect.value);
  submissionText.value = samples[idx][1];
});

function describeRuleParams(rule) {
  switch (rule.type) {
    case "industry_exclusion":
      return `Keywords: ${rule.keywords.join(", ")}`;
    case "max_value":
      return `${rule.field} must be ≤ ${rule.max.toLocaleString()}`;
    case "min_value":
      return `${rule.field} must be ≥ ${rule.min.toLocaleString()}`;
    case "state_max_value":
      return Object.entries(rule.states)
        .map(([st, r]) => `${st}: ${rule.field} ≤ ${r.max.toLocaleString()} (${r.note})`)
        .join("; ");
    case "text_contains":
      return (
        `${rule.field} contains: ${rule.keywords.join(", ")}` +
        (rule.exclude_keywords && rule.exclude_keywords.length ? ` — unless it also contains: ${rule.exclude_keywords.join(", ")}` : "")
      );
    case "missing_fields_threshold":
      return `Triggers when ≥ ${rule.min_missing} required fields are missing`;
    default:
      return "";
  }
}

async function loadReference() {
  const res = await fetch("/api/reference");
  const data = await res.json();

  document.getElementById("fields-count").textContent = `(${data.extraction_fields.length})`;
  document.getElementById("fields-content").innerHTML = `
    <table class="fields-table">
      ${data.extraction_fields
        .map(
          (f) => `<tr>
            <th><code>${escapeHtml(f.id)}</code><br /><span class="type-hint">${escapeHtml(f.type_hint)}</span></th>
            <td>${escapeHtml(f.description)}</td>
          </tr>`
        )
        .join("")}
    </table>`;

  document.getElementById("rules-count").textContent = `(${data.appetite_rules.length})`;
  document.getElementById("rules-content").innerHTML = `
    <ul class="rule-cards">
      ${data.appetite_rules
        .map(
          (r) => `<li class="rule-card">
            <div class="rule-card-header">
              <code>${escapeHtml(r.id)}</code>
              <span class="badge badge-${r.severity}">${escapeHtml(r.severity)}</span>
            </div>
            <p class="rule-desc">${escapeHtml(r.description)}</p>
            <p class="rule-params">${escapeHtml(describeRuleParams(r))}</p>
          </li>`
        )
        .join("")}
    </ul>`;

  document.getElementById("criteria-count").textContent = `(${data.risk_criteria.length})`;
  document.getElementById("criteria-content").innerHTML = `
    <ul class="criteria-list">
      ${data.risk_criteria
        .map(
          (c) => `<li><code>${escapeHtml(c.id)}</code><br /><span class="rule-desc">${escapeHtml(c.description)}</span></li>`
        )
        .join("")}
    </ul>`;
}

function renderExtractedTable(extracted) {
  const rows = Object.entries(extracted)
    .map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(Array.isArray(v) ? v.join(", ") : v)}</td></tr>`)
    .join("");
  return `<table class="fields-table">${rows}</table>`;
}

function renderResults(data) {
  const { extracted, appetite, risk, rationale_checks, email, mode } = data;

  const modeHtml =
    mode === "demo"
      ? `<p class="mode-banner mode-demo">Demo mode — no ANTHROPIC_API_KEY configured. Showing pre-generated Claude output for this sample. Set a key to run live.</p>`
      : `<p class="mode-banner mode-live">Live mode — this result just came from a real-time Claude API call.</p>`;

  const reasonsHtml = appetite.reasons
    .map((r) => `<li>${r.rule_id ? `<code>${escapeHtml(r.rule_id)}</code> — ` : ""}${escapeHtml(r.message)}</li>`)
    .join("");
  const rationaleHtml = (risk.rationale || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("");
  const gaps = risk.data_gaps || [];
  const gapsHtml = gaps.length
    ? `<p><strong>Data gaps flagged (prevents leakage):</strong></p><ul class="reasons">${gaps
        .map((g) => `<li>${escapeHtml(g)}</li>`)
        .join("")}</ul>`
    : "";

  const checksHtml = (rationale_checks || [])
    .map(
      (c) => `<li class="check-item ${c.passed ? "check-pass" : "check-fail"}">
        <span class="check-icon">${c.passed ? "✓" : "✗"}</span>
        <span><strong>${escapeHtml(c.description)}</strong><br /><span class="check-detail">${escapeHtml(c.detail)}</span></span>
      </li>`
    )
    .join("");

  resultsPanel.innerHTML = `
    ${modeHtml}
    <div class="result-block">
      <h3>1. Extracted Submission Data</h3>
      ${renderExtractedTable(extracted)}
    </div>
    <div class="result-block">
      <h3>2. Eligibility / Appetite Check (deterministic rule engine)</h3>
      <p><span class="badge badge-${appetite.status}">${escapeHtml(appetite.status)}</span></p>
      <ul class="reasons">${reasonsHtml}</ul>
    </div>
    <div class="result-block">
      <h3>3. Risk Triage (Claude)</h3>
      <p><span class="badge badge-${risk.risk_tier}">${escapeHtml(risk.risk_tier)}</span></p>
      <p><strong>Rationale:</strong></p>
      <ul class="reasons">${rationaleHtml}</ul>
      ${gapsHtml}
    </div>
    <div class="result-block">
      <h3>4. Rationale Verification (deterministic QA on Claude's output)</h3>
      <ul class="check-list">${checksHtml}</ul>
    </div>
    <div class="result-block">
      <h3>5. Drafted Broker Response (Claude)</h3>
      <div class="email-draft">${escapeHtml(email)}</div>
    </div>
  `;
}

analyzeBtn.addEventListener("click", async () => {
  analyzeBtn.disabled = true;
  statusMsg.textContent = "Running AURA pipeline (extraction → eligibility → risk → draft)...";
  resultsPanel.innerHTML = `<p class="placeholder">Analyzing...</p>`;
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ submission_text: submissionText.value }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Request failed");
    }
    renderResults(data);
    statusMsg.textContent = "Done.";
  } catch (err) {
    resultsPanel.innerHTML = `<p class="placeholder">Error: ${escapeHtml(err.message)}</p>`;
    statusMsg.textContent = "";
  } finally {
    analyzeBtn.disabled = false;
  }
});

loadSamples();
loadReference();
