"""
Aegis: Smart Incident Detection and Response Recommendation System
Flask Backend with scikit-learn Naive Bayes + Rule-Based Reasoning
"""

from datetime import datetime, timezone
from io import BytesIO
import os
from pathlib import Path
import json
import re
import shutil
import sqlite3
from functools import wraps
from uuid import uuid4
from xml.sax.saxutils import escape

import joblib
from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "aegis-dev-secret-key")

MODEL_PATH = Path(__file__).with_name("incident_model.pkl")
VECTORIZER_PATH = Path(__file__).with_name("vectorizer.pkl")
LEGACY_DATABASE_PATH = Path(__file__).with_name("aegis.db")
DATABASE_PATH = Path(app.instance_path) / "aegis.db"
OWNER_ACCESS_CODE = os.environ.get("AEGIS_OWNER_CODE", "aegis-owner-2026")


def ensure_database_path():
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    if LEGACY_DATABASE_PATH.exists() and not DATABASE_PATH.exists():
        try:
            shutil.copy2(LEGACY_DATABASE_PATH, DATABASE_PATH)
        except OSError:
            pass


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


ensure_database_path()


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

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS report_exports (
                report_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                incident_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                risk_level TEXT NOT NULL,
                risk_color TEXT NOT NULL,
                risk_icon TEXT NOT NULL,
                actions_json TEXT NOT NULL,
                services_json TEXT NOT NULL,
                contacts_json TEXT NOT NULL,
                scores_json TEXT NOT NULL,
                location_note TEXT NOT NULL,
                description_preview TEXT NOT NULL,
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


def save_report_snapshot(report_id, payload):
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO report_exports (
                report_id,
                description,
                location,
                incident_type,
                confidence,
                risk_level,
                risk_color,
                risk_icon,
                actions_json,
                services_json,
                contacts_json,
                scores_json,
                location_note,
                description_preview,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                payload["description"],
                payload["location"],
                payload["incident_type"],
                payload["confidence"],
                payload["risk_level"],
                payload["risk_color"],
                payload["risk_icon"],
                json.dumps(payload["actions"]),
                json.dumps(payload["services"]),
                json.dumps(payload["contacts"]),
                json.dumps(payload["all_scores"]),
                payload["location_note"],
                payload["description_preview"],
                created_at,
            ),
        )
        connection.commit()


def clean_action_text(text):
    return re.sub(r'^[^A-Za-z0-9]+\s*', '', str(text)).strip()


def dedupe_items(items, key_fn=lambda item: item):
    seen = set()
    unique_items = []
    for item in items:
        key = key_fn(item)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items


def load_report_snapshot(report_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM report_exports WHERE report_id = ?",
            (report_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "report_id": row["report_id"],
        "description": row["description"],
        "location": row["location"],
        "incident_type": row["incident_type"],
        "confidence": row["confidence"],
        "risk_level": row["risk_level"],
        "risk_color": row["risk_color"],
        "risk_icon": row["risk_icon"],
        "actions": json.loads(row["actions_json"]),
        "services": json.loads(row["services_json"]),
        "contacts": json.loads(row["contacts_json"]),
        "all_scores": json.loads(row["scores_json"]),
        "location_note": row["location_note"],
        "description_preview": row["description_preview"],
        "created_at": row["created_at"],
    }


def owner_required(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        if not session.get("owner_authenticated"):
            return redirect(url_for("owner_login", next=request.path))
        return view_function(*args, **kwargs)

    return wrapper


def fetch_dashboard_data():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        total_reports = connection.execute("SELECT COUNT(*) AS count FROM analysis_reports").fetchone()["count"]
        total_exports = connection.execute("SELECT COUNT(*) AS count FROM report_exports").fetchone()["count"]

        incident_rows = connection.execute(
            """
            SELECT incident_type, COUNT(*) AS count
            FROM analysis_reports
            GROUP BY incident_type
            ORDER BY count DESC, incident_type ASC
            """
        ).fetchall()

        location_rows = connection.execute(
            """
            SELECT location, COUNT(*) AS count
            FROM analysis_reports
            GROUP BY location
            ORDER BY count DESC, location ASC
            """
        ).fetchall()

        risk_rows = connection.execute(
            """
            SELECT risk_level, COUNT(*) AS count
            FROM analysis_reports
            GROUP BY risk_level
            ORDER BY count DESC, risk_level ASC
            """
        ).fetchall()

        trend_rows = connection.execute(
            """
            SELECT date(created_at) AS day, COUNT(*) AS count
            FROM analysis_reports
            GROUP BY date(created_at)
            ORDER BY day ASC
            """
        ).fetchall()

        recent_reports = connection.execute(
            """
            SELECT description, location, incident_type, confidence, risk_level, created_at
            FROM analysis_reports
            ORDER BY created_at DESC
            LIMIT 10
            """
        ).fetchall()

        all_reports = connection.execute(
            """
            SELECT description, location, incident_type, confidence, risk_level, created_at
            FROM analysis_reports
            ORDER BY created_at DESC
            """
        ).fetchall()

    return {
        "summary": {
            "total_reports": total_reports,
            "total_exports": total_exports,
            "unique_incidents": len(incident_rows),
            "unique_locations": len(location_rows),
        },
        "incident_labels": [row["incident_type"] for row in incident_rows],
        "incident_values": [row["count"] for row in incident_rows],
        "location_labels": [row["location"] for row in location_rows],
        "location_values": [row["count"] for row in location_rows],
        "risk_labels": [row["risk_level"] for row in risk_rows],
        "risk_values": [row["count"] for row in risk_rows],
        "trend_labels": [row["day"] for row in trend_rows],
        "trend_values": [row["count"] for row in trend_rows],
        "recent_reports": [dict(row) for row in recent_reports],
        "all_reports": [dict(row) for row in all_reports],
    }


def build_dashboard_pdf(dashboard_data):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    def pdf_text(value):
        return escape(str(value)).replace("\n", "<br/>")

    def table_block(rows, widths):
        table = Table(rows, colWidths=widths, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce7f4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#10233f")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cfd9e6")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde5ef")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return table

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="AEGIS Owner Dashboard Export",
        author="AEGIS",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DashTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#10233f"),
        alignment=TA_LEFT,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="DashBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#24364f"),
    ))
    styles.add(ParagraphStyle(
        name="DashRight",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#173153"),
    ))

    story = []
    story.append(Paragraph("AEGIS Owner Dashboard Export", styles["DashTitle"]))
    story.append(Paragraph("Complete summary of system usage generated from stored incident analysis records.", styles["DashBody"]))
    story.append(Spacer(1, 8))

    summary = dashboard_data["summary"]
    summary_rows = [
        [Paragraph("Total Reports", styles["DashBody"]), Paragraph(pdf_text(summary["total_reports"]), styles["DashRight"]), Paragraph("PDF Exports", styles["DashBody"]), Paragraph(pdf_text(summary["total_exports"]), styles["DashRight"])],
        [Paragraph("Incident Types", styles["DashBody"]), Paragraph(pdf_text(summary["unique_incidents"]), styles["DashRight"]), Paragraph("Locations", styles["DashBody"]), Paragraph(pdf_text(summary["unique_locations"]), styles["DashRight"])],
    ]
    story.append(table_block(summary_rows, [34 * mm, 56 * mm, 34 * mm, 56 * mm]))
    story.append(Spacer(1, 8))

    incident_rows = [[Paragraph("Incident Type", styles["DashBody"]), Paragraph("Count", styles["DashBody"])] ]
    for label, value in zip(dashboard_data["incident_labels"], dashboard_data["incident_values"]):
        incident_rows.append([Paragraph(pdf_text(label), styles["DashBody"]), Paragraph(pdf_text(value), styles["DashRight"])])
    story.append(Paragraph("Incident Type Breakdown", styles["DashBody"]))
    story.append(table_block(incident_rows, [100 * mm, 100 * mm]))
    story.append(Spacer(1, 8))

    recent_rows = [[Paragraph("Date", styles["DashBody"]), Paragraph("Incident", styles["DashBody"]), Paragraph("Location", styles["DashBody"]), Paragraph("Confidence", styles["DashBody"]), Paragraph("Risk", styles["DashBody"])] ]
    for row in dashboard_data["all_reports"][:30]:
        recent_rows.append([
            Paragraph(pdf_text(row["created_at"]), styles["DashBody"]),
            Paragraph(pdf_text(row["incident_type"]), styles["DashBody"]),
            Paragraph(pdf_text(row["location"]), styles["DashBody"]),
            Paragraph(pdf_text(f'{row["confidence"]:.1f}%'), styles["DashRight"]),
            Paragraph(pdf_text(row["risk_level"]), styles["DashBody"]),
        ])
    story.append(Paragraph("All Stored Results (Latest 30)", styles["DashBody"]))
    story.append(table_block(recent_rows, [42 * mm, 40 * mm, 48 * mm, 28 * mm, 30 * mm]))

    def add_page_number(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d6dfeb"))
        canvas.line(doc_obj.leftMargin, 12 * mm, doc.width + doc_obj.leftMargin, 12 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#667a96"))
        canvas.drawString(doc_obj.leftMargin, 7.5 * mm, "AEGIS Owner Dashboard")
        canvas.drawRightString(doc_obj.pagesize[0] - doc_obj.rightMargin, 7.5 * mm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    return buffer


def build_pdf(report):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"AEGIS Report {report['report_id']}",
        author="AEGIS",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#10233f"),
        alignment=TA_LEFT,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#10233f"),
        spaceAfter=6,
        spaceBefore=10,
    ))
    styles.add(ParagraphStyle(
        name="MetaLabel",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=colors.HexColor("#5c6f8f"),
        leading=11,
    ))
    styles.add(ParagraphStyle(
        name="MetaValue",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=colors.HexColor("#1d2f49"),
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name="BodySmall",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=12,
        textColor=colors.HexColor("#24364f"),
    ))
    styles.add(ParagraphStyle(
        name="BodyCentered",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4b6079"),
    ))
    styles.add(ParagraphStyle(
        name="PctRight",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#173153"),
    ))

    def box_table(rows, widths):
        table = Table(rows, colWidths=widths, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f7fb")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cfd9e6")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde5ef")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return table

    def pdf_text(value):
        return escape(str(value)).replace("\n", "<br/>")

    story = []
    story.append(Paragraph("AEGIS Incident Analysis Report", styles["ReportTitle"]))
    story.append(Paragraph("Professional export prepared for presentation, documentation, and operations review.", styles["BodySmall"]))
    story.append(Spacer(1, 8))

    summary_rows = [
        [Paragraph("Incident Type", styles["MetaLabel"]), Paragraph(pdf_text(report["incident_type"]), styles["MetaValue"]), Paragraph("Risk Level", styles["MetaLabel"]), Paragraph(pdf_text(report["risk_level"].upper()), styles["MetaValue"])],
        [Paragraph("Confidence", styles["MetaLabel"]), Paragraph(pdf_text(f'{report["confidence"]:.1f}%'), styles["MetaValue"]), Paragraph("Location", styles["MetaLabel"]), Paragraph(pdf_text(report["location"]), styles["MetaValue"])],
        [Paragraph("Generated", styles["MetaLabel"]), Paragraph(pdf_text(report["created_at"].replace("T", " ").replace("+00:00", " UTC")), styles["MetaValue"]), Paragraph("Report ID", styles["MetaLabel"]), Paragraph(pdf_text(report["report_id"]), styles["MetaValue"])],
    ]
    summary = box_table(summary_rows, [30 * mm, 55 * mm, 30 * mm, 55 * mm])
    story.append(summary)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Reported Description", styles["SectionHeader"]))
    story.append(Paragraph(pdf_text(report["description"]), styles["BodySmall"]))

    story.append(Paragraph("Immediate Actions", styles["SectionHeader"]))
    action_rows = [[Paragraph("#", styles["MetaLabel"]), Paragraph("Recommended Action", styles["MetaLabel"])] ]
    for index, action in enumerate(report["actions"], start=1):
        cleaned_action = action
        for prefix in ["🚨 ", "📞 ", "🔴 ", "💨 ", "🚪 ", "🧯 ", "🏃 ", "🚑 ", "⚠️ ", "🩹 ", "📸 ", "🛑 ", "🏥 ", "🫀 ", "💊 ", "🩸 ", "🧘 ", "🌡️ ", "🔒 ", "📍 ", "👤 ", "🎥 "]:
            cleaned_action = cleaned_action.replace(prefix, "", 1)
        action_rows.append([Paragraph(pdf_text(index), styles["BodySmall"]), Paragraph(pdf_text(cleaned_action), styles["BodySmall"])])
    actions_table = box_table(action_rows, [12 * mm, 168 * mm])
    actions_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce7f4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#10233f")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    story.append(actions_table)

    story.append(Paragraph("Service Coverage", styles["SectionHeader"]))
    services_text = ", ".join(report["services"])
    story.append(Paragraph(pdf_text(services_text), styles["BodySmall"]))

    story.append(Paragraph("Emergency Contacts", styles["SectionHeader"]))
    contact_rows = [[Paragraph("Service", styles["MetaLabel"]), Paragraph("Number", styles["MetaLabel"])] ]
    for contact in report["contacts"]:
        contact_rows.append([
            Paragraph(pdf_text(contact["name"]), styles["BodySmall"]),
            Paragraph(pdf_text(contact["number"]), styles["BodySmall"]),
        ])
    story.append(box_table(contact_rows, [110 * mm, 70 * mm]))

    story.append(Paragraph("Classification Breakdown", styles["SectionHeader"]))
    score_rows = [[Paragraph("Incident", styles["MetaLabel"]), Paragraph("Confidence", styles["MetaLabel"]), Paragraph("Visual", styles["MetaLabel"])] ]
    max_score = max((item["confidence"] for item in report["all_scores"]), default=0) or 1
    for item in report["all_scores"]:
        pct = (item["confidence"] / max_score) * 100
        bar_width = max(2, int(pct / 5))
        score_label = pdf_text(item["type"])
        score_rows.append([
            Paragraph(score_label, styles["BodySmall"]),
            Paragraph(pdf_text(f'{item["confidence"]:.1f}%'), styles["PctRight"]),
            Paragraph(
                f'<font color="#5c6f8f">{score_label}</font><br/><font color="#1f4d82">{"█" * bar_width}</font>',
                styles["BodySmall"],
            ),
        ])
    story.append(box_table(score_rows, [60 * mm, 30 * mm, 90 * mm]))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "This report is generated automatically from the AEGIS incident analysis workflow and is intended for operational guidance only.",
        styles["BodyCentered"],
    ))

    def add_page_number(canvas, doc_obj):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d6dfeb"))
        canvas.line(doc_obj.leftMargin, 14 * mm, A4[0] - doc_obj.rightMargin, 14 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#667a96"))
        canvas.drawString(doc_obj.leftMargin, 9 * mm, "AEGIS Incident Analysis")
        canvas.drawRightString(A4[0] - doc_obj.rightMargin, 9 * mm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    return buffer


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
KABACAN_CONTACTS = {
    "PNP": {"name": "KABACAN PNP", "number": "0939-339-3168"},
    "BFP": {"name": "KABACAN BFP", "number": "0910-048-9571"},
    "MDRRM": {"name": "KABACAN MDRRM", "number": "0909-382-9939"},
    "RHU": {"name": "KABACAN RHU", "number": "0926-397-0496"},
    "INFO": {"name": "KABACAN INFO", "number": "0926-402-0423"},
    "HOSPITAL": {"name": "Kabacan Polymedic Hospital", "number": "064 572 2063"},
    "SSMO": {"name": "USM Security Services and Management Office (SSMO)", "number": "(064) 572 2100"},
}

RULE_BASE = {
    "Fire": {
        "actions": [
            "Immediately evacuate all occupants from the building",
            "Call the Bureau of Fire Protection (BFP) at 160",
            "Do NOT use elevators — use emergency stairwells",
            "Stay low to avoid smoke inhalation",
            "Close doors behind you to slow fire spread",
            "Use fire extinguisher ONLY if fire is small and contained",
            "Move to the designated assembly point",
        ],
        "services": ["Fire Station", "Barangay Emergency Response", "Red Cross"],
        "contacts": [
            KABACAN_CONTACTS["BFP"],
            KABACAN_CONTACTS["PNP"],
            KABACAN_CONTACTS["MDRRM"],
        ]
    },
    "Accident": {
        "actions": [
            "Call an ambulance immediately — do NOT move injured persons",
            "Set up warning signs / hazard lights to prevent secondary accidents",
            "Apply first aid if you are trained to do so",
            "Report to the nearest police station",
            "Clear the area of bystanders",
            "Document the scene for insurance/legal purposes",
            "Do NOT leave the scene until authorities arrive",
        ],
        "services": ["Hospital", "Police Station", "Traffic Management"],
        "contacts": [
            KABACAN_CONTACTS["RHU"],
            KABACAN_CONTACTS["HOSPITAL"],
            KABACAN_CONTACTS["PNP"],
        ]
    },
    "Medical": {
        "actions": [
            "Transport patient to the nearest hospital immediately",
            "Perform CPR if the person is unresponsive and not breathing",
            "Do NOT give food, water, or medication without doctor's advice",
            "Apply pressure to stop any bleeding",
            "Call emergency services and describe symptoms clearly",
            "Keep the patient calm and still",
            "Monitor vital signs until help arrives",
        ],
        "services": ["Clinic / Hospital", "Barangay Health Center", "Ambulance"],
        "contacts": [
            KABACAN_CONTACTS["RHU"],
            KABACAN_CONTACTS["HOSPITAL"],
            KABACAN_CONTACTS["INFO"],
        ]
    },
    "Crime": {
        "actions": [
            "Call the police immediately — do NOT confront suspects",
            "Stay at a safe distance and observe from a safe location",
            "Note suspect descriptions: clothing, height, direction of escape",
            "Do NOT tamper with evidence at the scene",
            "Gather witness contact information if safe to do so",
            "Secure yourself in a safe location",
            "Report to Barangay Tanod if police are unavailable",
        ],
        "services": ["Police Station", "Barangay Tanod", "CCTV Monitoring"],
        "contacts": [
            KABACAN_CONTACTS["PNP"],
            KABACAN_CONTACTS["SSMO"],
            KABACAN_CONTACTS["INFO"],
        ]
    },
    "Flood": {
        "actions": [
            "Evacuate immediately to higher ground — do NOT wait",
            "Bring emergency kit: food, water, documents, medicines",
            "Turn off electricity at main breaker before leaving",
            "Do NOT drive through floodwaters — turn around",
            "Monitor PAGASA bulletins and local government advisories",
            "Report to NDRRMC or local DRRM office",
            "Proceed to designated evacuation centers",
        ],
        "services": ["Evacuation Center", "NDRRMC", "Coast Guard (if coastal)"],
        "contacts": [
            KABACAN_CONTACTS["MDRRM"],
            KABACAN_CONTACTS["INFO"],
            KABACAN_CONTACTS["PNP"],
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
            KABACAN_CONTACTS["SSMO"],
            KABACAN_CONTACTS["INFO"],
        ]
    },
    "Highway": {
        "additional_services": ["Highway Patrol", "MMDA / DPWH", "Towing Service"],
        "note": "Highway incidents may involve multiple agencies. MMDA or LTO may assist.",
        "contacts": [
            KABACAN_CONTACTS["PNP"],
            KABACAN_CONTACTS["INFO"],
        ]
    },
    "Residential": {
        "additional_services": ["Barangay Hall", "Homeowners Association", "Barangay Tanod"],
        "note": "Notify Barangay Captain immediately for community-level coordination.",
        "contacts": [
            KABACAN_CONTACTS["MDRRM"],
            KABACAN_CONTACTS["INFO"],
        ]
    },
    "Downtown": {
        "additional_services": ["City Police Precinct", "Mall Security", "City Health Office"],
        "note": "Downtown areas have denser resources. CCTV coverage may assist investigation.",
        "contacts": [
            KABACAN_CONTACTS["PNP"],
            KABACAN_CONTACTS["HOSPITAL"],
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


@app.route('/owner/login', methods=['GET', 'POST'])
def owner_login():
    """Simple owner gate for analytics access."""
    error_message = None

    if request.method == 'GET' and session.get('owner_authenticated'):
        return redirect(request.args.get('next') or url_for('dashboard'))

    if request.method == 'POST':
        access_code = request.form.get('access_code', '').strip()
        if access_code == OWNER_ACCESS_CODE:
            session['owner_authenticated'] = True
            next_url = request.form.get('next') or request.args.get('next') or url_for('dashboard')
            return redirect(next_url)

        error_message = 'Invalid owner code.'

    return render_template('owner_login.html', error_message=error_message)


@app.post('/owner/logout')
def owner_logout():
    """Clear owner session."""
    session.pop('owner_authenticated', None)
    return redirect(url_for('landing'))


@app.route('/dashboard')
@owner_required
def dashboard():
    """Owner analytics dashboard with charts and usage summaries."""
    dashboard_data = fetch_dashboard_data()
    return render_template('dashboard.html', **dashboard_data)


@app.route('/dashboard/export-pdf')
@owner_required
def export_dashboard_pdf():
    """Export a PDF summary of all stored system results."""
    dashboard_data = fetch_dashboard_data()
    pdf_buffer = build_dashboard_pdf(dashboard_data)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='aegis-dashboard-export.pdf',
    )

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
    cleaned_actions = [clean_action_text(action) for action in rules["actions"]]

    # Step 4: Location-Based Recommendations
    location_info = LOCATION_MAP.get(location, LOCATION_MAP["Residential"])

    # Step 5: Combine all contacts
    all_contacts = dedupe_items(
        rules["contacts"] + location_info["contacts"],
        key_fn=lambda contact: (contact["name"], contact["number"]),
    )

    all_services = dedupe_items(rules["services"] + location_info["additional_services"])

    # Prepare confidence scores for display
    sorted_scores = sorted(
        [{"type": label, "confidence": round(probability * 100, 1)} for label, probability in class_scores.items()],
        key=lambda x: x["confidence"],
        reverse=True
    )

    report_id = uuid4().hex

    response_payload = {
        "report_id": report_id,
        "description": description,
        "incident_type": incident_type,
        "confidence": round(confidence * 100, 1),
        "risk_level": risk_level,
        "risk_color": risk_color,
        "risk_icon": risk_icon,
        "actions": cleaned_actions,
        "services": all_services,
        "contacts": all_contacts,
        "location_note": location_info["note"],
        "all_scores": sorted_scores,
        "location": location,
        "description_preview": description[:100] + "..." if len(description) > 100 else description
    }

    save_analysis(description, location, incident_type, round(confidence * 100, 1), risk_level)
    save_report_snapshot(report_id, response_payload)

    return jsonify(response_payload)

@app.route('/result')
def result():
    """Result page (renders the template; data filled by JS)"""
    return render_template('result.html')


@app.route('/export/<report_id>')
def export_report(report_id):
    report = load_report_snapshot(report_id)

    if report is None:
        abort(404)

    pdf_buffer = build_pdf(report)
    filename = f"aegis-report-{report_id}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
