/**
 * MedLens - Interactive Client Application Logic
 * Implements Side-by-Side Source Viewer, Reference-Range Evaluator Display,
 * Human Verification Workflows, Longitudinal Analytics, and Role Perspectives.
 */

let currentPatientId = null;
let currentRole = "CLINICIAN"; // "CLINICIAN" or "PATIENT"
let currentSummaryView = "CLINICIAN";
let allPatients = [];
let patientIntake = null;
let patientReports = [];
let extractedItems = [];
let conflictAlerts = [];
let clarificationQuestions = [];
let longitudinalTrends = [];
let auditLogs = [];
let clinicalSummary = null;

let activeReportId = null;
let chartInstance = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  await loadPatients();
  lucide.createIcons();
});

// -------------------------------------------------------------
// 1. DATA FETCHING & PATIENT SWITCHING
// -------------------------------------------------------------
async function loadPatients() {
  try {
    const res = await fetch("/api/patients");
    allPatients = await res.json();
    const select = document.getElementById("patientSelect");
    select.innerHTML = "";

    allPatients.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = `${p.name} (${p.age}y, ${p.sex})`;
      select.appendChild(opt);
    });

    if (allPatients.length > 0) {
      currentPatientId = allPatients[0].id;
      select.value = currentPatientId;
      await refreshPatientData();
    }

    select.addEventListener("change", async (e) => {
      currentPatientId = e.target.value;
      await refreshPatientData();
    });
  } catch (err) {
    console.error("Failed loading patients:", err);
  }
}

async function refreshPatientData() {
  if (!currentPatientId) return;

  try {
    // Parallel fetch for snappy UI
    const [intakeRes, reportsRes, itemsRes, conflictsRes, questionsRes, trendsRes, summaryRes, logsRes] = await Promise.all([
      fetch(`/api/patients/${currentPatientId}/intake`),
      fetch(`/api/patients/${currentPatientId}/reports`),
      fetch(`/api/patients/${currentPatientId}/extracted`),
      fetch(`/api/patients/${currentPatientId}/conflicts`),
      fetch(`/api/patients/${currentPatientId}/clarifications`),
      fetch(`/api/patients/${currentPatientId}/longitudinal`),
      fetch(`/api/patients/${currentPatientId}/summary`),
      fetch(`/api/patients/${currentPatientId}/audit-logs`)
    ]);

    patientIntake = await intakeRes.json();
    patientReports = await reportsRes.json();
    extractedItems = await itemsRes.json();
    conflictAlerts = await conflictsRes.json();
    clarificationQuestions = await questionsRes.json();
    const trendsData = await trendsRes.json();
    longitudinalTrends = trendsData.biomarkers || [];
    clinicalSummary = await summaryRes.json();
    auditLogs = await logsRes.json();

    updateHeaderDemographics();
    renderConflictsBanner();
    populateReportFilterDropdown();
    renderSourceViewerTabs();
    applyFilters();
    renderLongitudinalTrends();
    renderIntakeView();
    renderClarificationsView();
    renderSummaryView();
    renderAuditLogsView();

    lucide.createIcons();
  } catch (err) {
    console.error("Error refreshing patient data:", err);
  }
}

// -------------------------------------------------------------
// 2. HEADER & DEMOGRAPHICS DISPLAY
// -------------------------------------------------------------
function updateHeaderDemographics() {
  const currentP = allPatients.find(p => p.id === currentPatientId);
  if (!currentP) return;

  document.getElementById("patientNameHeader").textContent = currentP.name;
  
  // Avatar initials
  const initials = currentP.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
  document.getElementById("patientAvatar").textContent = initials;
  document.getElementById("patientDemographicsBadge").textContent = 
    `${currentP.age}y | ${currentP.sex} | Blood: ${currentP.blood_group || 'Unknown'}`;

  // Quick stats
  const total = extractedItems.length;
  const abnormal = extractedItems.filter(it => 
    it.range_status === "HIGH" || it.range_status === "LOW" || 
    it.range_status === "CRITICAL_HIGH" || it.range_status === "CRITICAL_LOW"
  ).length;
  const verified = extractedItems.filter(it => it.verification_status === "VERIFIED" || it.verification_status === "EDITED").length;
  const verifiedPct = total > 0 ? Math.round((verified / total) * 100) : 0;

  document.getElementById("statTotalTests").textContent = total;
  document.getElementById("statAbnormalTests").textContent = abnormal;
  document.getElementById("statConflicts").textContent = conflictAlerts.length;
  document.getElementById("statVerifiedPct").textContent = `${verifiedPct}%`;

  // Intake snippet under name
  const conditions = (patientIntake?.conditions || []).slice(0, 2).join(", ") || "None recorded";
  const allergies = (patientIntake?.allergies || []).map(a => a.allergen).join(", ") || "None reported";
  const meds = (patientIntake?.medications || []).map(m => m.name).slice(0, 3).join(", ") || "None listed";

  document.getElementById("patientIntakeSummarySnippet").innerHTML = `
    <span><strong>Conditions:</strong> ${conditions}</span>
    <span><strong>Allergies:</strong> <span class="${allergies !== 'None reported' ? 'text-rose-600 font-semibold' : ''}">${allergies}</span></span>
    <span><strong>Active Meds:</strong> ${meds}</span>
  `;
}

// -------------------------------------------------------------
// 3. ROLE SWITCHING (CLINICIAN VS PATIENT VIEW)
// -------------------------------------------------------------
function switchRole(role) {
  currentRole = role;
  const btnClin = document.getElementById("roleBtnClinician");
  const btnPat = document.getElementById("roleBtnPatient");
  const roleBadge = document.getElementById("patientRoleIndicator");

  if (role === "CLINICIAN") {
    btnClin.className = "px-3 py-1 rounded-lg transition bg-white shadow-sm text-teal-800 flex items-center space-x-1.5 font-bold";
    btnPat.className = "px-3 py-1 rounded-lg transition text-slate-600 hover:text-slate-900 flex items-center space-x-1.5";
    roleBadge.textContent = "Clinician Review Mode";
    roleBadge.className = "text-xs bg-teal-50 text-teal-700 border border-teal-200 px-2 py-0.5 rounded-md font-medium";
  } else {
    btnPat.className = "px-3 py-1 rounded-lg transition bg-white shadow-sm text-rose-800 flex items-center space-x-1.5 font-bold";
    btnClin.className = "px-3 py-1 rounded-lg transition text-slate-600 hover:text-slate-900 flex items-center space-x-1.5";
    roleBadge.textContent = "Patient-Friendly Health Mode";
    roleBadge.className = "text-xs bg-rose-50 text-rose-700 border border-rose-200 px-2 py-0.5 rounded-md font-medium";
  }

  // Re-render items to show/hide technical clinical controls
  applyFilters();
  lucide.createIcons();
}

// -------------------------------------------------------------
// 4. INCONSISTENCY & CONFLICT ALERTS BANNER
// -------------------------------------------------------------
function renderConflictsBanner() {
  const container = document.getElementById("conflictsBannerContainer");
  if (!conflictAlerts || conflictAlerts.length === 0) {
    container.innerHTML = "";
    return;
  }

  const itemsHtml = conflictAlerts.map(c => {
    const isCritical = c.severity === "CRITICAL";
    const bgClass = isCritical ? "bg-rose-50 border-rose-200 text-rose-900" : "bg-amber-50 border-amber-200 text-amber-900";
    const badgeClass = isCritical ? "bg-rose-600 text-white" : "bg-amber-500 text-white";
    const icon = isCritical ? "alert-octagon" : "alert-triangle";

    return `
      <div class="border rounded-2xl p-4 shadow-sm ${bgClass} flex flex-col sm:flex-row items-start justify-between gap-3">
        <div class="flex items-start space-x-3">
          <div class="p-2 rounded-xl ${badgeClass} mt-0.5 flex-shrink-0">
            <i data-lucide="${icon}" class="w-4 h-4"></i>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <span class="text-xs font-black uppercase px-2 py-0.5 rounded ${badgeClass}">${c.severity} CONFLICT</span>
              <h4 class="text-sm font-bold text-slate-900">${c.title}</h4>
            </div>
            <p class="text-xs mt-1 text-slate-700">${c.description}</p>
            <div class="mt-2 text-xs font-semibold flex items-center space-x-1 text-teal-900">
              <i data-lucide="shield-check" class="w-3.5 h-3.5 text-teal-700"></i>
              <span><strong>Action Recommendation:</strong> ${c.recommendation}</span>
            </div>
          </div>
        </div>
        <div class="text-[11px] font-mono text-slate-500 self-end sm:self-center">
          Entities: ${c.source_entities.join(" &bull; ")}
        </div>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="space-y-3">
      <div class="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-slate-700">
        <i data-lucide="shield-alert" class="w-4 h-4 text-rose-600"></i>
        <span>Clinical Inconsistencies & Safety Contraindications (${conflictAlerts.length})</span>
      </div>
      ${itemsHtml}
    </div>
  `;
  lucide.createIcons();
}

// -------------------------------------------------------------
// 5. SIDE-BY-SIDE SOURCE VIEWER
// -------------------------------------------------------------
function renderSourceViewerTabs() {
  const tabsContainer = document.getElementById("sourceReportTabs");
  tabsContainer.innerHTML = "";

  if (patientReports.length === 0) {
    document.getElementById("sourceReportBadge").textContent = "No reports found";
    document.getElementById("sourceDocumentContent").textContent = "No laboratory documents uploaded for this patient.";
    return;
  }

  // If no active report chosen or not in list, select first
  if (!activeReportId || !patientReports.some(r => r.id === activeReportId)) {
    activeReportId = patientReports[0].id;
  }

  patientReports.forEach(rep => {
    const isActive = rep.id === activeReportId;
    const btn = document.createElement("button");
    btn.className = `text-xs px-2.5 py-1 rounded-lg transition whitespace-nowrap font-medium ${
      isActive 
        ? "bg-teal-700 text-white font-semibold" 
        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
    }`;
    btn.textContent = `${rep.report_date} (${rep.items_count || 0} tests)`;
    btn.onclick = () => selectSourceReport(rep.id);
    tabsContainer.appendChild(btn);
  });

  loadSourceReportContent(activeReportId);
}

function selectSourceReport(reportId) {
  activeReportId = reportId;
  renderSourceViewerTabs();
}

function loadSourceReportContent(reportId) {
  const rep = patientReports.find(r => r.id === reportId);
  if (!rep) return;

  document.getElementById("sourceReportBadge").textContent = `${rep.title} | ${rep.report_date}`;
  const pre = document.getElementById("sourceDocumentContent");
  pre.innerHTML = escapeHtml(rep.raw_text);
}

function inspectSourceSnippet(snippet, reportId) {
  // If item belongs to a different report, switch to that report first
  if (reportId && reportId !== activeReportId) {
    selectSourceReport(reportId);
  }

  const alertBox = document.getElementById("sourceSnippetAlert");
  const alertText = document.getElementById("sourceSnippetText");
  alertBox.classList.remove("hidden");
  alertText.textContent = `Matched Excerpt: "${snippet}"`;

  const pre = document.getElementById("sourceDocumentContent");
  const rep = patientReports.find(r => r.id === activeReportId);
  if (!rep) return;

  const raw = rep.raw_text;
  if (!raw) return;

  // Highlight snippet in the document text
  if (snippet && raw.includes(snippet.trim())) {
    const escapedSnippet = escapeHtml(snippet.trim());
    const escapedRaw = escapeHtml(raw);
    const highlighted = escapedRaw.replace(
      escapedSnippet,
      `<span id="activeSnippetAnchor" class="source-highlight">${escapedSnippet}</span>`
    );
    pre.innerHTML = highlighted;

    // Auto-scroll to snippet
    const targetEl = document.getElementById("activeSnippetAnchor");
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  } else {
    pre.innerHTML = escapeHtml(raw);
  }
}

function clearSourceHighlight() {
  document.getElementById("sourceSnippetAlert").classList.add("hidden");
  loadSourceReportContent(activeReportId);
}

// -------------------------------------------------------------
// 6. STRUCTURED MEDICAL RECORD RENDERING & FILTERING
// -------------------------------------------------------------
function populateReportFilterDropdown() {
  const sel = document.getElementById("filterReport");
  sel.innerHTML = '<option value="ALL">All Reports</option>';
  patientReports.forEach(r => {
    const opt = document.createElement("option");
    opt.value = r.id;
    opt.textContent = `${r.title} (${r.report_date})`;
    sel.appendChild(opt);
  });
}

function applyFilters() {
  const query = document.getElementById("searchInput").value.toLowerCase().trim();
  const category = document.getElementById("filterCategory").value;
  const status = document.getElementById("filterStatus").value;
  const report = document.getElementById("filterReport").value;

  const filtered = extractedItems.filter(it => {
    // Search query
    if (query && !it.test_name.toLowerCase().includes(query) && !(it.category || "").toLowerCase().includes(query)) {
      return false;
    }
    // Category
    if (category !== "ALL" && (it.category || "").toLowerCase() !== category.toLowerCase()) {
      return false;
    }
    // Status
    if (status !== "ALL") {
      if (status === "HIGH" && !it.range_status.includes("HIGH")) return false;
      if (status === "LOW" && !it.range_status.includes("LOW")) return false;
      if (status === "NORMAL" && it.range_status !== "NORMAL") return false;
      if (status === "UNREFERENCED" && it.range_status !== "UNREFERENCED") return false;
    }
    // Report
    if (report !== "ALL" && it.report_id !== report) {
      return false;
    }
    return true;
  });

  renderExtractedCards(filtered);
}

function resetFilters() {
  document.getElementById("searchInput").value = "";
  document.getElementById("filterCategory").value = "ALL";
  document.getElementById("filterStatus").value = "ALL";
  document.getElementById("filterReport").value = "ALL";
  applyFilters();
}

function renderExtractedCards(items) {
  const container = document.getElementById("extractedItemsList");
  document.getElementById("visibleItemsCount").textContent = items.length;

  if (items.length === 0) {
    container.innerHTML = `
      <div class="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-500 text-xs">
        <i data-lucide="inbox" class="w-8 h-8 text-slate-400 mx-auto mb-2"></i>
        No structured clinical items match the selected filter criteria.
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = items.map(it => {
    // Status badge style
    let statusBadgeClass = "badge-unreferenced";
    let statusLabel = it.range_status;

    if (it.range_status === "NORMAL") {
      statusBadgeClass = "badge-normal";
      statusLabel = "NORMAL";
    } else if (it.range_status === "HIGH") {
      statusBadgeClass = "badge-high";
      statusLabel = "HIGH";
    } else if (it.range_status === "LOW") {
      statusBadgeClass = "badge-low";
      statusLabel = "LOW";
    } else if (it.range_status === "CRITICAL_HIGH") {
      statusBadgeClass = "badge-critical";
      statusLabel = "CRITICAL HIGH";
    } else if (it.range_status === "CRITICAL_LOW") {
      statusBadgeClass = "badge-critical";
      statusLabel = "CRITICAL LOW";
    } else if (it.range_status === "UNREFERENCED") {
      statusBadgeClass = "badge-unreferenced";
      statusLabel = "NO SOURCE RANGE";
    }

    // Patient View simplification
    const isPatientView = currentRole === "PATIENT";
    const patientFriendlyStatus = it.range_status === "NORMAL" 
      ? "Within Typical Bounds" 
      : (it.range_status.includes("HIGH") ? "Above Target Range" : (it.range_status.includes("LOW") ? "Below Target Range" : "Recorded"));

    // Verification badge
    let verBadgeClass = "badge-unreviewed";
    if (it.verification_status === "VERIFIED") verBadgeClass = "badge-verified";
    else if (it.verification_status === "EDITED") verBadgeClass = "badge-edited";
    else if (it.verification_status === "FLAGGED") verBadgeClass = "badge-flagged";

    // Reference range text
    let refDisplay = "";
    if (it.reference_range) {
      refDisplay = `<span class="font-mono font-semibold text-slate-700">${escapeHtml(it.reference_range)}</span> ${escapeHtml(it.unit || '')}`;
    } else {
      refDisplay = `<span class="italic text-slate-400 text-[11px]">Not provided in source report (System never invents ranges)</span>`;
    }

    // Confidence display
    const confPct = Math.round((it.confidence || 0.95) * 100);

    return `
      <div class="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm hover:shadow-md transition">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          
          <!-- Title & Panel -->
          <div>
            <div class="flex items-center space-x-2">
              <h3 class="text-sm font-bold text-slate-900">${escapeHtml(it.test_name)}</h3>
              <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${statusBadgeClass}">
                ${isPatientView ? patientFriendlyStatus : statusLabel}
              </span>
            </div>
            <div class="text-[11px] text-slate-500 mt-0.5 flex items-center space-x-3">
              <span>Category: <strong>${escapeHtml(it.category || 'General')}</strong></span>
              <span>&bull;</span>
              <span>Date: <strong>${it.test_date || 'N/A'}</strong></span>
            </div>
          </div>

          <!-- Value & Unit -->
          <div class="text-left sm:text-right">
            <div class="text-lg font-black text-slate-900 tracking-tight">
              ${escapeHtml(it.value)} <span class="text-xs font-normal text-slate-500">${escapeHtml(it.unit || '')}</span>
            </div>
            <div class="text-[11px] text-slate-500">
              Source Range: ${refDisplay}
            </div>
          </div>

        </div>

        <!-- Provenance & Review Row -->
        <div class="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
          
          <!-- Source metadata -->
          <div class="flex items-center space-x-2 text-[11px] text-slate-500">
            <span class="inline-flex items-center space-x-1 bg-slate-100 px-2 py-0.5 rounded-md font-medium text-slate-700">
              <i data-lucide="file-check" class="w-3 h-3 text-teal-700"></i>
              <span>Report-Extracted</span>
            </span>
            <span class="text-slate-400">Confidence: <strong>${confPct}%</strong></span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold ${verBadgeClass}">
              ${it.verification_status} ${it.verified_by ? `by ${it.verified_by}` : ''}
            </span>
          </div>

          <!-- Actions -->
          <div class="flex items-center space-x-2">
            <button onclick="inspectSourceSnippet('${escapeHtml(it.source_snippet).replace(/'/g, "\\'")}', '${it.report_id}')" class="text-[11px] font-semibold text-teal-700 hover:text-teal-800 bg-teal-50 hover:bg-teal-100 px-2.5 py-1 rounded-lg transition flex items-center space-x-1">
              <i data-lucide="search" class="w-3 h-3"></i>
              <span>Inspect Source</span>
            </button>

            ${!isPatientView ? `
            <button onclick="openVerifyModal('${it.id}')" class="text-[11px] font-semibold text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded-lg transition flex items-center space-x-1">
              <i data-lucide="check-square" class="w-3 h-3 text-teal-600"></i>
              <span>Verify / Edit</span>
            </button>
            ` : ''}
          </div>

        </div>

        ${it.notes ? `
          <div class="mt-2 text-[11px] bg-slate-50 p-2 rounded-lg text-slate-600 border border-slate-100 italic">
            <strong>Clinical Note:</strong> ${escapeHtml(it.notes)}
          </div>
        ` : ''}

      </div>
    `;
  }).join("");

  lucide.createIcons();
}

// -------------------------------------------------------------
// 7. HUMAN-IN-THE-LOOP VERIFICATION MODAL & PATCH
// -------------------------------------------------------------
function openVerifyModal(itemId) {
  const item = extractedItems.find(it => it.id === itemId);
  if (!item) return;

  document.getElementById("editItemId").value = item.id;
  document.getElementById("editItemName").value = item.test_name;
  document.getElementById("editItemValue").value = item.value;
  document.getElementById("editItemUnit").value = item.unit || "";
  document.getElementById("editItemRange").value = item.reference_range || "";
  document.getElementById("editItemStatus").value = item.verification_status || "VERIFIED";
  document.getElementById("editItemNotes").value = item.notes || "";
  document.getElementById("editItemSnippet").textContent = item.source_snippet || "No snippet available.";

  openModal("modalVerify");
}

async function saveItemVerification() {
  const itemId = document.getElementById("editItemId").value;
  const val = document.getElementById("editItemValue").value.trim();
  const unit = document.getElementById("editItemUnit").value.trim();
  const ref = document.getElementById("editItemRange").value.trim();
  const status = document.getElementById("editItemStatus").value;
  const reviewer = document.getElementById("editItemReviewer").value.trim() || "Dr. Reviewer";
  const notes = document.getElementById("editItemNotes").value.trim();

  try {
    const res = await fetch(`/api/extracted/${itemId}?actor=${encodeURIComponent(reviewer)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        value: val,
        unit: unit,
        reference_range: ref,
        verification_status: status,
        notes: notes,
        verified_by: reviewer
      })
    });

    if (res.ok) {
      closeModal("modalVerify");
      await refreshPatientData();
    } else {
      alert("Failed to save verification update.");
    }
  } catch (err) {
    console.error("Verification error:", err);
  }
}

// -------------------------------------------------------------
// 8. LONGITUDINAL TRENDS & CHARTS
// -------------------------------------------------------------
function renderLongitudinalTrends() {
  const sel = document.getElementById("trendBiomarkerSelect");
  sel.innerHTML = "";
  document.getElementById("tabCountTrends").textContent = longitudinalTrends.length;

  if (longitudinalTrends.length === 0) {
    sel.innerHTML = "<option>No multi-report biomarkers</option>";
    document.getElementById("longitudinalTableBody").innerHTML = `
      <tr><td colspan="6" class="p-4 text-center text-slate-400">No longitudinal data points available.</td></tr>
    `;
    return;
  }

  longitudinalTrends.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t.test_name;
    const deltaStr = t.delta_percent !== null ? ` (${t.delta_percent > 0 ? '+' : ''}${t.delta_percent}%)` : '';
    opt.textContent = `${t.test_name}${deltaStr} [${t.points_count} pts]`;
    sel.appendChild(opt);
  });

  // Render Table
  const tbody = document.getElementById("longitudinalTableBody");
  tbody.innerHTML = longitudinalTrends.map(t => {
    const firstPt = t.data_points[0];
    const lastPt = t.data_points[t.data_points.length - 1];

    let deltaBadge = `<span class="bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono font-bold">0%</span>`;
    if (t.delta_percent !== null) {
      const isUp = t.delta_percent > 0;
      const colClass = isUp ? "bg-rose-50 text-rose-700 border-rose-200" : "bg-teal-50 text-teal-700 border-teal-200";
      deltaBadge = `<span class="border px-2 py-0.5 rounded font-mono font-bold ${colClass}">${isUp ? '+' : ''}${t.delta_percent}%</span>`;
    }

    return `
      <tr class="hover:bg-slate-50 transition cursor-pointer" onclick="selectBiomarkerChart('${escapeHtml(t.test_name)}')">
        <td class="py-3 px-4 font-bold text-slate-900">${escapeHtml(t.test_name)}</td>
        <td class="py-3 px-4 text-slate-500">${escapeHtml(t.category)}</td>
        <td class="py-3 px-4">
          <span class="font-mono font-semibold">${firstPt.value} ${firstPt.unit}</span>
          <div class="text-[10px] text-slate-400">${firstPt.date}</div>
        </td>
        <td class="py-3 px-4">
          <span class="font-mono font-semibold">${lastPt.value} ${lastPt.unit}</span>
          <div class="text-[10px] text-slate-400">${lastPt.date}</div>
        </td>
        <td class="py-3 px-4 text-center">${deltaBadge}</td>
        <td class="py-3 px-4 text-slate-600">${escapeHtml(t.clinical_note)}</td>
      </tr>
    `;
  }).join("");

  renderSelectedTrendChart();
}

function selectBiomarkerChart(testName) {
  const sel = document.getElementById("trendBiomarkerSelect");
  sel.value = testName;
  renderSelectedTrendChart();
  window.scrollTo({ top: 200, behavior: "smooth" });
}

function renderSelectedTrendChart() {
  const sel = document.getElementById("trendBiomarkerSelect");
  const selectedName = sel.value;
  const trend = longitudinalTrends.find(t => t.test_name === selectedName);
  if (!trend) return;

  const ctx = document.getElementById("longitudinalChart").getContext("2d");
  if (chartInstance) chartInstance.destroy();

  const labels = trend.data_points.map(p => `${p.date} (${p.report_title})`);
  const values = trend.data_points.map(p => p.value);

  // Update Insight Banner
  document.getElementById("trendInterpretationText").textContent = trend.clinical_note;
  const badge = document.getElementById("trendDeltaBadge");
  if (trend.delta_percent !== null) {
    badge.textContent = `${trend.delta_percent > 0 ? '+' : ''}${trend.delta_percent}% Net Shift`;
    badge.className = `font-bold text-xs px-2.5 py-1 rounded-full ${
      trend.delta_percent > 0 ? 'bg-rose-100 text-rose-800' : 'bg-teal-100 text-teal-800'
    }`;
  } else {
    badge.textContent = "Baseline Only";
    badge.className = "font-bold text-xs px-2.5 py-1 rounded-full bg-slate-200 text-slate-700";
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: `${trend.test_name} (${trend.unit})`,
        data: values,
        borderColor: '#0f766e',
        backgroundColor: 'rgba(15, 118, 110, 0.1)',
        borderWidth: 3,
        pointBackgroundColor: '#0f766e',
        pointRadius: 6,
        pointHoverRadius: 8,
        fill: true,
        tension: 0.2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: false,
          grid: { color: '#f1f5f9' },
          ticks: { font: { family: 'inherit', size: 11 } }
        },
        x: {
          grid: { color: '#f1f5f9' },
          ticks: { font: { family: 'inherit', size: 10 } }
        }
      },
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: {
          backgroundColor: '#0f172a',
          titleFont: { size: 12 },
          bodyFont: { size: 12 }
        }
      }
    }
  });
}

// -------------------------------------------------------------
// 9. PATIENT INTAKE & CLINICAL HISTORY VIEW
// -------------------------------------------------------------
function renderIntakeView() {
  if (!patientIntake) return;

  // Symptoms
  const sympCont = document.getElementById("intakeSymptomsList");
  sympCont.innerHTML = (patientIntake.symptoms || []).map(s => `
    <span class="bg-rose-50 text-rose-800 border border-rose-200 text-xs px-3 py-1 rounded-xl font-medium">
      ${escapeHtml(s)}
    </span>
  `).join("") || '<span class="text-slate-400 text-xs italic">No active symptoms recorded.</span>';

  // Conditions
  const condCont = document.getElementById("intakeConditionsList");
  condCont.innerHTML = (patientIntake.conditions || []).map(c => `
    <span class="bg-amber-50 text-amber-800 border border-amber-200 text-xs px-3 py-1 rounded-xl font-medium">
      ${escapeHtml(c)}
    </span>
  `).join("") || '<span class="text-slate-400 text-xs italic">No chronic conditions listed.</span>';

  // Allergies
  const allgCont = document.getElementById("intakeAllergiesList");
  allgCont.innerHTML = (patientIntake.allergies || []).map(a => `
    <div class="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-xs flex items-center justify-between">
      <div>
        <span class="font-bold text-rose-900">${escapeHtml(a.allergen)}</span>
        <span class="text-slate-500 ml-2">Reaction: <strong>${escapeHtml(a.reaction || 'Unspecified')}</strong></span>
      </div>
      <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-rose-600 text-white">${escapeHtml(a.severity || 'Moderate')}</span>
    </div>
  `).join("") || '<span class="text-slate-400 text-xs italic">No known drug allergies (NKDA).</span>';

  // Medications
  const medCont = document.getElementById("intakeMedicationsList");
  medCont.innerHTML = (patientIntake.medications || []).map(m => `
    <div class="p-2.5 rounded-xl bg-teal-50 border border-teal-200 text-xs flex items-center justify-between">
      <div>
        <span class="font-bold text-teal-900">${escapeHtml(m.name)}</span>
        <span class="text-slate-600 ml-2">${escapeHtml(m.dosage || '')} &bull; ${escapeHtml(m.frequency || '')}</span>
      </div>
      <span class="text-[11px] text-teal-700 italic">${escapeHtml(m.purpose || 'Therapeutic')}</span>
    </div>
  `).join("") || '<span class="text-slate-400 text-xs italic">No active medications listed.</span>';

  // Surgeries
  const surgCont = document.getElementById("intakeSurgeriesList");
  surgCont.innerHTML = (patientIntake.surgeries || []).map(s => `
    <li>${escapeHtml(s)}</li>
  `).join("") || '<li class="italic text-slate-400">None documented.</li>';

  // Family History
  const famCont = document.getElementById("intakeFamilyList");
  famCont.innerHTML = (patientIntake.family_history || []).map(f => `
    <li>${escapeHtml(f)}</li>
  `).join("") || '<li class="italic text-slate-400">None documented.</li>';

  // Lifestyle Notes
  document.getElementById("intakeLifestyleNotes").textContent = patientIntake.lifestyle_notes || "None recorded.";
}

// -------------------------------------------------------------
// 10. CONTEXT-AWARE CLARIFICATIONS VIEW
// -------------------------------------------------------------
function renderClarificationsView() {
  const container = document.getElementById("clarificationsList");
  document.getElementById("tabCountClarifications").textContent = clarificationQuestions.length;

  const unanswered = clarificationQuestions.filter(q => !q.answered).length;
  document.getElementById("unansweredClarificationCount").textContent = unanswered;

  if (clarificationQuestions.length === 0) {
    container.innerHTML = `
      <div class="p-6 text-center text-slate-400 text-xs">
        <i data-lucide="check-circle" class="w-8 h-8 text-teal-600 mx-auto mb-2"></i>
        No active ambiguities or missing clinical parameters detected.
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = clarificationQuestions.map(q => {
    return `
      <div class="p-4 rounded-2xl border ${q.answered ? 'bg-slate-50 border-slate-200' : 'bg-white border-teal-200 shadow-sm'} space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-100 text-teal-800">
            ${escapeHtml(q.category)}
          </span>
          <span class="text-[11px] font-semibold ${q.answered ? 'text-teal-700' : 'text-amber-600'}">
            ${q.answered ? '✓ Answered & Clarified' : '● Pending Patient/Provider Clarification'}
          </span>
        </div>

        <h4 class="text-sm font-bold text-slate-900">${escapeHtml(q.question)}</h4>
        <p class="text-xs text-slate-500 italic">Clinical Rationale: ${escapeHtml(q.rationale)}</p>

        ${q.answered ? `
          <div class="mt-2 text-xs bg-white p-3 rounded-xl border border-slate-200 text-slate-800 font-medium">
            <strong>Recorded Clarification:</strong> ${escapeHtml(q.answer || '')}
          </div>
        ` : `
          <div class="mt-3 flex items-center space-x-2">
            <input type="text" id="clarifyInput_${q.id}" placeholder="Type clarification response here..." class="flex-1 text-xs border border-slate-300 rounded-xl px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500">
            <button onclick="submitClarificationAnswer('${q.id}')" class="text-xs font-semibold px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-xl shadow-sm transition">
              Submit Answer
            </button>
          </div>
        `}
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

async function submitClarificationAnswer(questionId) {
  const input = document.getElementById(`clarifyInput_${questionId}`);
  if (!input || !input.value.trim()) return;

  try {
    const res = await fetch(`/api/clarifications/${questionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: input.value.trim() })
    });

    if (res.ok) {
      await refreshPatientData();
    } else {
      alert("Failed to record clarification answer.");
    }
  } catch (err) {
    console.error("Error answering clarification:", err);
  }
}

// -------------------------------------------------------------
// 11. AI CLINICAL SUMMARY VIEW
// -------------------------------------------------------------
function switchSummaryView(view) {
  currentSummaryView = view;
  const btnPat = document.getElementById("sumViewBtnPatient");
  const btnClin = document.getElementById("sumViewBtnClinician");

  if (view === "CLINICIAN") {
    btnClin.className = "text-xs font-semibold px-3 py-1.5 rounded-xl border border-teal-600 bg-teal-50 text-teal-800 transition font-bold";
    btnPat.className = "text-xs font-semibold px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-700 hover:bg-white transition";
  } else {
    btnPat.className = "text-xs font-semibold px-3 py-1.5 rounded-xl border border-rose-600 bg-rose-50 text-rose-800 transition font-bold";
    btnClin.className = "text-xs font-semibold px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-700 hover:bg-white transition";
  }

  renderSummaryView();
}

function renderSummaryView() {
  if (!clinicalSummary) return;

  const contentBox = document.getElementById("summaryContentBox");
  const text = currentSummaryView === "CLINICIAN" 
    ? clinicalSummary.clinician_brief 
    : clinicalSummary.patient_friendly_summary;

  contentBox.textContent = text;

  // Key findings grid
  const kfContainer = document.getElementById("summaryKeyFindings");
  kfContainer.innerHTML = (clinicalSummary.key_findings || []).map(f => `
    <div class="bg-white p-3 rounded-xl border border-slate-200 text-xs">
      <div class="font-bold text-slate-900">${escapeHtml(f.test_name)}</div>
      <div class="font-mono font-semibold text-rose-700 mt-1">${escapeHtml(f.value)}</div>
      <div class="text-[10px] text-slate-500 mt-0.5">Source Range: ${escapeHtml(f.reference_range)}</div>
    </div>
  `).join("") || '<div class="text-xs text-slate-400 col-span-3">No abnormal findings recorded.</div>';
}

// -------------------------------------------------------------
// 12. AUDIT TRAIL VIEW
// -------------------------------------------------------------
function renderAuditLogsView() {
  const countEl = document.getElementById("auditLogCount");
  countEl.textContent = `${auditLogs.length} entries`;

  const tbody = document.getElementById("auditTableBody");
  tbody.innerHTML = auditLogs.map(l => {
    let actBadge = "bg-slate-100 text-slate-700";
    if (l.action === "VERIFIED") actBadge = "bg-teal-100 text-teal-800";
    else if (l.action === "EDITED") actBadge = "bg-indigo-100 text-indigo-800";
    else if (l.action === "EXTRACTED") actBadge = "bg-blue-100 text-blue-800";
    else if (l.action === "INTAKE_UPDATED") actBadge = "bg-amber-100 text-amber-800";

    return `
      <tr class="hover:bg-slate-50">
        <td class="py-2.5 px-4 font-mono text-[11px] text-slate-500">${l.timestamp.substring(0, 19).replace('T', ' ')}</td>
        <td class="py-2.5 px-4"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${actBadge}">${l.action}</span></td>
        <td class="py-2.5 px-4 font-semibold text-slate-800">${escapeHtml(l.actor)}</td>
        <td class="py-2.5 px-4 font-mono text-[11px] text-slate-500">${escapeHtml(l.old_value || '-')}</td>
        <td class="py-2.5 px-4 font-mono text-[11px] text-slate-900 font-bold">${escapeHtml(l.new_value || '-')}</td>
        <td class="py-2.5 px-4 text-slate-600">${escapeHtml(l.details || '')}</td>
      </tr>
    `;
  }).join("") || `<tr><td colspan="6" class="p-4 text-center text-slate-400">No audit logs recorded yet.</td></tr>`;
}

// -------------------------------------------------------------
// 13. REPORT UPLOAD HANDLING
// -------------------------------------------------------------
async function handleReportUpload(e) {
  e.preventDefault();
  const fileInput = document.getElementById("uploadFileInput");
  if (!fileInput.files || fileInput.files.length === 0) return;

  const btn = document.getElementById("uploadSubmitBtn");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader" class="w-3.5 h-3.5 animate-spin"></i><span>Processing Report...</span>`;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  const title = document.getElementById("uploadTitleInput").value.trim();
  const date = document.getElementById("uploadDateInput").value;
  const fac = document.getElementById("uploadFacilityInput").value.trim();
  if (title) formData.append("title", title);
  if (date) formData.append("report_date", date);
  if (fac) formData.append("facility_name", fac);

  try {
    const res = await fetch(`/api/patients/${currentPatientId}/reports/upload`, {
      method: "POST",
      body: formData
    });

    if (res.ok) {
      closeModal("modalUpload");
      fileInput.value = "";
      document.getElementById("uploadTitleInput").value = "";
      await refreshPatientData();
    } else {
      alert("Report upload failed.");
    }
  } catch (err) {
    console.error("Upload error:", err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="upload-cloud" class="w-3.5 h-3.5"></i><span>Process & Extract</span>`;
    lucide.createIcons();
  }
}

// -------------------------------------------------------------
// 14. EDIT PATIENT INTAKE MODAL
// -------------------------------------------------------------
function openEditIntakeModal() {
  if (!patientIntake) return;

  document.getElementById("intakeFormSymptoms").value = (patientIntake.symptoms || []).join(", ");
  document.getElementById("intakeFormConditions").value = (patientIntake.conditions || []).join(", ");
  document.getElementById("intakeFormLifestyle").value = patientIntake.lifestyle_notes || "";

  // Render Allergy rows
  const allgContainer = document.getElementById("intakeFormAllergiesContainer");
  allgContainer.innerHTML = "";
  (patientIntake.allergies || []).forEach((a, idx) => addAllergyRow(a.allergen, a.reaction, a.severity));

  // Render Med rows
  const medsContainer = document.getElementById("intakeFormMedsContainer");
  medsContainer.innerHTML = "";
  (patientIntake.medications || []).forEach((m, idx) => addMedicationRow(m.name, m.dosage, m.frequency, m.purpose));

  openModal("modalEditIntake");
}

function addAllergyRow(allergen = "", reaction = "", severity = "Moderate") {
  const container = document.getElementById("intakeFormAllergiesContainer");
  const div = document.createElement("div");
  div.className = "flex items-center space-x-2 allergy-row";
  div.innerHTML = `
    <input type="text" placeholder="Allergen (e.g. Penicillin)" value="${escapeHtml(allergen)}" class="flex-1 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs allergen-name">
    <input type="text" placeholder="Reaction (e.g. Hives/Angioedema)" value="${escapeHtml(reaction)}" class="flex-1 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs allergen-reaction">
    <select class="border border-slate-300 rounded-lg px-2 py-1.5 text-xs allergen-severity">
      <option value="Severe" ${severity === 'Severe' ? 'selected' : ''}>Severe</option>
      <option value="Moderate" ${severity === 'Moderate' ? 'selected' : ''}>Moderate</option>
      <option value="Mild" ${severity === 'Mild' ? 'selected' : ''}>Mild</option>
    </select>
    <button type="button" onclick="this.parentElement.remove()" class="text-rose-500 hover:text-rose-700 font-bold px-1.5">&times;</button>
  `;
  container.appendChild(div);
}

function addMedicationRow(name = "", dosage = "", frequency = "", purpose = "") {
  const container = document.getElementById("intakeFormMedsContainer");
  const div = document.createElement("div");
  div.className = "flex items-center space-x-2 med-row";
  div.innerHTML = `
    <input type="text" placeholder="Drug Name (e.g. Metformin)" value="${escapeHtml(name)}" class="flex-1 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs med-name">
    <input type="text" placeholder="Dosage (e.g. 500mg)" value="${escapeHtml(dosage)}" class="w-24 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs med-dosage">
    <input type="text" placeholder="Schedule (e.g. BID)" value="${escapeHtml(frequency)}" class="w-24 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs med-frequency">
    <button type="button" onclick="this.parentElement.remove()" class="text-rose-500 hover:text-rose-700 font-bold px-1.5">&times;</button>
  `;
  container.appendChild(div);
}

async function handleSaveIntake(e) {
  e.preventDefault();
  const symptoms = document.getElementById("intakeFormSymptoms").value.split(",").map(s => s.trim()).filter(Boolean);
  const conditions = document.getElementById("intakeFormConditions").value.split(",").map(c => c.trim()).filter(Boolean);
  const lifestyle = document.getElementById("intakeFormLifestyle").value.trim();

  // Parse allergies
  const allergyRows = document.querySelectorAll(".allergy-row");
  const allergies = [];
  allergyRows.forEach(row => {
    const alg = row.querySelector(".allergen-name").value.trim();
    const rxn = row.querySelector(".allergen-reaction").value.trim();
    const sev = row.querySelector(".allergen-severity").value;
    if (alg) allergies.push({ allergen: alg, reaction: rxn, severity: sev, source: "Patient Intake Form" });
  });

  // Parse meds
  const medRows = document.querySelectorAll(".med-row");
  const medications = [];
  medRows.forEach(row => {
    const name = row.querySelector(".med-name").value.trim();
    const dos = row.querySelector(".med-dosage").value.trim();
    const freq = row.querySelector(".med-frequency").value.trim();
    if (name) medications.push({ name: name, dosage: dos, frequency: freq, source: "Patient Intake Form" });
  });

  const payload = {
    patient_id: currentPatientId,
    symptoms: symptoms,
    conditions: conditions,
    allergies: allergies,
    medications: medications,
    surgeries: patientIntake?.surgeries || [],
    family_history: patientIntake?.family_history || [],
    lifestyle_notes: lifestyle,
    source: "Patient Intake Form"
  };

  try {
    const res = await fetch(`/api/patients/${currentPatientId}/intake?actor=Clinician%20Intake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeModal("modalEditIntake");
      await refreshPatientData();
    } else {
      alert("Failed to save intake update.");
    }
  } catch (err) {
    console.error("Error saving intake:", err);
  }
}

// -------------------------------------------------------------
// 15. CREATE NEW PATIENT
// -------------------------------------------------------------
async function handleCreatePatient(e) {
  e.preventDefault();
  const name = document.getElementById("newPatientName").value.trim();
  const age = parseInt(document.getElementById("newPatientAge").value, 10);
  const sex = document.getElementById("newPatientSex").value;
  const blood = document.getElementById("newPatientBlood").value.trim() || "Unknown";

  try {
    const res = await fetch("/api/patients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        age: age,
        sex: sex,
        blood_group: blood
      })
    });

    if (res.ok) {
      const created = await res.json();
      closeModal("modalNewPatient");
      await loadPatients();
      // Select the new patient
      document.getElementById("patientSelect").value = created.id;
      currentPatientId = created.id;
      await refreshPatientData();
    } else {
      alert("Failed to create patient.");
    }
  } catch (err) {
    console.error("Error creating patient:", err);
  }
}

// -------------------------------------------------------------
// 16. EXPORTS (PDF & JSON)
// -------------------------------------------------------------
function downloadPDF() {
  if (!currentPatientId) return;
  window.open(`/api/patients/${currentPatientId}/export/pdf`, '_blank');
}

function downloadJSON() {
  if (!currentPatientId) return;
  window.open(`/api/patients/${currentPatientId}/export/json`, '_blank');
}

function toggleExportMenu() {
  const menu = document.getElementById("exportMenu");
  menu.classList.toggle("hidden");
}

document.addEventListener("click", (e) => {
  const btn = document.getElementById("exportDropdownBtn");
  const menu = document.getElementById("exportMenu");
  if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
    menu.classList.add("hidden");
  }
});

// -------------------------------------------------------------
// 17. TAB NAVIGATION & MODAL HELPERS
// -------------------------------------------------------------
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".tab-btn").forEach(el => {
    el.classList.remove("border-teal-700", "text-teal-700");
    el.classList.add("border-transparent", "text-slate-500");
  });

  const activePane = document.getElementById(tabId);
  if (activePane) activePane.classList.remove("hidden");

  // Nav button active class
  const btnMap = {
    "tabStructured": "navTabStructured",
    "tabLongitudinal": "navTabLongitudinal",
    "tabIntake": "navTabIntake",
    "tabClarifications": "navTabClarifications",
    "tabSummary": "navTabSummary",
    "tabAudit": "navTabAudit"
  };

  const activeBtn = document.getElementById(btnMap[tabId]);
  if (activeBtn) {
    activeBtn.classList.remove("border-transparent", "text-slate-500");
    activeBtn.classList.add("border-teal-700", "text-teal-700");
  }

  if (tabId === "tabLongitudinal") {
    setTimeout(renderSelectedTrendChart, 50);
  }

  lucide.createIcons();
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("hidden");
    lucide.createIcons();
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("hidden");
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
