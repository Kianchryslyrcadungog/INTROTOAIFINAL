/**
 * Aegis — Result Page JavaScript
 * Reads analysis data from sessionStorage and renders it dynamically
 */

// Incident style and labels
const INCIDENT_CONFIG = {
  "Fire":     { color: "#dc2626", bg: "rgba(220,38,38,0.1)" },
  "Accident": { color: "#d97706", bg: "rgba(217,119,6,0.1)" },
  "Medical":  { color: "#0284c7", bg: "rgba(2,132,199,0.1)" },
  "Crime":    { color: "#7c3aed", bg: "rgba(124,58,237,0.1)" },
  "Flood":    { color: "#2563eb", bg: "rgba(37,99,235,0.1)" },
};

const SERVICE_ICONS = {
  "Fire Station": "FS",
  "Hospital": "H",
  "Police Station": "PS",
  "Ambulance": "AMB",
  "Evacuation Center": "EC",
  "NDRRMC": "N",
  "Red Cross": "RC",
  "Clinic": "CL",
  "Barangay Emergency Response": "BER",
  "Traffic Management": "TM",
  "School Clinic": "SC",
  "School Security": "SS",
  "DepEd Emergency": "DE",
  "Highway Patrol": "HP",
  "MMDA / DPWH": "DP",
  "Towing Service": "TS",
  "Barangay Hall": "BH",
  "Homeowners Association": "HOA",
  "Barangay Tanod": "BT",
  "City Police Precinct": "CPP",
  "Mall Security": "MS",
  "City Health Office": "CHO",
  "Coast Guard (if coastal)": "CG",
  "Barangay Health Center": "BHC",
  "Clinic / Hospital": "CH",
  "CCTV Monitoring": "CCTV",
  "PAGASA": "P",
};

const percentFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

let currentResult = null;

// Load and render data
document.addEventListener('DOMContentLoaded', () => {
  const raw = sessionStorage.getItem('aegisResult');

  if (!raw) {
    // No data — redirect back to report
    showNoDataMessage();
    return;
  }

  const data = JSON.parse(raw);
  currentResult = data;
  renderResult(data);
});

function renderResult(data) {
  const config = INCIDENT_CONFIG[data.incident_type] || INCIDENT_CONFIG["Medical"];

  // --- Type Banner ---
  document.getElementById('typeName').textContent = data.incident_type;

  // Style the banner to reflect the incident type without a separate icon badge
  const typeBanner = document.getElementById('typeBanner');
  typeBanner.style.background = config.bg;
  typeBanner.style.borderColor = `${config.color}33`;

  // --- Confidence ---
  document.getElementById('confidenceValue').textContent = `${formatPercent(data.confidence)}%`;

  // --- Risk Badge ---
  const riskBadge = document.getElementById('riskBadge');
  const riskClass = data.risk_level.toLowerCase();
  riskBadge.classList.add('risk-' + riskClass);
  document.getElementById('riskIcon').textContent = data.risk_icon;
  document.getElementById('riskValue').textContent = data.risk_level.toUpperCase();

  // --- Metadata ---
  document.getElementById('metaLocation').textContent = data.location;
  document.getElementById('metaTime').textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // --- Description Preview ---
  document.getElementById('descPreview').textContent = '"' + data.description_preview + '"';

  // --- Actions List ---
  const actionsList = document.getElementById('actionsList');
  data.actions.forEach((action, i) => {
    const li = document.createElement('li');
    li.className = 'action-item';
    li.style.animationDelay = (i * 0.05) + 's';
    li.textContent = cleanActionText(action);

    actionsList.appendChild(li);
  });

  // --- Services List ---
  const servicesList = document.getElementById('servicesList');
  // Deduplicate services
  const uniqueServices = [...new Set(data.services)];
  uniqueServices.forEach(service => {
    const chip = document.createElement('div');
    chip.className = 'service-chip';
    const icon = SERVICE_ICONS[service] || 'S';
    chip.innerHTML = `<span>${icon}</span> ${service}`;
    servicesList.appendChild(chip);
  });

  // --- Location Note ---
  const locationNote = document.getElementById('locationNote');
  locationNote.innerHTML = `<span style="color:var(--accent-blue)">Location ${escapeHtml(data.location)}:</span> ${escapeHtml(data.location_note)}`;

  // --- Contacts ---
  const contactsList = document.getElementById('contactsList');
  // Deduplicate by number
  const seen = new Set();
  data.contacts.forEach(contact => {
    if (seen.has(contact.number)) return;
    seen.add(contact.number);

    const btn = document.createElement('a');
    btn.className = 'contact-btn';
    btn.href = `tel:${contact.number}`;
    btn.innerHTML = `
      <div class="contact-info">
        <span class="contact-name">${contact.name}</span>
        <span class="contact-number">${contact.number}</span>
      </div>
      <span class="contact-call-icon">CALL</span>
    `;
    contactsList.appendChild(btn);
  });

  // --- ML Breakdown Bars ---
  const mlBars = document.getElementById('mlBars');
  const maxScore = Math.max(...data.all_scores.map(s => s.confidence));

  data.all_scores.forEach((item, i) => {
    const cfg = INCIDENT_CONFIG[item.type] || { color: 'var(--accent-blue)' };
    const isWinner = item.type === data.incident_type;
    const pct = maxScore > 0 ? ((item.confidence / maxScore) * 100).toFixed(2) : 0;

    const div = document.createElement('div');
    div.className = 'ml-bar-item';
    div.innerHTML = `
      <div class="ml-bar-label">${item.type}</div>
      <div class="ml-bar-track">
        <div class="ml-bar-fill ${isWinner ? 'winner' : ''}"
             style="width:0%; background:${isWinner ? '' : cfg.color}"
             data-target="${pct}">
        </div>
      </div>
      <div class="ml-bar-pct">${formatPercent(item.confidence)}%</div>
    `;
    mlBars.appendChild(div);
  });

  // Animate bars after a short delay
  setTimeout(() => {
    document.querySelectorAll('.ml-bar-fill').forEach(bar => {
      bar.style.width = bar.dataset.target + '%';
    });
  }, 200);
}

function showNoDataMessage() {
  document.querySelector('.result-main').innerHTML = `
    <div style="text-align:center; padding: 5rem 2rem;">
      <div style="font-size:3rem; margin-bottom:1rem">Data</div>
      <h2 style="font-family:var(--font-display); font-size:1.5rem; margin-bottom:0.5rem">No Analysis Found</h2>
      <p style="color:var(--text-secondary); margin-bottom:2rem">It looks like you navigated here directly. Please submit an incident report first.</p>
      <a href="/report" class="btn-primary" style="display:inline-flex">Report an Incident</a>
    </div>
  `;
}

function shareReport() {
  const data = currentResult || JSON.parse(sessionStorage.getItem('aegisResult') || '{}');
  const text = `AEGIS Emergency Report\n` +
    `Incident: ${data.incident_type || 'Unknown'}\n` +
    `Risk Level: ${data.risk_level || 'Unknown'}\n` +
    `Location: ${data.location || 'Unknown'}\n` +
    `Emergency: Call 911`;

  if (navigator.share) {
    navigator.share({ title: 'Aegis Incident Report', text });
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      alert('Report copied to clipboard!');
    });
  }
}

function cleanActionText(action) {
  return String(action || '').replace(/^[^\w\d]+\s*/u, '').trim();
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatPercent(value) {
  const numericValue = Number(value) || 0;
  return percentFormatter.format(numericValue);
}

function buildScoresTableRows(scores = []) {
  return scores.map((score) => `
    <tr>
      <td>${escapeHtml(score.type)}</td>
      <td style="text-align:right;">${formatPercent(score.confidence)}%</td>
    </tr>
  `).join('');
}

function buildBarChartSvg(scores = []) {
  const safeScores = scores.slice(0, 5);
  const width = 860;
  const rowHeight = 44;
  const barStart = 220;
  const barMaxWidth = 520;
  const height = Math.max(180, safeScores.length * rowHeight + 36);

  const rows = safeScores.map((score, idx) => {
    const y = 28 + idx * rowHeight;
    const barWidth = Math.max(0, Math.min(barMaxWidth, (Number(score.confidence) || 0) * barMaxWidth / 100));

    return `
      <text x="20" y="${y + 16}" font-family="'IBM Plex Sans', Arial, sans-serif" font-size="14" fill="#0f172a">${escapeHtml(score.type)}</text>
      <rect x="${barStart}" y="${y}" width="${barMaxWidth}" height="16" rx="8" fill="#e2e8f0"></rect>
      <rect x="${barStart}" y="${y}" width="${barWidth.toFixed(2)}" height="16" rx="8" fill="#1d4ed8"></rect>
      <text x="${barStart + barMaxWidth + 20}" y="${y + 13}" font-family="'IBM Plex Sans', Arial, sans-serif" font-size="13" fill="#334155">${formatPercent(score.confidence)}%</text>
    `;
  }).join('');

  return `
    <svg width="100%" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Classification confidence chart">
      <rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"></rect>
      ${rows}
    </svg>
  `;
}

function exportReport() {
  const data = currentResult || JSON.parse(sessionStorage.getItem('aegisResult') || '{}');
  if (!data || !data.incident_type) {
    alert('No report data found to export.');
    return;
  }

  const timestamp = new Date();
  const generatedAt = timestamp.toLocaleString();
  const datePart = timestamp.toISOString().slice(0, 10);
  const actionsHtml = (data.actions || []).map((action) => `<li>${escapeHtml(cleanActionText(action))}</li>`).join('');
  const servicesHtml = [...new Set(data.services || [])].map((service) => `<li>${escapeHtml(service)}</li>`).join('');
  const contactsHtml = (data.contacts || []).map((contact) => `
    <tr>
      <td>${escapeHtml(contact.name)}</td>
      <td>${escapeHtml(contact.number)}</td>
    </tr>
  `).join('');

  const chartSvg = buildBarChartSvg(data.all_scores || []);
  const tableRows = buildScoresTableRows(data.all_scores || []);

  const exportHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Aegis Professional Incident Report</title>
  <style>
    :root { color-scheme: light; }
    body {
      margin: 0;
      padding: 32px;
      font-family: 'IBM Plex Sans', Arial, sans-serif;
      color: #0f172a;
      background: #f8fafc;
    }
    .page {
      background: #ffffff;
      border: 1px solid #dbe2ea;
      border-radius: 16px;
      padding: 28px;
      box-shadow: 0 6px 22px rgba(15, 23, 42, 0.08);
      max-width: 1100px;
      margin: 0 auto;
    }
    h1, h2 { margin: 0 0 12px; }
    h1 { font-size: 28px; letter-spacing: 0.02em; }
    h2 { font-size: 18px; margin-top: 26px; }
    .meta-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 16px 0 20px;
    }
    .meta-card {
      background: #f8fafc;
      border: 1px solid #dbe2ea;
      border-radius: 10px;
      padding: 10px 12px;
    }
    .meta-card .k {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #475569;
      display: block;
      margin-bottom: 4px;
    }
    .meta-card .v {
      font-size: 15px;
      font-weight: 600;
      color: #0f172a;
    }
    .lead {
      border-left: 4px solid #1d4ed8;
      background: #eff6ff;
      padding: 10px 12px;
      border-radius: 8px;
      margin: 12px 0 0;
      color: #1e3a8a;
    }
    .section-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-top: 10px;
    }
    ul {
      margin: 10px 0 0 20px;
      padding: 0;
      line-height: 1.6;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 14px;
    }
    th, td {
      border-bottom: 1px solid #e2e8f0;
      padding: 8px;
      text-align: left;
    }
    th {
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.08em;
      color: #475569;
      background: #f8fafc;
    }
    .foot {
      margin-top: 20px;
      padding-top: 14px;
      border-top: 1px solid #dbe2ea;
      font-size: 12px;
      color: #475569;
    }
    @media print {
      body { background: #fff; padding: 0; }
      .page { border: none; border-radius: 0; box-shadow: none; max-width: 100%; }
    }
  </style>
</head>
<body>
  <div class="page">
    <h1>Aegis Professional Incident Report</h1>
    <div class="meta-grid">
      <div class="meta-card"><span class="k">Incident Type</span><span class="v">${escapeHtml(data.incident_type)}</span></div>
      <div class="meta-card"><span class="k">Risk Level</span><span class="v">${escapeHtml(data.risk_level)}</span></div>
      <div class="meta-card"><span class="k">Confidence</span><span class="v">${formatPercent(data.confidence)}%</span></div>
      <div class="meta-card"><span class="k">Location</span><span class="v">${escapeHtml(data.location)}</span></div>
    </div>
    <div class="lead">Generated: ${generatedAt}</div>

    <h2>Incident Description</h2>
    <p>${escapeHtml(data.description_preview || 'N/A')}</p>

    <h2>Recommended Actions and Services</h2>
    <div class="section-grid">
      <div>
        <strong>Immediate Actions</strong>
        <ul>${actionsHtml}</ul>
      </div>
      <div>
        <strong>Suggested Services</strong>
        <ul>${servicesHtml}</ul>
      </div>
    </div>

    <h2>Classification Confidence Chart</h2>
    ${chartSvg}

    <h2>Classification Data Table</h2>
    <table>
      <thead><tr><th>Incident Class</th><th style="text-align:right;">Confidence</th></tr></thead>
      <tbody>${tableRows}</tbody>
    </table>

    <h2>Emergency Contacts</h2>
    <table>
      <thead><tr><th>Service</th><th>Contact Number</th></tr></thead>
      <tbody>${contactsHtml}</tbody>
    </table>

    <div class="foot">Guidance generated by Aegis. In life-threatening situations, contact official emergency services immediately.</div>
  </div>
</body>
</html>`;

  const blob = new Blob([exportHtml], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `aegis-incident-report-${datePart}.html`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
