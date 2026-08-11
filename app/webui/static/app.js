"use strict";

const EXAMPLE_TEXT =
  "The patient presented with severe chest pain, persistent cough and " +
  "high fever. He was diagnosed with pneumonia and type 2 diabetes. " +
  "Treatment included antibiotics, insulin therapy and regular blood " +
  "pressure monitoring. The doctor also recommended an MRI scan to rule " +
  "out a stroke.";

const el = {
  text: document.getElementById("input-text"),
  analyze: document.getElementById("btn-analyze"),
  clear: document.getElementById("btn-clear"),
  csv: document.getElementById("btn-csv"),
  pdf: document.getElementById("btn-pdf"),
  title: document.getElementById("results-title"),
  body: document.getElementById("results-body"),
  status: document.getElementById("status"),
  statusBar: document.querySelector(".status-bar"),
  spinner: document.getElementById("spinner"),
  hostInfo: document.getElementById("host-info"),
};

let terms = [];
let busy = false;

el.text.value = EXAMPLE_TEXT;

function setStatus(message, isError) {
  el.status.textContent = message;
  el.statusBar.classList.toggle("error", Boolean(isError));
}

function setBusy(value, message) {
  busy = value;
  el.spinner.hidden = !value;
  el.analyze.disabled = value;
  el.clear.disabled = value;
  el.csv.disabled = value || terms.length === 0;
  el.pdf.disabled = value || terms.length === 0;
  if (message) {
    setStatus(message, false);
  }
}

function showEmpty(message) {
  const row = document.createElement("tr");
  row.className = "empty";
  const cell = document.createElement("td");
  cell.colSpan = 3;
  cell.textContent = message;
  row.appendChild(cell);
  el.body.replaceChildren(row);
}

function renderTerms(items) {
  terms = items;
  if (items.length === 0) {
    showEmpty("No medical terms were found in the text.");
    el.title.textContent = "Found terms";
    return;
  }

  const rows = items.map((term) => {
    const row = document.createElement("tr");

    const name = document.createElement("td");
    name.textContent = term.text;

    const category = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "badge badge-" + term.category;
    badge.textContent = term.category;
    category.appendChild(badge);

    const score = document.createElement("td");
    score.textContent = (term.score * 100).toFixed(1) + "%";

    row.append(name, category, score);
    return row;
  });

  el.body.replaceChildren(...rows);
  el.title.textContent = "Found terms (" + items.length + ")";
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response;
}

async function readError(response) {
  try {
    const data = await response.json();
    return data.error || "HTTP " + response.status;
  } catch (err) {
    return "HTTP " + response.status;
  }
}

async function analyze() {
  if (busy) {
    return;
  }
  const text = el.text.value.trim();
  if (!text) {
    setStatus("Please enter text to analyze.", true);
    return;
  }

  setBusy(true, "Loading model and analyzing text...");
  try {
    const response = await postJson("/api/analyze", { text: text });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    const data = await response.json();
    renderTerms(data.terms);
    setBusy(false);
    setStatus(
      "Done. Found " + data.count + " terms in " +
        data.elapsed_seconds + " s. Export to save definitions.",
      false
    );
  } catch (err) {
    setBusy(false);
    setStatus("Error during analysis: " + err.message, true);
  }
  refreshInfo();
}

async function exportAs(format) {
  if (busy || terms.length === 0) {
    return;
  }
  setBusy(true, "Preparing " + format.toUpperCase() + " export...");
  try {
    const response = await postJson("/api/export/" + format, { terms: terms });
    if (!response.ok) {
      throw new Error(await readError(response));
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "medical_terms." + format;

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);

    setBusy(false);
    setStatus(
      "Exported " + filename + " (saved on the server as well).",
      false
    );
  } catch (err) {
    setBusy(false);
    setStatus("Export failed: " + err.message, true);
  }
}

function clearAll() {
  el.text.value = "";
  terms = [];
  showEmpty("No results yet.");
  el.title.textContent = "Found terms";
  setBusy(false, "Ready.");
}

async function refreshInfo() {
  try {
    const response = await fetch("/api/info");
    if (!response.ok) {
      return;
    }
    const info = await response.json();
    el.hostInfo.textContent =
      "Version " + info.version + " | model " + info.model +
      " | " + info.system + " (" + info.machine + ") on " + info.hostname +
      " | Python " + info.python +
      " | model " + (info.model_loaded ? "loaded" : "not loaded yet");
  } catch (err) {
    el.hostInfo.textContent = "Service information unavailable.";
  }
}

el.analyze.addEventListener("click", analyze);
el.clear.addEventListener("click", clearAll);
el.csv.addEventListener("click", () => exportAs("csv"));
el.pdf.addEventListener("click", () => exportAs("pdf"));

refreshInfo();
