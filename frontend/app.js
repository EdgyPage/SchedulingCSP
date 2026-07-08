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
  if (minimums.some((m) => !Number.isFinite(m) || m < 0)) {
    showError("Every target must be a number ≥ 0.");
    return;
  }

  const form = new FormData();
  form.append("file", state.file);
  form.append("minimums", JSON.stringify(minimums));
  form.append("max_schedules", String(Number(els.maxSchedules.value) || 10));
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
  state.schedules = result.schedules || [];
  const count = result.count || 0;
  const taskList = (result.tasks || []).join(", ");

  els.resultsCard.hidden = false;
  if (count === 0) {
    els.resultsSummary.textContent =
      "No complete schedule found. The targets may be infeasible for the given approvals " +
      "(e.g. more headcount required for a task than there are people approved for it).";
    els.resultsControls.hidden = true;
    els.tableWrap.innerHTML = "";
    return;
  }

  els.resultsSummary.textContent =
    `Found ${count} schedule${count === 1 ? "" : "s"} for tasks: ${taskList}.`;

  els.scheduleSelect.innerHTML = "";
  state.schedules.forEach((_, i) => {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = `Schedule ${i + 1}`;
    els.scheduleSelect.appendChild(opt);
  });
  els.resultsControls.hidden = false;
  renderScheduleTable(0);
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
  try {
    const res = await fetch(`/api/export?format=${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ schedules: state.schedules }),
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
