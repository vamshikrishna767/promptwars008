"""
MedLens - PDF Clinical Report Export Service
Generates professional, printable clinical documentation with:
- Patient demographics & intake details
- Laboratory results table with source reference ranges and status badges
- Inconsistency alerts and conflict warnings
- Traceability and audit notes
- Mandatory Responsible AI non-diagnostic disclaimer
"""

from io import BytesIO
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


class ClinicalPDFExporter:
    @staticmethod
    def generate_pdf(
        patient: Dict[str, Any],
        intake: Dict[str, Any],
        reports: List[Dict[str, Any]],
        items: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0f766e")  # Medical Teal
        text_dark = colors.HexColor("#1e293b")
        text_muted = colors.HexColor("#64748b")
        border_color = colors.HexColor("#cbd5e1")
        danger_color = colors.HexColor("#dc2626")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=primary_color
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=text_muted
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=primary_color,
            spaceBefore=8,
            spaceAfter=4
        )

        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=text_dark
        )

        disclaimer_style = ParagraphStyle(
            "DocDisclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#b91c1c")
        )

        story = []

        # 1. Header Banner
        header_data = [
            [
                Paragraph("<b>MEDLENS</b> <font size=11 color='#0f766e'>| Clinical Information Intelligence Record</font>", title_style),
                Paragraph(f"Generated: {summary.get('generated_at', '')[:10]}<br/>System: MedLens v2.0", subtitle_style)
            ]
        ]
        t_header = Table(header_data, colWidths=[400, 140])
        t_header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        story.append(t_header)
        story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=4, spaceAfter=8))

        # 2. Disclaimer Box
        disc_text = (
            "<b>MANDATORY CLINICAL NOTICE:</b> MedLens is an assistive clinical intelligence and documentation "
            "organization platform. It is <b>NOT</b> a diagnostic device or healthcare provider. MedLens does not "
            "provide definitive medical diagnoses, prescribe medications, or recommend treatment dosages. "
            "All findings, extractions, and conflict alerts must be reviewed and verified by a licensed clinician."
        )
        disc_table = Table([[Paragraph(disc_text, disclaimer_style)]], colWidths=[540])
        disc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f87171")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(disc_table)
        story.append(Spacer(1, 8))

        # 3. Patient Demographics & Intake
        story.append(Paragraph("1. PATIENT DEMOGRAPHICS & CLINICAL INTAKE (Source: Self-Reported / Intake)", section_heading))
        intake_allergies = ", ".join([a.get("allergen", "") for a in intake.get("allergies", [])]) or "None Reported"
        intake_meds = ", ".join([f"{m.get('name')} {m.get('dosage','')}".strip() for m in intake.get("medications", [])]) or "None Reported"
        intake_conds = ", ".join(intake.get("conditions", [])) or "None Reported"
        intake_symps = ", ".join(intake.get("symptoms", [])) or "None Reported"

        demo_data = [
            [
                Paragraph(f"<b>Patient Name:</b> {patient.get('name', 'N/A')}", body_style),
                Paragraph(f"<b>Age / Sex:</b> {patient.get('age', 'N/A')} yrs / {patient.get('sex', 'N/A')}", body_style),
                Paragraph(f"<b>Blood Group:</b> {patient.get('blood_group', 'N/A')}", body_style)
            ],
            [
                Paragraph(f"<b>Reported Symptoms:</b> {intake_symps}", body_style),
                Paragraph(f"<b>Known Conditions:</b> {intake_conds}", body_style),
                Paragraph(f"<b>Known Allergies:</b> <font color='#b91c1c'><b>{intake_allergies}</b></font>", body_style)
            ],
            [
                Paragraph(f"<b>Active Medications:</b> {intake_meds}", body_style),
                Paragraph(f"<b>Surgeries:</b> {', '.join(intake.get('surgeries', [])) or 'None'}", body_style),
                Paragraph(f"<b>Family History:</b> {', '.join(intake.get('family_history', [])) or 'None'}", body_style)
            ]
        ]
        demo_table = Table(demo_data, colWidths=[180, 180, 180])
        demo_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(demo_table)
        story.append(Spacer(1, 8))

        # 4. Clinical Inconsistency & Conflict Alerts
        if conflicts:
            story.append(Paragraph(f"2. SAFETY & INCONSISTENCY ALERTS ({len(conflicts)} Identified)", section_heading))
            conflict_rows = [["Severity", "Alert Title", "Clinical Description & Action"]]
            for c in conflicts:
                sev = c.get("severity", "WARNING")
                sev_color = "#dc2626" if sev == "CRITICAL" else "#d97706"
                conflict_rows.append([
                    Paragraph(f"<font color='{sev_color}'><b>{sev}</b></font>", body_style),
                    Paragraph(f"<b>{c.get('title','')}</b>", body_style),
                    Paragraph(f"{c.get('description','')}<br/><i>Action: {c.get('recommendation','')}</i>", body_style)
                ])
            c_table = Table(conflict_rows, colWidths=[65, 175, 300])
            c_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef2f2")),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(c_table)
            story.append(Spacer(1, 8))

        # 5. Laboratory Extractions with Source Reference Ranges
        story.append(Paragraph(f"3. EXTRACTED LABORATORY & DIAGNOSTIC RECORD ({len(items)} Items)", section_heading))
        lab_headers = ["Category", "Test Name", "Result", "Source Ref Range", "Status", "Verified"]
        lab_rows = [lab_headers]

        for it in items:
            status = it.get("range_status", "UNREFERENCED")
            status_color = "#16a34a" if status == "NORMAL" else ("#dc2626" if "HIGH" in status or "LOW" in status else "#475569")
            ver = it.get("verification_status", "UNREVIEWED")

            ref_str = it.get("reference_range")
            if not ref_str:
                ref_cell = "<font color='#64748b'>Not in source</font>"
            else:
                ref_cell = f"<b>{ref_str}</b>"

            lab_rows.append([
                Paragraph(f"<font color='#475569'>{it.get('category','General')}</font>", body_style),
                Paragraph(f"<b>{it.get('test_name','')}</b>", body_style),
                Paragraph(f"{it.get('value','')} {it.get('unit','')}", body_style),
                Paragraph(ref_cell, body_style),
                Paragraph(f"<font color='{status_color}'><b>{status}</b></font>", body_style),
                Paragraph(f"<font size=7>{ver}</font>", body_style)
            ])

        lab_table = Table(lab_rows, colWidths=[85, 150, 85, 100, 70, 50])
        lab_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(lab_table)
        story.append(Spacer(1, 8))

        # 6. Clinician Brief Summary
        story.append(Paragraph("4. CLINICIAN SYNTHESIS & REVIEW BRIEF", section_heading))
        brief_html = summary.get("clinician_brief", "").replace("\n", "<br/>")
        brief_box = Table([[Paragraph(brief_html, body_style)]], colWidths=[540])
        brief_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(brief_box)

        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data
