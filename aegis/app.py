"""
Aegis: Smart Incident Detection and Response Recommendation System
Flask Backend with Naive Bayes Classifier + Rule-Based Reasoning
"""

from flask import Flask, render_template, request, jsonify
import csv
import json
import math
from pathlib import Path
import re

app = Flask(__name__)

# ============================================================
# TRAINING DATA: Labeled incident descriptions
# Used to train our Naive Bayes classifier
# ============================================================
TRAINING_DATA = [
    # Fire incidents
    ("there is a fire in the building smoke everywhere", "Fire"),
    ("flames coming out of the kitchen burning smell", "Fire"),
    ("building is on fire people are trapped inside", "Fire"),
    ("smoke detected fire alarm is ringing", "Fire"),
    ("electrical fire short circuit sparks flames", "Fire"),
    ("forest fire spreading rapidly burning trees", "Fire"),
    ("house fire neighbor called firefighters", "Fire"),
    ("fire broke out in the warehouse explosion", "Fire"),

    # Accident incidents
    ("car crash collision two vehicles road accident", "Accident"),
    ("motorcycle accident hit by truck injured driver", "Accident"),
    ("vehicle collision highway multiple cars pileup", "Accident"),
    ("road accident injured passengers car overturned", "Accident"),
    ("bus accident crash passengers injured", "Accident"),
    ("bicycle hit by car road accident pedestrian", "Accident"),
    ("truck collision bridge accident road closed", "Accident"),
    ("car fell into ravine accident rescue needed", "Accident"),

    # Medical emergencies
    ("person unconscious not breathing heart attack", "Medical"),
    ("patient having seizure convulsions on the floor", "Medical"),
    ("severe chest pain difficulty breathing emergency", "Medical"),
    ("stroke symptoms face drooping arm weakness", "Medical"),
    ("overdose unconscious found unresponsive", "Medical"),
    ("diabetic emergency blood sugar very low", "Medical"),
    ("allergic reaction anaphylaxis swelling throat", "Medical"),
    ("person collapsed fainted pulse weak medical help", "Medical"),
    ("pregnant woman labor contractions giving birth", "Medical"),

    # Crime incidents
    ("robbery armed men stealing at gunpoint", "Crime"),
    ("burglary break in house theft stolen items", "Crime"),
    ("assault attack beating person injured", "Crime"),
    ("stabbing knife attack person bleeding", "Crime"),
    ("shooting gunshot heard people running", "Crime"),
    ("kidnapping person taken abducted missing", "Crime"),
    ("drug dealing suspicious activity neighborhood", "Crime"),
    ("vandalism property damage graffiti broken windows", "Crime"),
    ("sexual harassment assault victim needs help", "Crime"),

    # Flood incidents
    ("flooding rising water streets submerged", "Flood"),
    ("flood water entering houses evacuation needed", "Flood"),
    ("typhoon heavy rain flooding low lying areas", "Flood"),
    ("river overflowing flood warning issued", "Flood"),
    ("flash flood sudden water surge road blocked", "Flood"),
    ("storm surge coastal flooding people trapped", "Flood"),
    ("heavy rainfall flood stranded residents", "Flood"),
    ("dam overflow flooding downstream communities", "Flood"),
]

LABEL_TO_CLASS = {
    "fire": "Fire",
    "accident": "Accident",
    "medical": "Medical",
    "crime": "Crime",
    "flood": "Flood",
}

def load_training_data_from_csv(csv_path):
    """Load (text, label) rows from CSV using text + incident_label columns."""
    loaded = []

    if not csv_path.exists():
        return loaded

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            text = (row.get("text") or "").strip()
            raw_label = (row.get("incident_label") or "").strip().lower()
            label = LABEL_TO_CLASS.get(raw_label)

            if text and label:
                loaded.append((text, label))

    return loaded

# ============================================================
# NAIVE BAYES CLASSIFIER (TF-IDF Inspired)
# Classifies free-text incident reports into categories
# ============================================================
class NaiveBayesClassifier:
    def __init__(self):
        self.class_probs = {}       # P(class)
        self.word_probs = {}        # P(word | class)
        self.vocabulary = set()
        self.classes = []

    def tokenize(self, text):
        """Convert text to lowercase tokens, remove punctuation"""
        text = text.lower()
        text = re.sub(r'[^a-z\s]', '', text)
        return text.split()

    def train(self, data):
        """Train the Naive Bayes model on labeled data"""
        # Count occurrences
        class_counts = {}
        word_counts = {}

        for text, label in data:
            tokens = self.tokenize(text)
            class_counts[label] = class_counts.get(label, 0) + 1

            if label not in word_counts:
                word_counts[label] = {}

            for word in tokens:
                self.vocabulary.add(word)
                word_counts[label][word] = word_counts[label].get(word, 0) + 1

        # Calculate class probabilities P(class)
        total_docs = len(data)
        self.classes = list(class_counts.keys())
        self.class_probs = {
            cls: count / total_docs
            for cls, count in class_counts.items()
        }

        # Calculate word probabilities with Laplace smoothing P(word | class)
        vocab_size = len(self.vocabulary)
        self.word_probs = {}
        for cls in self.classes:
            total_words = sum(word_counts[cls].values())
            self.word_probs[cls] = {}
            for word in self.vocabulary:
                count = word_counts[cls].get(word, 0)
                # Laplace smoothing: add 1 to avoid zero probabilities
                self.word_probs[cls][word] = (count + 1) / (total_words + vocab_size)

    def predict(self, text):
        """Predict the class of a new text input"""
        tokens = self.tokenize(text)
        scores = {}

        for cls in self.classes:
            # Start with log of class probability
            score = math.log(self.class_probs[cls])

            for token in tokens:
                if token in self.word_probs[cls]:
                    score += math.log(self.word_probs[cls][token])
                # Unknown words: use a small smoothed probability
                else:
                    score += math.log(1 / (len(self.vocabulary) + 1))

            scores[cls] = score

        # Return the class with highest log-probability
        predicted = max(scores, key=scores.get)

        # Calculate confidence (normalized softmax-like)
        max_score = max(scores.values())
        exp_scores = {cls: math.exp(s - max_score) for cls, s in scores.items()}
        total = sum(exp_scores.values())
        confidence = exp_scores[predicted] / total

        return predicted, confidence, scores

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
            "Immediately evacuate all occupants from the building.",
            "Call the Bureau of Fire Protection (BFP) at 160.",
            "Do not use elevators; use emergency stairwells.",
            "Stay low to reduce smoke inhalation risk.",
            "Close doors behind you to slow fire spread.",
            "Use a fire extinguisher only if the fire is small and contained.",
            "Move to the designated assembly point and conduct a headcount.",
        ],
        "services": ["Fire Station", "Barangay Emergency Response", "Red Cross"],
        "contacts": [
            {"name": "KABACAN BFP", "number": "0910-048-9571"},
            {"name": "KABACAN PNP", "number": "0939-339-3168"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
        ]
    },
    "Accident": {
        "actions": [
            "Call an ambulance immediately; do not move injured persons unless necessary for safety.",
            "Set up warning signs or hazard lights to prevent secondary accidents.",
            "Apply first aid only if you are trained to do so.",
            "Report the incident to the nearest police station.",
            "Clear the area of bystanders and maintain a safe perimeter.",
            "Document the scene for insurance and legal purposes.",
            "Do not leave the scene until authorities arrive.",
        ],
        "services": ["Hospital", "Police Station", "Traffic Management"],
        "contacts": [
            {"name": "KABACAN PNP", "number": "0939-339-3168"},
            {"name": "KABACAN RHU", "number": "0926-397-0496"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
        ]
    },
    "Medical": {
        "actions": [
            "Transport the patient to the nearest hospital immediately.",
            "Perform CPR if the person is unresponsive and not breathing.",
            "Do not provide food, water, or medication without medical advice.",
            "Apply pressure to control active bleeding.",
            "Call emergency services and describe symptoms clearly.",
            "Keep the patient calm and still while waiting for responders.",
            "Monitor vital signs until professional help arrives.",
        ],
        "services": ["Clinic / Hospital", "Barangay Health Center", "Ambulance"],
        "contacts": [
            {"name": "Kabacan Polymedic Hospital", "number": "0645722063"},
            {"name": "KABACAN RHU", "number": "0926-397-0496"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
        ]
    },
    "Crime": {
        "actions": [
            "Call the police immediately and do not confront suspects.",
            "Stay at a safe distance and observe from a secure location.",
            "Record suspect descriptions, including clothing and direction of escape.",
            "Do not tamper with potential evidence at the scene.",
            "Gather witness contact information if safe to do so.",
            "Move yourself and others to a secure location.",
            "Report to Barangay Tanod if police services are unavailable.",
        ],
        "services": ["Police Station", "Barangay Tanod", "CCTV Monitoring"],
        "contacts": [
            {"name": "KABACAN PNP", "number": "0939-339-3168"},
            {"name": "KABACAN INFO", "number": "0926-402-0423"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
        ]
    },
    "Flood": {
        "actions": [
            "Evacuate immediately to higher ground without delay.",
            "Bring an emergency kit with food, water, documents, and medicines.",
            "Turn off electricity at the main breaker before leaving.",
            "Do not drive through floodwaters; turn around and reroute.",
            "Monitor PAGASA bulletins and local government advisories.",
            "Report the incident to NDRRMC or your local DRRM office.",
            "Proceed to designated evacuation centers.",
        ],
        "services": ["Evacuation Center", "NDRRMC", "Coast Guard (if coastal)"],
        "contacts": [
            {"name": "KABACAN MDRRM", "number": "0909-382-9939"},
            {"name": "KABACAN INFO", "number": "0926-402-0423"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
        ]
    }
}

# ============================================================
# LOCATION-BASED RECOMMENDATION MAPPING
# Adds location-specific services based on incident location
# ============================================================
LOCATION_MAP = {
    "School": {
        "additional_services": ["School Clinic", "School Security", "Barangay Emergency"],
        "note": "Contact school administration and activate school emergency plan.",
        "contacts": [
            {"name": "KABACAN INFO", "number": "0926-402-0423"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
        ]
    },
    "Highway": {
        "additional_services": ["Barangay Emergency Response", "Traffic Management", "Towing Service"],
        "note": "Highway incidents may involve multiple agencies. Local authorities may assist.",
        "contacts": [
            {"name": "KABACAN PNP", "number": "0939-339-3168"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
        ]
    },
    "Residential": {
        "additional_services": ["Barangay Hall", "Homeowners Association", "Barangay Emergency"],
        "note": "Notify Barangay Captain immediately for community-level coordination.",
        "contacts": [
            {"name": "KABACAN INFO", "number": "0926-402-0423"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
        ]
    },
    "Downtown": {
        "additional_services": ["City Police Precinct", "Commercial Security", "City Health Office"],
        "note": "Downtown areas have denser resources. CCTV coverage may assist investigation.",
        "contacts": [
            {"name": "KABACAN PNP", "number": "0939-339-3168"},
            {"name": "USM SSMO", "number": "(064) 5722100"},
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
        return "High", "#dc2626", "H"
    elif risk_score >= 3:
        return "Medium", "#d97706", "M"
    else:
        return "Low", "#15803d", "L"

# ============================================================
# TRAIN THE MODEL ON STARTUP
# ============================================================
classifier = NaiveBayesClassifier()
CSV_DATA_PATH = Path(__file__).with_name("aegis_kaggle_style_incident_dataset.csv")
CSV_TRAINING_DATA = load_training_data_from_csv(CSV_DATA_PATH)

if CSV_TRAINING_DATA:
    # Merge CSV and built-in samples, removing duplicates while preserving order.
    merged_samples = []
    seen_samples = set()

    for text, label in CSV_TRAINING_DATA + TRAINING_DATA:
        key = (text.strip().lower(), label)
        if key not in seen_samples:
            seen_samples.add(key)
            merged_samples.append((text, label))

    training_samples = merged_samples
    training_source = f"combined CSV + built-in ({CSV_DATA_PATH.name})"
else:
    training_samples = TRAINING_DATA
    training_source = "built-in fallback dataset"

classifier.train(training_samples)
print("✅ Naive Bayes classifier trained successfully!")
print(f"   Source: {training_source}")
if CSV_TRAINING_DATA:
    print(f"   CSV samples: {len(CSV_TRAINING_DATA)}")
    print(f"   Built-in samples: {len(TRAINING_DATA)}")
print(f"   Samples: {len(training_samples)}")
print(f"   Classes: {classifier.classes}")
print(f"   Vocabulary size: {len(classifier.vocabulary)} words")

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

    # Step 1: ML Classification (Naive Bayes)
    incident_type, confidence, all_scores = classifier.predict(description)

    # Step 2: Risk Assessment (Forward Chaining)
    risk_level, risk_color, risk_icon = determine_risk_level(incident_type, description, location)

    # Step 3: Apply IF-THEN Rules
    rules = RULE_BASE.get(incident_type, RULE_BASE["Medical"])

    # Step 4: Location-Based Recommendations
    location_info = LOCATION_MAP.get(location, LOCATION_MAP["Residential"])

    # Step 5: Combine all contacts
    all_contacts = rules["contacts"] + location_info["contacts"]

    # Prepare confidence scores for display
    max_log_score = max(all_scores.values())
    stabilized_scores = {cls: math.exp(score - max_log_score) for cls, score in all_scores.items()}
    total_score = sum(stabilized_scores.values())
    normalized_scores = {
        cls: (value / total_score) * 100 if total_score else 0.0
        for cls, value in stabilized_scores.items()
    }

    sorted_scores = sorted(
        [{"type": cls, "confidence": round(prob, 2)} for cls, prob in normalized_scores.items()],
        key=lambda x: x["confidence"],
        reverse=True
    )

    return jsonify({
        "incident_type": incident_type,
        "confidence": round(confidence * 100, 2),
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
    })

@app.route('/result')
def result():
    """Result page (renders the template; data filled by JS)"""
    return render_template('result.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
