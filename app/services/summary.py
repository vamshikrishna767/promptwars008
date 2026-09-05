"""
MedLens - Clinical Information Summary Engine
Generates dual-perspective summaries:
1. Patient-Friendly Summary (plain language, educational, empowering)
2. Clinician Brief (concise, structured, highlighting abnormalities and conflicts)
STRICT RESPONSIBLE AI GUARDRAIL: No definitive diagnosis, no prescriptions, no dosage changes.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models import ClinicalSummary, RangeStatus


class ClinicalSummaryEngine:
    @staticmethod
    def generate_summary(
        patient: Dict[str, Any],
        intake: Optional[Dict[str, Any]],
        extracted_items: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        patient_name = patient.get("name", "Patient")
        age = patient.get("age", "")
        sex = patient.get("sex", "")

        intake = intake or {}
        symptoms = intake.get("symptoms", [])
        conditions = intake.get("conditions", [])
        allergies = intake.get("allergies", [])
        medications = intake.get("medications", [])

        # Categorize lab findings based on source reference ranges
        abnormal_items = [
            it for it in extracted_items 
            if it.get("range_status") in [RangeStatus.HIGH, RangeStatus.LOW, RangeStatus.CRITICAL_HIGH, RangeStatus.CRITICAL_LOW]
        ]
        normal_items = [it for it in extracted_items if it.get("range_status") == RangeStatus.NORMAL]
        unreferenced_items = [it for it in extracted_items if it.get("range_status") == RangeStatus.UNREFERENCED]

        critical_items = [
            it for it in extracted_items
            if it.get("range_status") in [RangeStatus.CRITICAL_HIGH, RangeStatus.CRITICAL_LOW]
        ]

        # -------------------------------------------------------------
        # 1. PATIENT-FRIENDLY SUMMARY GENERATION
        # -------------------------------------------------------------
        patient_summary_paragraphs = []

        # Intro
        patient_summary_paragraphs.append(
            f"Hello {patient_name}. MedLens has compiled and structured your latest medical records. "
            f"Here is an easy-to-read overview of your reported health information and laboratory tests."
        )

        # Symptoms & Medications overview
        symptom_str = ", ".join(symptoms) if symptoms else "None actively reported"
        med_count = len(medications)
        patient_summary_paragraphs.append(
            f"**Your Reported Health Background**: You reported symptoms including **{symptom_str}**, "
            f"with {len(conditions)} recorded medical conditions and {med_count} ongoing medications. "
            f"Allergies on file: {', '.join([a.get('allergen', '') for a in allergies]) if allergies else 'None reported'}."
        )

        # Lab Results Explanation
        if abnormal_items:
            abnormal_desc = []
            for item in abnormal_items[:5]:  # Top 5
                status_text = "higher than" if "HIGH" in item.get("range_status", "") else "lower than"
                abnormal_desc.append(
                    f"- **{item['test_name']}**: {item['value']} {item.get('unit','')}. This is {status_text} "
                    f"the reference range provided by the testing laboratory ({item.get('reference_range') or 'range indicated on report'})."
                )
            patient_summary_paragraphs.append(
                f"**Tests Outside Laboratory Reference Ranges**:\n" + "\n".join(abnormal_desc) + "\n\n"
                f"*Note: Having a result outside the reference range is common and does not automatically mean a disease. "
                f"Your healthcare provider will evaluate what these numbers mean in the context of your overall health.*"
            )
        else:
            patient_summary_paragraphs.append(
                f"**Laboratory Results**: All {len(normal_items)} evaluated laboratory tests were within the normal ranges specified by the laboratory."
            )

        # Questions to discuss with your doctor
        patient_summary_paragraphs.append(
            f"**Suggested Questions to Ask Your Doctor at Your Next Visit**:\n"
            f"1. *Do any of my laboratory values outside the laboratory reference range require follow-up or lifestyle changes?*\n"
            f"2. *Are all my active medications and supplements working well together with my latest test results?*\n"
            f"3. *When should my next routine blood tests or check-ups be scheduled?*"
        )

        patient_friendly_text = "\n\n".join(patient_summary_paragraphs)

        # -------------------------------------------------------------
        # 2. CLINICIAN BRIEF GENERATION
        # -------------------------------------------------------------
        clinician_sections = []

        allergy_strs = [f"{a.get('allergen')} ({a.get('reaction', 'unspecified')})" for a in allergies]
        allergy_summary = ", ".join(allergy_strs) if allergy_strs else "NKDA"
        med_strs = [f"{m.get('name', '')} {m.get('dosage', '')} {m.get('frequency', '')}".strip() for m in medications]
        med_summary = ", ".join(med_strs) if med_strs else "None listed"

        clinician_sections.append(
            f"### PATIENT PROFILE & SUBJECTIVE INTAKE\n"
            f"- **Demographics**: {patient_name}, {age}y {sex}\n"
            f"- **Active Complaints**: {', '.join(symptoms) if symptoms else 'None reported'}\n"
            f"- **Past History/Conditions**: {', '.join(conditions) if conditions else 'Unspecified'}\n"
            f"- **Documented Allergies**: {allergy_summary}\n"
            f"- **Active Pharmacotherapy**: {med_summary}"
        )

        # Objective Laboratory Findings
        abnormal_lines = [
            f"- **{it['test_name']}**: {it['value']} {it.get('unit','')} [Source Range: {it.get('reference_range') or 'None'}] -> **{it['range_status']}**"
            for it in abnormal_items
        ]
        clinician_sections.append(
            f"### OBJECTIVE LABORATORY HIGHLIGHTS ({len(extracted_items)} tests analyzed)\n"
            f"- **Abnormal Parameters ({len(abnormal_items)})**:\n  " +
            ("\n  ".join(abnormal_lines) if abnormal_lines else "  No abnormal values detected against source reference ranges.")
        )

        if unreferenced_items:
            clinician_sections.append(
                f"- **Unreferenced Parameters ({len(unreferenced_items)})**: " +
                ", ".join([f"{u['test_name']} ({u['value']} {u.get('unit','')})" for u in unreferenced_items[:4]]) +
                " *(Source report provided no reference bounds; status left unassumed)*"
            )

        # Safety Conflicts Section
        if conflicts:
            conflict_lines = [
                f"- **[{c['severity']}] {c['title']}**: {c['description']} *(Action: {c['recommendation']})*"
                for c in conflicts
            ]
            clinician_sections.append(
                f"### SAFETY & CONFLICT ALERTS ({len(conflicts)} detected)\n" +
                "\n".join(conflict_lines)
            )
        else:
            clinician_sections.append("### SAFETY & CONFLICT ALERTS\n- No acute drug-allergy or drug-lab contraindications identified.")

        clinician_brief_text = "\n\n".join(clinician_sections)

        key_findings = [
            {
                "test_name": it["test_name"],
                "value": f"{it['value']} {it.get('unit','')}".strip(),
                "status": it["range_status"],
                "reference_range": it.get("reference_range", "N/A"),
                "source": "Report Extracted"
            }
            for it in abnormal_items
        ]

        return {
            "patient_id": patient["id"],
            "patient_name": patient_name,
            "patient_friendly_summary": patient_friendly_text,
            "clinician_brief": clinician_brief_text,
            "key_findings": key_findings,
            "active_conflicts_count": len(conflicts),
            "total_tests_count": len(extracted_items),
            "abnormal_tests_count": len(abnormal_items),
            "disclaimer": (
                "CLINICAL DECISION SUPPORT NOTICE: MedLens is an information organization "
                "and assistance tool, not a diagnostic device or treatment authority. "
                "MedLens does not offer definitive medical diagnoses, prescribe medications, "
                "or recommend dosage changes. All summaries and conflict flags must be clinically "
                "validated by a licensed medical practitioner."
            ),
            "generated_at": datetime.utcnow().isoformat()
        }
