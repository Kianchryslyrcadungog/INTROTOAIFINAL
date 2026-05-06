# Aegis: A Smart Incident Detection and Response Recommendation System

A web-based AI emergency guidance system that classifies incident reports, assigns risk levels, recommends actions, provides emergency contacts, and simulates location-based service guidance.

---

## Introduction

In emergency situations, timely and informed decision-making is essential. Aegis addresses this by combining machine learning and rule-based reasoning so users do not only report an incident, but also receive immediate guidance on what to do next.

The system includes:
- incident classification with machine learning
- stop-word filtered TF-IDF preprocessing
- rule-based recommendations
- simulated location-based service mapping
- emergency contact assistance
- local SQLite logging for analysis history

---

## Folder Structure

```
aegis/
├── app.py                  ← Flask backend (loads saved ML + rules + API)
├── train_model.py          ← TF-IDF + Naive Bayes training/evaluation script
├── requirements.txt        ← Python dependencies
├── aegis_kaggle_style_incident_dataset.csv
├── incident_model.pkl      ← Generated after training
├── vectorizer.pkl          ← Generated after training
├── aegis.db                ← Generated SQLite log database
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
pip install -r requirements.txt
```

### 3. Train the model
```bash
python train_model.py
```

This prints accuracy, precision, recall, and a classification report, then saves `incident_model.pkl` and `vectorizer.pkl`.

### 4. Run the app
```bash
cd aegis
python app.py
```

### 5. Open in browser
Visit: http://localhost:5000

---

## How The AI Works

### TF-IDF + Naive Bayes Classifier
- Uses `TfidfVectorizer(stop_words='english')` for preprocessing
- Trains `MultinomialNB` on the labeled dataset
- Reports accuracy, precision, recall, and a classification report
- Saves reusable model artifacts for Flask inference
- Accepts text-based incident reports from the web form

### Forward Chaining Risk Engine
- Starts with base risk score per incident type
- Chains rules: checks for HIGH_RISK_KEYWORDS (+2 pts)
- Then checks MEDIUM_RISK_KEYWORDS (+1 pt)
- Location modifier: School/Highway add +1 pt
- Final decision: ≥5 = High, ≥3 = Medium, else = Low

### Location-Based Recommendation System
- Uses predefined locations: School, Highway, Residential, Downtown
- Maps locations to nearby services such as clinics, hospitals, police, barangay units, and evacuation support
- Simulates GPS-style guidance without real-time location tracking

### Emergency Contact Assistance
- Displays clickable phone links where supported
- Includes predefined emergency numbers for police, fire, medical, and disaster response

### SQLite Logging
- Stores each analysis result locally in `aegis.db`
- Keeps a lightweight record of description, location, incident type, confidence, and risk level

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

## Scope and Limitations

### Scope
- Text-based incident reports
- Incident classes: Fire, Accident, Medical, Crime, Flood
- Risk level generation: Low, Medium, High
- Recommendations for actions, services, and contacts
- Simulated location-based guidance

### Limitations
- Small labeled dataset
- No real GPS or map API integration
- No live emergency service API integration
- Rules and contacts are predefined for academic use only

---

## Disclaimer
This system is for educational/guidance purposes only.
**Always call 911 in life-threatening emergencies.**
