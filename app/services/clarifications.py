"""
MedLens - Context-Aware Clinical Clarification Engine
Identifies ambiguities, missing clinical details, or conflicting data
and formulates targeted clarification prompts for the patient or provider.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime


class ClarificationEngine:
    @staticmethod
    def generate_questions(
        patient_id: str,
        intake: Optional[Dict[str, Any]],
        extracted_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        questions = []
        if not intake:
            intake = {}

        allergies = intake.get("allergies", [])
        medications = intake.get("medications", [])
        symptoms = intake.get("symptoms", [])

        # 1. Allergy Clarifications: Missing reaction nature or severity
        for a in allergies:
            allergen = a.get("allergen", "")
            reaction = a.get("reaction", "")
            if not reaction or reaction.lower() in ["unspecified", "unknown", ""]:
                questions.append({
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "category": "Allergy Safety",
                    "question": f"For your listed allergy to '{allergen}', what specific reaction did you experience?",
                    "rationale": "Differentiating IgE-mediated anaphylaxis/angioedema from mild intolerance is vital for safe antimicrobial prescribing.",
                    "answered": False,
                    "answer": None
                })

        # 2. Medication Clarifications: Missing dosage or frequency
        for m in medications:
            med_name = m.get("name", "")
            dosage = m.get("dosage", "")
            freq = m.get("frequency", "")
            if med_name and (not dosage or not freq):
                questions.append({
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "category": "Medication Reconciliation",
                    "question": f"What is your exact daily dosage and schedule for '{med_name}'?",
                    "rationale": "Precise dose reconciliation is required to assess therapeutic efficacy and avoid toxicity.",
                    "answered": False,
                    "answer": None
                })

        # 3. Lab Fasting Status Clarification
        has_lipid_or_glucose = any(
            any(k in item.get("test_name", "").lower() for k in ["fasting", "lipid", "triglyceride", "glucose"])
            for item in extracted_items
        )
        if has_lipid_or_glucose:
            questions.append({
                "id": str(uuid.uuid4()),
                "patient_id": patient_id,
                "category": "Pre-Analytical Accuracy",
                "question": "Were you strictly fasting (8–12 hours water only) prior to your blood specimen collection?",
                "rationale": "Non-fasting status can transiently elevate triglycerides and glucose, potentially skewing metabolic interpretations.",
                "answered": False,
                "answer": None
            })

        # 4. Temporal Gap Clarification for Key Chronic Markers
        # Check if latest HbA1c is older than 6 months
        hba1c_items = [it for it in extracted_items if "hba1c" in it.get("test_name", "").lower()]
        if hba1c_items:
            latest_hba1c = max(hba1c_items, key=lambda x: x.get("test_date") or "")
            tdate = latest_hba1c.get("test_date")
            if tdate:
                try:
                    d = datetime.strptime(tdate[:10], "%Y-%m-%d")
                    months_ago = (datetime.utcnow() - d).days / 30.0
                    if months_ago > 3.0:
                        questions.append({
                            "id": str(uuid.uuid4()),
                            "patient_id": patient_id,
                            "category": "Disease Monitoring",
                            "question": f"Your last recorded HbA1c ({latest_hba1c.get('value')}%) was on {tdate}. Has a more recent 3-month glycemic test been performed?",
                            "rationale": "Clinical guidelines recommend HbA1c monitoring every 3 months for active glycemic management.",
                            "answered": False,
                            "answer": None
                        })
                except Exception:
                    pass

        # 5. Symptom Onset Clarification
        for s in symptoms[:2]:
            questions.append({
                "id": str(uuid.uuid4()),
                "patient_id": patient_id,
                "category": "Symptom Assessment",
                "question": f"How long have you experienced '{s}', and is it constant or episodic?",
                "rationale": "Symptom chronicity helps the clinical team distinguish acute exacerbations from progressive chronic conditions.",
                "answered": False,
                "answer": None
            })

        return questions[:5]  # Limit to top 5 most actionable questions
