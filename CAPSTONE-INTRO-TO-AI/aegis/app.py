"""
Aegis: Smart Incident Detection and Response Recommendation System
Flask Backend with scikit-learn Naive Bayes + Rule-Based Reasoning
"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import joblib
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

MODEL_PATH = Path(__file__).with_name("incident_model.pkl")
VECTORIZER_PATH = Path(__file__).with_name("vectorizer.pkl")
DATABASE_PATH = Path(__file__).with_name("aegis.db")


def load_artifact(file_path):
    if not file_path.exists():
        return None
    return joblib.load(file_path)


model = load_artifact(MODEL_PATH)
vectorizer = load_artifact(VECTORIZER_PATH)

if model is None or vectorizer is None:
    print("Model artifacts not found. Run train_model.py to generate incident_model.pkl and vectorizer.pkl.")
else:
    print("Scikit-learn model loaded successfully.")
    print(f"   Model: {MODEL_PATH.name}")
    print(f"   Vectorizer: {VECTORIZER_PATH.name}")


def init_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                incident_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                risk_level TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_analysis(description, location, incident_type, confidence, risk_level):
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO analysis_reports (
                description,
                location,
                incident_type,
                confidence,
                risk_level,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (description, location, incident_type, confidence, risk_level, created_at),
        )
        connection.commit()


init_database()

# ============================================================
# RULE-BASED SYSTEM (Forward Chaining)
# Determines risk level and recommended actions based on
# incident type and location context
# ============================================================

# Risk keywords — presence of these raises risk level
HIGH_RISK_KEYWORDS = [
    'trapped', 'unconscious', 'bleeding', 'explosion', 'gunshot',
    'stabbing', 'overdose', 'collapsed', 'stroke', 'heart attack',
    'not breathing', 'seizing', 'anaphylaxis', 'dam', 'surge',
    'spreading', 'multiple', 'pileup', 'kidnapping', 'shooting'
]

MEDIUM_RISK_KEYWORDS = [
    'injured', 'accident', 'fire', 'flood', 'crime', 'assault',
    'collision', 'rising water', 'robbery', 'seizure', 'unconscious',
    'alarm', 'smoke', 'theft', 'overdose', 'burst', 'crash'
]

# IF-THEN Rule Base
# Format: { incident_type: { rules } }
RULE_BASE = {
    "Fire": {
        "actions": [
            "🚨 Immediately evacuate all occupants from the building",
            "📞 Call the Bureau of Fire Protection (BFP) at 160",
            "🔴 Do NOT use elevators — use emergency stairwells",
            "💨 Stay low to avoid smoke inhalation",
            "🚪 Close doors behind you to slow fire spread",
            "🧯 Use fire extinguisher ONLY if fire is small and contained",
            "🏃 Move to the designated assembly point",
        ],
        "services": ["Fire Station", "Barangay Emergency Response", "Red Cross"],
        "contacts": [
            {"name": "Bureau of Fire Protection", "number": "160"},
            {"name": "Red Cross", "number": "143"},
            {"name": "Emergency Hotline", "number": "911"},
        ]
    },
    "Accident": {
        "actions": [
            "🚑 Call an ambulance immediately — do NOT move injured persons",
            "⚠️ Set up warning signs / hazard lights to prevent secondary accidents",
            "🩹 Apply first aid if you are trained to do so",
            "📞 Report to the nearest police station",
            "🚧 Clear the area of bystanders",
            "📸 Document the scene for insurance/legal purposes",
            "🛑 Do NOT leave the scene until authorities arrive",
        ],
        "services": ["Hospital", "Police Station", "Traffic Management"],
        "contacts": [
            {"name": "Emergency Ambulance", "number": "911"},
            {"name": "Philippine National Police", "number": "117"},
            {"name": "Traffic Management Group", "number": "(02) 8523-0303"},
        ]
    },
    "Medical": {
        "actions": [
            "🏥 Transport patient to the nearest hospital immediately",
            "🫀 Perform CPR if the person is unresponsive and not breathing",
            "💊 Do NOT give food, water, or medication without doctor's advice",
            "🩸 Apply pressure to stop any bleeding",
            "📞 Call emergency services and describe symptoms clearly",
            "🧘 Keep the patient calm and still",
            "🌡️ Monitor vital signs until help arrives",
        ],
        "services": ["Clinic / Hospital", "Barangay Health Center", "Ambulance"],
        "contacts": [
            {"name": "Emergency Ambulance", "number": "911"},
            {"name": "DOH Emergency", "number": "1555"},
            {"name": "Red Cross Ambulance", "number": "143"},
        ]
    },
    "Crime": {
        "actions": [
            "🚔 Call the police immediately — do NOT confront suspects",
            "📍 Stay at a safe distance and observe from a safe location",
            "📝 Note suspect descriptions: clothing, height, direction of escape",
            "🎥 Do NOT tamper with evidence at the scene",
            "👤 Gather witness contact information if safe to do so",
            "🔒 Secure yourself in a safe location",
            "📞 Report to Barangay Tanod if police are unavailable",
        ],
        "services": ["Police Station", "Barangay Tanod", "CCTV Monitoring"],
        "contacts": [
            {"name": "Philippine National Police", "number": "117"},
            {"name": "PNP Hotline", "number": "8722-8888"},
            {"name": "Emergency Hotline", "number": "911"},
        ]
    },
    "Flood": {
        "actions": [
            "🏃 Evacuate immediately to higher ground — do NOT wait",
            "🎒 Bring emergency kit: food, water, documents, medicines",
            "⚡ Turn off electricity at main breaker before leaving",
            "🚗 Do NOT drive through floodwaters — turn around",
            "📻 Monitor PAGASA bulletins and local government advisories",
            "📞 Report to NDRRMC or local DRRM office",
            "🏫 Proceed to designated evacuation centers",
        ],
        "services": ["Evacuation Center", "NDRRMC", "Coast Guard (if coastal)"],
        "contacts": [
            {"name": "NDRRMC Operations Center", "number": "8911-1406"},
            {"name": "PAGASA", "number": "1555"},
            {"name": "Emergency Hotline", "number": "911"},
        ]
    }
}

# ============================================================
# LOCATION-BASED RECOMMENDATION MAPPING
# Adds location-specific services based on incident location
# ============================================================
LOCATION_MAP = {
    "School": {
        "additional_services": ["School Clinic", "School Security", "DepEd Emergency"],
        "note": "Contact school administration and activate school emergency plan.",
        "contacts": [
            {"name": "DepEd Emergency", "number": "(02) 8634-1072"},
            {"name": "School Security", "number": "Local Extension"},
        ]
    },
    "Highway": {
        "additional_services": ["Highway Patrol", "MMDA / DPWH", "Towing Service"],
        "note": "Highway incidents may involve multiple agencies. MMDA or LTO may assist.",
        "contacts": [
            {"name": "Highway Patrol Group", "number": "8706-3882"},
            {"name": "MMDA Hotline", "number": "136"},
        ]
    },
    "Residential": {
        "additional_services": ["Barangay Hall", "Homeowners Association", "Barangay Tanod"],
        "note": "Notify Barangay Captain immediately for community-level coordination.",
        "contacts": [
            {"name": "Barangay Emergency", "number": "Local Barangay"},
            {"name": "City Disaster Risk", "number": "Local DRRM"},
        ]
    },
    "Downtown": {
        "additional_services": ["City Police Precinct", "Mall Security", "City Health Office"],
        "note": "Downtown areas have denser resources. CCTV coverage may assist investigation.",
        "contacts": [
            {"name": "City Police", "number": "117"},
            {"name": "City Health Emergency", "number": "Local City Hall"},
        ]
    }
}

# ============================================================
# FORWARD CHAINING ENGINE
# Chains rules together to determine final risk level
# ============================================================
def determine_risk_level(incident_type, description, location):
    """
    Uses forward chaining to assess risk level.
    Chain: incident_type + keywords + location → risk_level
    """
    desc_lower = description.lower()
    risk_score = 0

    # Base risk from incident type
    base_risk = {
        "Fire": 2,
        "Accident": 2,
        "Medical": 2,
        "Crime": 1,
        "Flood": 2
    }
    risk_score += base_risk.get(incident_type, 1)

    # Forward chain: check for high-risk keywords
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in desc_lower:
            risk_score += 2
            break  # One is enough to push to high

    # Check for medium-risk keywords
    for keyword in MEDIUM_RISK_KEYWORDS:
        if keyword in desc_lower:
            risk_score += 1
            break

    # Location modifier
    if location == "School":
        risk_score += 1  # More vulnerable population
    elif location == "Highway":
        risk_score += 1  # Higher danger from traffic

    # Forward chaining decision
    if risk_score >= 5:
        return "High", "#ef4444", "🔴"
    elif risk_score >= 3:
        return "Medium", "#f59e0b", "🟡"
    else:
        return "Low", "#22c55e", "🟢"

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def landing():
    """Landing page"""
    return render_template('landing.html')

@app.route('/report')
def report():
    """Incident reporting page"""
    return render_template('report.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Main analysis endpoint.
    Receives incident description + location,
    runs ML classification + rule-based reasoning,
    returns structured result.
    """
    data = request.get_json()
    description = data.get('description', '').strip()
    location = data.get('location', 'Residential')

    if not description:
        return jsonify({"error": "Please provide an incident description."}), 400

    if model is None or vectorizer is None:
        return jsonify({"error": "Model artifacts are missing. Run train_model.py first."}), 500

    # Step 1: ML Classification (TF-IDF + Naive Bayes)
    description_tfidf = vectorizer.transform([description])
    predicted_label = model.predict(description_tfidf)[0]
    incident_type = str(predicted_label).strip().title()

    probabilities = model.predict_proba(description_tfidf)[0]
    class_scores = {
        str(label).strip().title(): float(probability)
        for label, probability in zip(model.classes_, probabilities)
    }
    confidence = class_scores.get(incident_type, max(class_scores.values()))

    # Step 2: Risk Assessment (Forward Chaining)
    risk_level, risk_color, risk_icon = determine_risk_level(incident_type, description, location)

    # Step 3: Apply IF-THEN Rules
    rules = RULE_BASE.get(incident_type, RULE_BASE["Medical"])

    # Step 4: Location-Based Recommendations
    location_info = LOCATION_MAP.get(location, LOCATION_MAP["Residential"])

    # Step 5: Combine all contacts
    all_contacts = rules["contacts"] + location_info["contacts"]

    # Prepare confidence scores for display
    sorted_scores = sorted(
        [{"type": label, "confidence": round(probability * 100, 1)} for label, probability in class_scores.items()],
        key=lambda x: x["confidence"],
        reverse=True
    )

    response_payload = {
        "incident_type": incident_type,
        "confidence": round(confidence * 100, 1),
        "risk_level": risk_level,
        "risk_color": risk_color,
        "risk_icon": risk_icon,
        "actions": rules["actions"],
        "services": rules["services"] + location_info["additional_services"],
        "contacts": all_contacts,
        "location_note": location_info["note"],
        "all_scores": sorted_scores,
        "location": location,
        "description_preview": description[:100] + "..." if len(description) > 100 else description
    }

    save_analysis(description, location, incident_type, round(confidence * 100, 1), risk_level)

    return jsonify(response_payload)

@app.route('/result')
def result():
    """Result page (renders the template; data filled by JS)"""
    return render_template('result.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
