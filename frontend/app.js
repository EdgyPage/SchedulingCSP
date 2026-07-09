"use strict";

// Same-origin API (the UI is served by the FastAPI app itself), so no base URL or
// CORS to worry about. No API key: this UI assumes the service runs open, protected
// by the server-side caps in config.py.

const els = {
  file: document.getElementById("file"),
  fileLabel: document.querySelector(".file-input span"),
  rosterSummary: document.getElementById("roster-summary"),
  paramsCard: document.getElementById("params-card"),
  targets: document.getElementById("targets"),
  maxSchedules: document.getElementById("max_schedules"),
  timeBudget: document.getElementById("time_budget_s"),
  seed: document.getElementById("seed"),
  metric: document.getElementById("metric"),
  mode: document.getElementById("mode"),
  solve: document.getElementById("solve"),
  loading: document.getElementById("loading"),
  error: document.getElementById("error"),
  resultsCard: document.getElementById("results-card"),
  resultsSummary: document.getElementById("results-summary"),
  resultsControls: document.getElementById("results-controls"),
  scheduleSelect: document.getElementById("schedule-select"),
  exportXlsx: document.getElementById("export-xlsx"),
  exportCsv: document.getElementById("export-csv"),
  tableWrap: document.getElementById("table-wrap"),
};

const state = {
  file: null,       // the selected File, reused for inspect + solve
  tasks: [],        // task column names, in order
  schedules: null,  // last solve's schedules array (for export + display)
  exportMeta: null, // near-miss context to attach on export (null for exact results)
};

// --- helpers ---------------------------------------------------------------

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]
  ));
}

function showError(message) {
  els.error.textContent = message;
  els.error.hidden = false;
}

function clearError() {
  els.error.hidden = true;
  els.error.textContent = "";
}

function setLoading(on) {
  els.loading.hidden = !on;
  els.solve.disabled = on;
}

// Read a JSON API response, raising the FastAPI `detail` message on non-2xx.
async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch (_) { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return res.json();
}

function numberOrNull(input) {
  const raw = input.value.trim();
  if (raw === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

// --- step 1: inspect the uploaded roster -----------------------------------

els.file.addEventListener("change", async () => {
  const file = els.file.files[0];
  if (!file) return;
  state.file = file;
  els.fileLabel.textContent = file.name;
  clearError();
  els.rosterSummary.hidden = true;
  els.paramsCard.hidden = true;
  els.resultsCard.hidden = true;
  state.schedules = null;
  state.exportMeta = null;

  const form = new FormData();
  form.append("file", file);
  try {
    const info = await fetchJson("/api/inspect", { method: "POST", body: form });
    state.tasks = info.tasks || [];
    renderTargets(state.tasks);
    els.rosterSummary.textContent =
      `${info.employee_count} employee(s), ${state.tasks.length} task(s) detected.`;
    els.rosterSummary.hidden = false;
    els.paramsCard.hidden = false;
  } catch (err) {
    showError(err.message);
  }
});

function renderTargets(tasks) {
  els.targets.innerHTML = "";
  if (tasks.length === 0) {
    els.targets.textContent = "No task columns found in this file.";
    return;
  }
  for (const task of tasks) {
    const label = document.createElement("label");
    label.textContent = task;
    const input = document.createElement("input");
    input.type = "number";
    input.min = "0";
    input.step = "1";
    input.value = "1";
    input.dataset.task = task;
    label.appendChild(input);
    els.targets.appendChild(label);
  }
}

// --- step 2: solve ---------------------------------------------------------

els.solve.addEventListener("click", async () => {
  if (!state.file) { showError("Choose a roster file first."); return; }
  clearError();

  const minimums = [...els.targets.querySelectorAll("input")].map((i) => Number(i.value));
  if (minimums.some((m) => !Number.isInteger(m) || m < 0)) {
    showError("Every target must be a whole number ≥ 0.");
    return;
  }

  const form = new FormData();
  form.append("file", state.file);
  form.append("minimums", JSON.stringify(minimums));
  form.append("max_schedules", String(Number(els.maxSchedules.value) || 10));
  form.append("metric", els.metric.value);
  form.append("mode", els.mode.value);
  const budget = numberOrNull(els.timeBudget);
  if (budget !== null) form.append("time_budget_s", String(budget));
  const seed = numberOrNull(els.seed);
  if (seed !== null) form.append("seed", String(seed));

  setLoading(true);
  try {
    const result = await fetchJson("/api/solve/file", { method: "POST", body: form });
    renderResults(result);
  } catch (err) {
    showError(err.message);
    els.resultsCard.hidden = true;
  } finally {
    setLoading(false);
  }
});

// --- step 3: results + export ----------------------------------------------

function renderResults(result) {
  els.resultsCard.hidden = false;
  const count = result.count || 0;

  if (count > 0) {
    // Exact schedules (the happy path).
    state.schedules = result.schedules || [];
    state.exportMeta = null;
    const taskList = (result.tasks || []).join(", ");
    els.resultsSummary.textContent =
      `Found ${count} schedule${count === 1 ? "" : "s"} for tasks: ${taskList}.`;
    populateScheduleSelect(state.schedules.map((_, i) => `Schedule ${i + 1}`));
    els.resultsControls.hidden = false;
    renderScheduleTable(0);
    return;
  }

  renderInfeasible(result);
}

// count === 0: explain why no exact schedule exists, then show the closest we can staff.
function renderInfeasible(result) {
  const info = result.infeasibility || {};
  const closest = result.closest;

  const reasons = [];
  for (const r of info.reasons || []) {
    const verb = r.available === 1 ? "person is" : "people are";
    reasons.push(`“${escapeHtml(r.task)}” needs ${escapeHtml(r.needed)} but only ` +
                 `${escapeHtml(r.available)} ${verb} approved for it`);
  }
  if (info.understaffed) {
    reasons.push(`there are only ${escapeHtml(info.total_available)} people for ` +
                 `${escapeHtml(info.total_needed)} required slots`);
  }

  let html = "<strong>No schedule can hit your targets exactly.</strong>";
  if (reasons.length) html += "<br>Why: " + reasons.join("; ") + ".";

  if (!closest || !(closest.schedules || []).length) {
    els.resultsSummary.innerHTML = html;
    els.resultsControls.hidden = true;
    els.tableWrap.innerHTML = "";
    state.schedules = null;
    state.exportMeta = null;
    return;
  }

  const n = closest.schedules.length;
  html += "<br>" + (n === 1 ? "Here is the closest schedule" : `Here are the ${n} closest schedules`) +
          ` we can staff (${escapeHtml(closest.mode)} search, ${metricLabel(closest.metric)}):`;
  els.resultsSummary.innerHTML = html;

  state.schedules = closest.schedules.map((s) => s.table);
  state.exportMeta = buildExportMeta(result);
  populateScheduleSelect(closest.schedules.map((s, i) => closestLabel(s, i)));
  els.resultsControls.hidden = false;
  renderScheduleTable(0);
}

function metricLabel(metric) {
  return metric === "l1" ? "ranked by headcount shortfall" : "ranked by cosine similarity";
}

function closestLabel(s, i) {
  const short = (s.shortfall || [])
    .map((v, k) => (v > 0 ? `${state.tasks[k] || "task " + (k + 1)} short ${v}` : null))
    .filter(Boolean);
  const detail = short.length ? ` — ${short.join(", ")}` : " — all tasks covered";
  return `Closest ${i + 1}: ${s.covered}/${s.target_total} filled${detail}`;
}

function buildExportMeta(result) {
  const closest = result.closest;
  return {
    tasks: result.tasks || state.tasks,
    target: closest.target,
    metric: closest.metric,
    mode: closest.mode,
    schedules: closest.schedules.map((s) => ({
      distance: s.distance,
      coverage: s.coverage,
      shortfall: s.shortfall,
      covered: s.covered,
      target_total: s.target_total,
    })),
  };
}

function populateScheduleSelect(labels) {
  els.scheduleSelect.innerHTML = "";
  labels.forEach((label, i) => {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = label;
    els.scheduleSelect.appendChild(opt);
  });
}

els.scheduleSelect.addEventListener("change", () => {
  renderScheduleTable(Number(els.scheduleSelect.value));
});

function renderScheduleTable(index) {
  const rows = state.schedules[index] || [];
  const body = rows.map((row) => {
    const isUnassigned = row.Function === "Unassigned";
    return `<tr>
      <td>${escapeHtml(row.Name)}</td>
      <td>${escapeHtml(row.ID)}</td>
      <td class="${isUnassigned ? "unassigned" : ""}">${escapeHtml(row.Function)}</td>
    </tr>`;
  }).join("");
  els.tableWrap.innerHTML =
    `<table><thead><tr><th>Name</th><th>ID</th><th>Function</th></tr></thead>` +
    `<tbody>${body}</tbody></table>`;
}

async function exportSchedules(format) {
  if (!state.schedules || state.schedules.length === 0) return;
  clearError();
  const payload = { schedules: state.schedules };
  if (state.exportMeta) payload.meta = state.exportMeta;
  try {
    const res = await fetch(`/api/export?format=${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      let detail = `Export failed (${res.status}).`;
      try { const b = await res.json(); if (b.detail) detail = b.detail; } catch (_) {}
      throw new Error(detail);
    }
    const blob = await res.blob();
    const filename = filenameFromDisposition(res.headers.get("Content-Disposition"))
      || `schedules.${format}`;
    downloadBlob(blob, filename);
  } catch (err) {
    showError(err.message);
  }
}

function filenameFromDisposition(header) {
  if (!header) return null;
  const match = /filename="?([^"]+)"?/.exec(header);
  return match ? match[1] : null;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

els.exportXlsx.addEventListener("click", () => exportSchedules("xlsx"));
els.exportCsv.addEventListener("click", () => exportSchedules("csv"));
