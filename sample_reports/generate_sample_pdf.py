"""
Script to generate sample PDF laboratory report for testing MedLens PDF parsing.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUT_PATH = os.path.join(os.path.dirname(__file__), "sample_lab_report.pdf")

doc = SimpleDocTemplate(OUT_PATH, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
styles = getSampleStyleSheet()

title_style = ParagraphStyle("T", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#0f766e"))
sub_style = ParagraphStyle("S", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#475569"))
cell_style = ParagraphStyle("C", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12)

story = [
    Paragraph("METROPOLITAN CLINICAL LABORATORIES", title_style),
    Paragraph("CLIA #45D0982314 | CAP Accredited | Specimen Date: 2025-08-25 | Report Date: 2025-08-25", sub_style),
    Paragraph("Patient Name: Sarah Jenkins | Age: 54 | Sex: Female | Ordering Provider: Dr. A. Vance", sub_style),
    Spacer(1, 10)
]

headers = ["TEST NAME", "RESULT", "UNITS", "REFERENCE RANGE", "FLAG"]
data = [headers]

rows = [
    ("Fasting Blood Sugar", "184", "mg/dL", "70 - 99", "HIGH"),
    ("HbA1c", "9.1", "%", "< 5.7", "HIGH"),
    ("Total Cholesterol", "238", "mg/dL", "< 200", "HIGH"),
    ("Triglycerides", "215", "mg/dL", "< 150", "HIGH"),
    ("HDL Cholesterol", "42", "mg/dL", "> 50", "LOW"),
    ("LDL Cholesterol", "153", "mg/dL", "< 100", "HIGH"),
    ("Serum Creatinine", "1.0", "mg/dL", "0.6 - 1.1", "NORMAL"),
    ("eGFR", "72", "mL/min", "> 60", "NORMAL"),
    ("Potassium", "4.6", "mEq/L", "3.5 - 5.1", "NORMAL"),
    ("ALT (SGPT)", "78", "U/L", "7 - 45", "HIGH"),
    ("AST (SGOT)", "58", "U/L", "8 - 40", "HIGH"),
    ("Troponin I", "0.01", "ng/mL", "", "")
]

for r in rows:
    data.append([Paragraph(x, cell_style) for x in r])

t = Table(data, colWidths=[160, 70, 70, 140, 80])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4)
]))

story.append(t)
doc.build(story)
print(f"Sample PDF created at: {OUT_PATH}")
