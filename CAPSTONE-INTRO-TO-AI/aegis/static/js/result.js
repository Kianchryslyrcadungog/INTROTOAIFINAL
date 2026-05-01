/**
 * Aegis — Result Page JavaScript
 * Reads analysis data from sessionStorage and renders it dynamically
 */

// Incident type icons and colors
const INCIDENT_CONFIG = {
  "Fire":     { icon: "🔥", color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  "Accident": { icon: "🚗", color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  "Medical":  { icon: "🏥", color: "#06b6d4", bg: "rgba(6,182,212,0.1)" },
  "Crime":    { icon: "🚔", color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  "Flood":    { icon: "🌊", color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
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

// Load and render data
document.addEventListener('DOMContentLoaded', () => {
  const raw = sessionStorage.getItem('aegisResult');

  if (!raw) {
    // No data — redirect back to report
    showNoDataMessage();
    return;
  }

  const data = JSON.parse(raw);
  renderResult(data);
});

function renderResult(data) {
  const config = INCIDENT_CONFIG[data.incident_type] || INCIDENT_CONFIG["Medical"];

  // --- Type Banner ---
  document.getElementById('typeIcon').textContent = config.icon;
  document.getElementById('typeName').textContent = data.incident_type;

  // Style the type icon background
  const typeIconEl = document.getElementById('typeIcon');
  typeIconEl.style.background = config.bg;
  typeIconEl.style.border = `1px solid ${config.color}33`;

  // --- Confidence ---
  document.getElementById('confidenceValue').textContent = data.confidence + '%';

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
    li.textContent = action;

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
  locationNote.innerHTML = `<span style="color:var(--accent-blue)">Location ${data.location}:</span> ${data.location_note}`;

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
    const cfg = INCIDENT_CONFIG[item.type] || { icon: '?', color: 'var(--accent-blue)' };
    const isWinner = item.type === data.incident_type;
    const pct = maxScore > 0 ? ((item.confidence / maxScore) * 100).toFixed(1) : 0;

    const div = document.createElement('div');
    div.className = 'ml-bar-item';
    div.innerHTML = `
      <div class="ml-bar-label">${cfg.icon} ${item.type}</div>
      <div class="ml-bar-track">
        <div class="ml-bar-fill ${isWinner ? 'winner' : ''}"
             style="width:0%; background:${isWinner ? '' : cfg.color}"
             data-target="${pct}">
        </div>
      </div>
      <div class="ml-bar-pct">${item.confidence.toFixed(1)}%</div>
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
      <div style="font-size:3rem; margin-bottom:1rem">!</div>
      <h2 style="font-family:var(--font-display); font-size:1.5rem; margin-bottom:0.5rem">No Analysis Found</h2>
      <p style="color:var(--text-secondary); margin-bottom:2rem">It looks like you navigated here directly. Please submit an incident report first.</p>
      <a href="/report" class="btn-primary" style="display:inline-flex">! Report an Incident</a>
    </div>
  `;
}

function shareReport() {
  const data = JSON.parse(sessionStorage.getItem('aegisResult') || '{}');
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
