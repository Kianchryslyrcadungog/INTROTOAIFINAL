# AEGIS - Smart Incident Detection and Response Recommendation System

A web-based AI emergency guidance system using Naive Bayes classification and rule-based reasoning.

---

## Folder Structure

```
aegis/
├── app.py                  ← Flask backend (ML + Rules + API)
├── requirements.txt        ← Python dependencies
├── templates/
│   ├── landing.html        ← Landing/home page
│   ├── report.html         ← Incident input form
│   └── result.html         ← Analysis result display
└── static/
    ├── css/
    │   └── main.css        ← All styles
    └── js/
        ├── landing.js      ← Landing page animations
        ├── report.js       ← Form submission logic
        └── result.js       ← Result rendering logic
```

---

## Setup & Run

### 1. Install Python (3.8+)
Download from https://python.org

### 2. Install dependencies
```bash
pip install flask
```

### 3. Run the app
```bash
cd aegis
python app.py
```

### 4. Open in browser
Visit: http://localhost:5000

---

## How The AI Works

### Naive Bayes Classifier
- Trained on 40+ labeled incident descriptions
- Tokenizes input text into words
- Calculates probability: P(class | words) using Bayes' theorem
- Uses Laplace smoothing to handle unseen words
- Returns top class + confidence scores

### Forward Chaining Risk Engine
- Starts with base risk score per incident type
- Chains rules: checks for HIGH_RISK_KEYWORDS (+2 pts)
- Then checks MEDIUM_RISK_KEYWORDS (+1 pt)
- Location modifier: School/Highway add +1 pt
- Final decision: ≥5 = High, ≥3 = Medium, else = Low

### IF-THEN Rule Base
```
IF incident = Fire    → Evacuate + Fire Station + BFP (160)
IF incident = Accident → Hospital + Police + Traffic Management
IF incident = Medical → First Aid + Clinic + DOH (1555)
IF incident = Crime   → Police + Barangay Tanod
IF incident = Flood   → Evacuation Center + NDRRMC
```

### Location Mapping
```
School     → Clinic, Security, DepEd Emergency
Highway    → Highway Patrol, MMDA
Residential → Barangay Hall, Barangay Tanod
Downtown   → City Police, City Health Office
```

---

## API Endpoint

### POST /analyze
**Request:**
```json
{
  "description": "There is a fire and smoke everywhere",
  "location": "Residential"
}
```

**Response:**
```json
{
  "incident_type": "Fire",
  "confidence": 94.2,
  "risk_level": "High",
  "risk_color": "#ef4444",
  "actions": ["Evacuate immediately...", ...],
  "services": ["Fire Station", "Barangay Emergency Response"],
  "contacts": [{"name": "BFP", "number": "160"}, ...],
  "all_scores": [{"type": "Fire", "confidence": 94.2}, ...]
}
```

---

## Disclaimer
This system is for educational/guidance purposes only.
**Always call 911 in life-threatening emergencies.**
