/* ==========================================================================
   QR Scanner Pro — frontend logic
   ========================================================================== */

"use strict";

/* ------------------------------------------------------------------ *
   Icons (inline SVGs, injected via data-icon attributes)
 * ------------------------------------------------------------------ */

const ICONS = {
  qr: '<svg viewBox="0 0 24 24"><path d="M3 3h7v7H3z"/><path d="M14 3h7v7h-7z"/><path d="M3 14h7v7H3z"/><path d="M14 14h3v3h-3z"/><path d="M20 14h1"/><path d="M14 20h1"/><path d="M17 17h4"/><path d="M20 20h1"/></svg>',
  camera: '<svg viewBox="0 0 24 24"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>',
  upload: '<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/></svg>',
  image: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>',
  scan_result: '<svg viewBox="0 0 24 24"><path d="M4 7V5a1 1 0 0 1 1-1h2"/><path d="M17 4h2a1 1 0 0 1 1 1v2"/><path d="M20 17v2a1 1 0 0 1-1 1h-2"/><path d="M7 20H5a1 1 0 0 1-1-1v-2"/><path d="M4 12h16"/></svg>',
  history: '<svg viewBox="0 0 24 24"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg>',
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>',
  play: '<svg viewBox="0 0 24 24"><path d="M5 3l14 9-14 9V3z"/></svg>',
  stop: '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
  switch: '<svg viewBox="0 0 24 24"><path d="M4 4v6h6"/><path d="M4 10a8 8 0 0 1 13.7-4.1L20 8"/><path d="M20 20v-6h-6"/><path d="M20 14a8 8 0 0 1-13.7 4.1L4 16"/></svg>',
  copy: '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  save: '<svg viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/></svg>',
  external: '<svg viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6"/><path d="M10 14L21 3"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>',
  alert: '<svg viewBox="0 0 24 24"><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>',
  "qr-big": '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3h-3z"/><path d="M20 14h1"/><path d="M14 20h1"/><path d="M17 17h4"/><path d="M20 20h1"/></svg>'
};

const TYPE_KEYS_ORDERED = [
  "URL", "EMAIL", "PHONE", "SMS", "WIFI", "GEO",
  "CALENDAR_EVENT", "CONTACT", "CRYPTO", "TEXT", "UNKNOWN"
];

// History entries store the human-readable value (e.g. "Phone Number"),
// while badges/filters are keyed by the enum name (e.g. "PHONE").
const TYPE_DISPLAY_TO_KEY = {
  "URL": "URL",
  "Email": "EMAIL",
  "Phone Number": "PHONE",
  "SMS": "SMS",
  "Wi-Fi Credentials": "WIFI",
  "Geographic Location": "GEO",
  "Calendar Event": "CALENDAR_EVENT",
  "Contact Card": "CONTACT",
  "Cryptocurrency Address": "CRYPTO",
  "Plain Text": "TEXT",
  "Unknown": "UNKNOWN",
};

/* ------------------------------------------------------------------ *
   Small helpers
 * ------------------------------------------------------------------ */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const esc = (s) => String(s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

function injectIcons(root = document) {
  $$("[data-icon]", root).forEach((el) => {
    const key = el.dataset.icon;
    if (key && ICONS[key]) el.innerHTML = ICONS[key];
  });
}

async function api(url, options = {}) {
  const opts = { headers: {}, ...options };
  if (opts.body && typeof opts.body !== "string" && !(opts.body instanceof FormData) && !(opts.body instanceof Blob)) {
    opts.body = JSON.stringify(opts.body);
    opts.headers["Content-Type"] = "application/json";
  }
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch (_) { /* non-JSON */ }
  if (!res.ok && data === null) {
    throw new Error(`Request failed (${res.status})`);
  }
  return { ok: res.ok, status: res.status, data };
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

/* ------------------------------------------------------------------ *
   App state
 * ------------------------------------------------------------------ */

const state = {
  cameraRunning: false,
  cameras: 0,
  pollTimer: null,
  lastEventTs: 0,
  currentRaw: "",
  currentCopyText: "",
  historyLimit: 1000,
};

const el = {
  navDot: $("#navDot"), navStatusText: $("#navStatusText"),
  cameraDot: $("#cameraDot"), cameraStatusText: $("#cameraStatusText"),
  viewport: $("#viewport"), viewfinder: $("#viewfinder"), viewportOverlay: $("#viewportOverlay"),
  cameraFeed: $("#cameraFeed"),
  startCameraBtn: $("#startCameraBtn"), heroStartBtn: $("#heroStartBtn"),
  overlayStartBtn: $("#overlayStartBtn"), switchCameraBtn: $("#switchCameraBtn"),
  uploadBtn: $("#uploadBtn"), heroUploadBtn: $("#heroUploadBtn"),
  emptyUploadBtn: $("#emptyUploadBtn"), fileInput: $("#fileInput"), dropzone: $("#dropzone"),
  autoOpenToggle: $("#autoOpenToggle"),
  resultBadge: $("#resultBadge"), resultEmpty: $("#resultEmpty"),
  resultContent: $("#resultContent"), successAnim: $("#successAnim"),
  resultTime: $("#resultTime"), resultActionMsg: $("#resultActionMsg"),
  resultText: $("#resultText"), copyBtn: $("#copyBtn"), saveBtn: $("#saveBtn"), openBtn: $("#openBtn"),
  historyCount: $("#historyCount"), historyList: $("#historyList"), historyEmpty: $("#historyEmpty"),
  searchInput: $("#searchInput"), typeFilter: $("#typeFilter"), sortOrder: $("#sortOrder"),
  clearHistoryBtn: $("#clearHistoryBtn"),
  statScans: $("#statScans"), statTypes: $("#statTypes"), statCameras: $("#statCameras"),
};

/* ------------------------------------------------------------------ *
   Status
 * ------------------------------------------------------------------ */

function setStatus(stateName, text, { nav = true, camera = false } = {}) {
  if (nav) {
    el.navDot.className = `status-dot is-${stateName}`;
    el.navStatusText.textContent = text;
  }
  if (camera) {
    el.cameraDot.className = `status-dot is-${stateName}`;
    el.cameraStatusText.textContent = text;
  }
}

/* ------------------------------------------------------------------ *
   Toasts
 * ------------------------------------------------------------------ */

function toast(message, type = "info", sub = "", duration = 3400) {
  const container = $("#toastContainer");
  const node = document.createElement("div");
  node.className = `toast toast-${type}`;
  node.innerHTML = `
    <span class="toast-icon">${ICONS[type === "success" ? "check" : type === "error" ? "alert" : type === "warning" ? "alert" : "info"]}</span>
    <div class="toast-body">
      <div class="toast-message">${esc(message)}</div>
      ${sub ? `<div class="toast-sub">${esc(sub)}</div>` : ""}
    </div>
    <div class="toast-bar"></div>`;
  container.appendChild(node);

  const bar = $(".toast-bar", node);
  bar.style.animationDuration = `${duration}ms`;
  setTimeout(() => node.classList.add("is-leaving"), duration - 80);
  setTimeout(() => node.remove(), duration + 180);
}

/* ------------------------------------------------------------------ *
   Clipboard / download
 * ------------------------------------------------------------------ */

async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (_) { /* fall through to legacy path */ }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "position:fixed;opacity:0;pointer-events:none";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  } catch (_) {
    return false;
  }
}

function download(filename, content, mime = "text/plain") {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

/* ------------------------------------------------------------------ *
   Button loading state
 * ------------------------------------------------------------------ */

function setLoading(btn, loading, label = null) {
  if (!btn) return;
  if (loading) {
    btn.dataset.label = label || btn.textContent.trim();
    btn.innerHTML = `<span class="spinner"></span>${esc(btn.dataset.label)}`;
    btn.classList.add("is-loading");
    btn.disabled = true;
  } else {
    btn.classList.remove("is-loading");
    btn.disabled = false;
    if (btn.dataset.label) {
      btn.textContent = "";
      btn.innerHTML = (ICONS[btn.dataset.icon] || "") + `<span>${btn.dataset.label}</span>`;
    }
  }
}

/* ------------------------------------------------------------------ *
   Camera
 * ------------------------------------------------------------------ */

async function startCamera() {
  setLoading(el.startCameraBtn, true, "Starting…");
  setLoading(el.heroStartBtn, true, "Starting…");
  let res;
  try {
    res = await api("/api/camera/start", { method: "POST" });
  } catch (err) {
    res = { ok: false, data: { success: false, message: err.message } };
  }
  setLoading(el.startCameraBtn, false);
  setLoading(el.heroStartBtn, false);

  if (!res.ok || !res.data.success) {
    toast(res.data.message || "Could not start the camera.", "error");
    setStatus("error", "Camera error", { camera: true });
    return;
  }

  state.cameraRunning = true;
  state.lastEventTs = Date.now() / 1000;

  el.viewfinder.classList.remove("hidden");
  el.viewportOverlay.classList.add("is-hidden");
  el.cameraFeed.classList.add("is-visible");
  el.cameraFeed.src = `/camera?t=${Date.now()}`;

  el.startCameraBtn.innerHTML = (ICONS.stop || "") + "<span>Stop Camera</span>";
  el.startCameraBtn.classList.remove("btn-primary");
  el.startCameraBtn.classList.add("btn-danger-ghost");
  el.heroStartBtn.textContent = "";
  el.heroStartBtn.innerHTML = (ICONS.stop || "") + "<span>Stop Camera</span>";
  el.heroStartBtn.classList.remove("btn-primary");
  el.heroStartBtn.classList.add("btn-danger-ghost");
  el.switchCameraBtn.disabled = state.cameras < 2;

  setStatus("scanning", "Camera scanning…", { nav: true, camera: true });
  toast("Camera Started", "success", "Live scanning is active.");
  startEventPolling();
}

async function stopCamera(silent = false) {
  await api("/api/camera/stop", { method: "POST" }).catch(() => {});
  state.cameraRunning = false;
  stopEventPolling();

  el.cameraFeed.src = "";
  el.cameraFeed.classList.remove("is-visible");
  el.viewfinder.classList.add("hidden");
  el.viewportOverlay.classList.remove("is-hidden");

  el.startCameraBtn.innerHTML = (ICONS.camera || "") + "<span>Start Camera</span>";
  el.startCameraBtn.classList.add("btn-primary");
  el.startCameraBtn.classList.remove("btn-danger-ghost");
  el.heroStartBtn.innerHTML = (ICONS.camera || "") + "<span>Start Camera</span>";
  el.heroStartBtn.classList.add("btn-primary");
  el.heroStartBtn.classList.remove("btn-danger-ghost");

  setStatus("idle", "Camera stopped", { nav: true, camera: true });
  if (!silent) toast("Camera Stopped", "info");
}

async function toggleCamera() {
  if (state.cameraRunning) await stopCamera();
  else await startCamera();
}

async function switchCamera() {
  setLoading(el.switchCameraBtn, true, "Switching…");
  const res = await api("/api/camera/switch", { method: "POST" }).catch(() => ({ data: { success: false, message: "Switch failed." } }));
  setLoading(el.switchCameraBtn, false);
  if (!res.data.success) {
    toast(res.data.message || "Could not switch camera.", "error");
    return;
  }
  el.cameraFeed.src = `/camera?t=${Date.now()}`;
  toast("Camera Switched", "success", `Now using camera ${res.data.index}.`);
}

function startEventPolling() {
  stopEventPolling();
  state.pollTimer = setInterval(async () => {
    try {
      const res = await api(`/api/camera/events?after=${state.lastEventTs}`);
      const events = res.data.events || [];
      if (!events.length) return;
      events.forEach((ev) => { state.lastEventTs = ev.ts; onScanDetected(ev); });
    } catch (_) { /* transient network blip; keep polling */ }
  }, 1300);
}

function stopEventPolling() {
  if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
}

/* ------------------------------------------------------------------ *
   Scanning / result rendering
 * ------------------------------------------------------------------ */

function onScanDetected(payload) {
  renderResult(payload);
  refreshHistory();
}

function highlight(text) {
  let out = esc(text);
  out = out.replace(
    /\b(https?:\/\/|ftp:\/\/|www\.)[^\s"'<>]+/gi,
    (m) => `<span class="hl-url">${m}</span>`
  );
  out = out.replace(/\b[\w.+-]+@[\w-]+\.[\w.-]+\b/g, (m) => `<span class="hl-email">${m}</span>`);
  return out;
}

function renderResult(payload) {
  state.currentRaw = payload.raw || "";
  state.currentCopyText = payload.copy_text || payload.raw || "";

  el.resultBadge.textContent = payload.type || "Unknown";
  el.resultBadge.className = `type-badge badge-${payload.type_key || "UNKNOWN"}`;

  el.resultTime.textContent = payload.timestamp ? `Scanned ${payload.timestamp}` : "";
  el.resultActionMsg.textContent = payload.action?.message || "";

  const displayText = payload.type_key === "TEXT" ? (payload.raw || payload.body || "") : (payload.body || payload.raw || "");
  el.resultText.innerHTML = highlight(displayText || "(empty)");

  const canOpen = !!(payload.can_open && payload.action);
  el.openBtn.disabled = !canOpen;
  el.openBtn.title = canOpen ? "" : "Nothing to open for this type";

  el.resultEmpty.classList.add("hidden");
  el.resultContent.classList.remove("hidden");

  const anim = el.successAnim;
  anim.style.animation = "none";
  anim.offsetHeight; // restart animation
  anim.style.animation = "";

  toast("QR Detected", "success", payload.type || "Unknown", 2400);

  if (canOpen && el.autoOpenToggle.checked && payload.action.kind === "url") {
    const win = window.open(payload.action.url, "_blank");
    if (!win) {
      toast("Auto-open blocked by the browser", "warning", "Use the Open button instead.", 3200);
    }
  }
}

/* ------------------------------------------------------------------ *
   Upload
 * ------------------------------------------------------------------ */

async function uploadFile(file) {
  if (!file) return;
  if (!/\.(png|jpe?g|bmp|gif|webp|tiff?)$/i.test(file.name)) {
    toast("Unsupported image type", "error", "Use PNG, JPG, JPEG, BMP, GIF, WebP or TIFF.");
    return;
  }
  const fd = new FormData();
  fd.append("image", file);

  setStatus("scanning", "Scanning image…", { nav: true, camera: true });
  toast("Image Uploaded", "info", file.name, 1800);

  el.viewfinder.classList.remove("hidden");
  el.viewportOverlay.classList.add("is-hidden");
  el.cameraFeed.classList.add("is-visible");
  el.cameraFeed.src = "";

  let res;
  try {
    res = await api("/scan", { method: "POST", body: fd });
  } catch (err) {
    res = { ok: false, data: { success: false, message: err.message } };
  }

  if (!res.ok || !res.data.success) {
    el.viewfinder.classList.add("hidden");
    el.viewportOverlay.classList.remove("is-hidden");
    el.cameraFeed.classList.remove("is-visible");
    setStatus("error", "Scan error", { nav: true, camera: true });
    toast(res.data.message || "Could not scan the image.", "error");
    return;
  }

  const data = res.data;
  if (data.preview) {
    el.cameraFeed.src = data.preview;
  }

  if (data.count === 0) {
    toast("No QR Found", "warning", "No QR code was detected in that image.");
    setStatus("idle", "No QR code found", { nav: true, camera: true });
  } else {
    setStatus("idle", `Found ${data.count} QR code${data.count > 1 ? "s" : ""}`, { nav: true, camera: true });
    data.scans.forEach((payload) => onScanDetected(payload));
  }
}

function triggerUpload() { el.fileInput.click(); }

/* ------------------------------------------------------------------ *
   History
 * ------------------------------------------------------------------ */

async function loadHistory() {
  const params = new URLSearchParams({
    q: el.searchInput.value.trim(),
    type: el.typeFilter.value,
    sort: el.sortOrder.value,
    limit: String(state.historyLimit),
  });
  let res;
  try {
    res = await api(`/history?${params}`);
  } catch (_) {
    renderHistory([]);
    return;
  }
  renderHistory(res.data.entries || []);
}

const refreshHistory = debounce(loadHistory, 120);

function renderHistory(entries) {
  el.historyCount.textContent = String(entries.length);
  el.historyList.innerHTML = "";
  el.historyEmpty.classList.toggle("hidden", entries.length > 0);

  entries.forEach((entry, i) => {
    el.historyList.appendChild(historyCard(entry, i));
  });

  updateStats(entries);
}

function historyCard(entry, index) {
  const node = document.createElement("div");
  node.className = "history-item";
  node.style.animationDelay = `${Math.min(index * 35, 350)}ms`;

  const summary = entry.summary || entry.raw_data || "(empty)";
  const short = summary.length > 90 ? summary.slice(0, 87) + "…" : summary;
  const typeKey = TYPE_DISPLAY_TO_KEY[entry.qr_type] || "UNKNOWN";

  node.innerHTML = `
    <div class="hi-icon">${ICONS["scan_result"]}</div>
    <div class="hi-main">
      <div class="hi-top">
        <span class="type-badge badge-${typeKey}">${esc(entry.qr_type)}</span>
        <span class="hi-time">${esc(entry.timestamp)}</span>
      </div>
      <div class="hi-summary ${entry.summary ? "" : "muted"}">${esc(short)}</div>
    </div>
    <div class="hi-actions">
      <button class="hi-btn" data-action="copy" title="Copy content">${ICONS.copy}</button>
      <button class="hi-btn is-open" data-action="open" title="Open">${ICONS.external}</button>
      <button class="hi-btn is-delete" data-action="delete" title="Delete">${ICONS.trash}</button>
    </div>`;

  $('[data-action="copy"]', node).addEventListener("click", () => copyEntry(entry));
  $('[data-action="open"]', node).addEventListener("click", () => openEntry(entry));
  $('[data-action="delete"]', node).addEventListener("click", () => deleteEntry(entry));

  return node;
}

async function copyEntry(entry) {
  const text = entry.raw_data;
  const ok = await copyText(text);
  toast(ok ? "Copied to clipboard" : "Copy failed", ok ? "success" : "error");
}

async function openEntry(entry) {
  const res = await api("/open", { method: "POST", body: { raw: entry.raw_data } }).catch(() => ({ data: null }));
  if (!res.data || !res.data.success) {
    toast("Could not prepare action", "error");
    return;
  }
  performAction(res.data.action);
}

async function deleteEntry(entry) {
  const res = await api("/history/delete", { method: "POST", body: { id: entry.id } });
  if (res.data && res.data.success) {
    toast("Entry removed", "success");
    loadHistory();
  } else {
    toast(res.data?.message || "Could not delete entry", "error");
  }
}

async function clearHistory() {
  const res = await api("/history/clear", { method: "POST" });
  if (res.data && res.data.success) {
    toast("History cleared", "success");
    loadHistory();
  }
}

/* ------------------------------------------------------------------ *
   Perform a prepared action (URL open / .ics download)
 * ------------------------------------------------------------------ */

function performAction(action) {
  if (!action) return;
  if (action.kind === "url") {
    window.open(action.url, "_blank");
  } else if (action.kind === "ics") {
    download(action.filename, action.content, "text/calendar");
    toast("Calendar event saved", "success", action.filename);
  } else {
    toast("Nothing to open for this content type", "info");
  }
}

/* ------------------------------------------------------------------ *
   Stats
 * ------------------------------------------------------------------ */

function updateStats(entries) {
  el.statScans.textContent = String(entries.length);
  const types = new Set(entries.map((e) => e.qr_type));
  el.statTypes.textContent = String(types.size);
  el.statCameras.textContent = String(state.cameras);
}

/* ------------------------------------------------------------------ *
   Ripple effect
 * ------------------------------------------------------------------ */

function attachRipple() {
  $$(".btn").forEach((btn) => {
    btn.addEventListener("pointerdown", (e) => {
      if (btn.disabled) return;
      const rect = btn.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const span = document.createElement("span");
      span.className = "ripple";
      span.style.width = span.style.height = `${size}px`;
      span.style.left = `${e.clientX - rect.left - size / 2}px`;
      span.style.top = `${e.clientY - rect.top - size / 2}px`;
      btn.appendChild(span);
      setTimeout(() => span.remove(), 650);
    });
  });
}

/* ------------------------------------------------------------------ *
   Camera availability + type filter options
 * ------------------------------------------------------------------ */

async function initCameraInfo() {
  const res = await api("/api/camera/list").catch(() => ({ data: { cameras: [] } }));
  state.cameras = (res.data.cameras || []).length;
  el.statCameras.textContent = String(state.cameras);
  el.switchCameraBtn.disabled = state.cameras < 2;
}

function initTypeFilter() {
  const frag = document.createDocumentFragment();
  const all = document.createElement("option");
  all.value = "";
  all.textContent = "All types";
  frag.appendChild(all);
  Object.keys(TYPE_DISPLAY_TO_KEY).forEach((value) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    frag.appendChild(opt);
  });
  el.typeFilter.appendChild(frag);
}

/* ------------------------------------------------------------------ *
   Drag & drop
 * ------------------------------------------------------------------ */

function initDropzone() {
  el.dropzone.addEventListener("click", triggerUpload);
  el.dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); triggerUpload(); }
  });
  ["dragenter", "dragover"].forEach((ev) =>
    el.dropzone.addEventListener(ev, (e) => { e.preventDefault(); el.dropzone.classList.add("is-dragging"); })
  );
  ["dragleave", "drop"].forEach((ev) =>
    el.dropzone.addEventListener(ev, (e) => { e.preventDefault(); el.dropzone.classList.remove("is-dragging"); })
  );
  el.dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });
}

/* ------------------------------------------------------------------ *
   Wire everything together
 * ------------------------------------------------------------------ */

function bind() {
  el.startCameraBtn.addEventListener("click", toggleCamera);
  el.heroStartBtn.addEventListener("click", toggleCamera);
  el.overlayStartBtn.addEventListener("click", startCamera);
  el.switchCameraBtn.addEventListener("click", switchCamera);

  el.uploadBtn.addEventListener("click", triggerUpload);
  el.heroUploadBtn.addEventListener("click", triggerUpload);
  el.emptyUploadBtn.addEventListener("click", triggerUpload);
  el.fileInput.addEventListener("change", (e) => {
    if (e.target.files[0]) uploadFile(e.target.files[0]);
    e.target.value = "";
  });

  el.copyBtn.addEventListener("click", async () => {
    const ok = await copyText(state.currentCopyText);
    toast(ok ? "Copied" : "Copy failed", ok ? "success" : "error");
  });
  el.saveBtn.addEventListener("click", () => {
    if (!state.currentRaw) return;
    download(`qr_result_${Date.now()}.txt`, state.currentRaw);
    toast("Saved", "success", "qr_result.txt");
  });
  el.openBtn.addEventListener("click", async () => {
    if (!state.currentRaw) return;
    const res = await api("/open", { method: "POST", body: { raw: state.currentRaw } }).catch(() => ({ data: null }));
    if (res.data && res.data.success) performAction(res.data.action);
    else toast("Could not prepare action", "error");
  });

  el.searchInput.addEventListener("input", refreshHistory);
  el.typeFilter.addEventListener("change", refreshHistory);
  el.sortOrder.addEventListener("change", refreshHistory);

  el.clearHistoryBtn.addEventListener("click", clearHistory);

  $$("[data-export]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const fmt = btn.dataset.export;
      setLoading(btn, true, fmt.toUpperCase());
      const res = await fetch(`/export/${fmt}`).catch(() => ({ status: 0 }));
      setLoading(btn, false);
      if (res.status === 400) {
        const body = await res.json().catch(() => null);
        toast(body?.message || "Nothing to export", "warning");
        return;
      }
      if (!res.ok) { toast("Export failed", "error"); return; }
      const blob = await res.blob();
      download(`qr_history.${fmt}`, blob, blob.type || "text/plain");
      toast("Export Complete", "success", `qr_history.${fmt}`);
    });
  });

  injectIcons();
  attachRipple();
}

async function init() {
  bind();
  initTypeFilter();
  initDropzone();
  initCameraInfo();
  await loadHistory();
}

document.addEventListener("DOMContentLoaded", init);
