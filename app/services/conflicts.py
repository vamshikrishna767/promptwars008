"""
MedLens - Clinical Inconsistency and Conflict Detection Engine
Analyzes patient intake (allergies, medications, conditions) against
extracted laboratory reports and historical biomarker trajectories.
Flags Drug-Allergy conflicts, Drug-Lab contraindications, Intake-Lab mismatches,
and sharp historical drifts.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models import ConflictSeverity

# Common allergy and cross-reactivity families
DRUG_ALLERGY_MAP = {
    "penicillin": ["amoxicillin", "ampicillin", "augmentin", "penicillin", "piperacillin", "dicloxacillin"],
    "amoxicillin": ["amoxicillin", "ampicillin", "augmentin", "penicillin"],
    "sulfa": ["bactrim", "sulfamethoxazole", "septra", "sulfasalazine", "trimethoprim-sulfamethoxazole"],
    "nsaid": ["ibuprofen", "advil", "motrin", "naproxen", "aleve", "celecoxib", "meloxicam", "ketorolac", "aspirin"],
    "aspirin": ["aspirin", "bayer", "ecotrin", "ibuprofen", "naproxen"],
    "cephalosporin": ["cephalexin", "keflex", "cefdinir", "ceftriaxone", "cefuroxime"],
    "codeine": ["codeine", "tylenol 3", "tramadol", "morphine", "hydrocodone", "oxycodone"],
    "ace inhibitor": ["lisinopril", "enalapril", "ramipril", "benazepril", "captopril"]
}


class ConflictDetector:
    @staticmethod
    def detect_conflicts(
        patient_id: str,
        intake: Optional[Dict[str, Any]],
        extracted_items: List[Dict[str, Any]],
        all_reports: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        conflicts = []

        if not intake:
            intake = {}

        allergies = intake.get("allergies", [])
        medications = intake.get("medications", [])
        conditions = intake.get("conditions", [])

        # Normalize medications for matching
        active_med_names = [m.get("name", "").strip().lower() for m in medications if m.get("name")]

        # -------------------------------------------------------------
        # 1. DRUG - ALLERGY CONFLICTS (CRITICAL SEVERITY)
        # -------------------------------------------------------------
        for allergy in allergies:
            allergen_text = (allergy.get("allergen") or "").strip().lower()
            if not allergen_text:
                continue

            # Check direct match or class cross-reactivity
            for class_key, associated_meds in DRUG_ALLERGY_MAP.items():
                if class_key in allergen_text or any(med in allergen_text for med in associated_meds):
                    # Check if patient is taking any drug in this family
                    for med in active_med_names:
                        if any(med_name in med for med_name in associated_meds):
                            conflicts.append({
                                "id": str(uuid.uuid4()),
                                "patient_id": patient_id,
                                "conflict_type": "DRUG_ALLERGY",
                                "severity": ConflictSeverity.CRITICAL,
                                "title": f"Critical Allergy Conflict: {allergen_text.title()} vs {med.title()}",
                                "description": (
                                    f"Patient intake records an allergy to '{allergen_text}', "
                                    f"yet current active medications include '{med}'. "
                                    f"High risk of severe hypersensitivity or anaphylaxis."
                                ),
                                "recommendation": (
                                    f"Immediate clinician review required: Verify patient allergy history and "
                                    f"consider withholding '{med}' for a safe alternative."
                                ),
                                "source_entities": [f"Allergy: {allergen_text}", f"Medication: {med}"]
                            })

        # -------------------------------------------------------------
        # 2. DRUG - LAB CONTRAINDICATIONS & SAFETY LIMITS
        # -------------------------------------------------------------
        # Map latest test values
        latest_tests: Dict[str, Dict[str, Any]] = {}
        for item in sorted(extracted_items, key=lambda x: x.get("test_date") or "", reverse=True):
            test_key = item.get("test_name", "").strip().lower()
            if test_key not in latest_tests:
                latest_tests[test_key] = item

        # Helper to retrieve test value
        def get_val(test_substr: str) -> Optional[float]:
            for k, v in latest_tests.items():
                if test_substr in k:
                    return v.get("numeric_value")
            return None

        potassium_val = get_val("potassium")
        creatinine_val = get_val("creatinine")
        egfr_val = get_val("egfr") or get_val("gfr")
        alt_val = get_val("alt") or get_val("sgpt")
        ast_val = get_val("ast") or get_val("sgot")
        fasting_glucose = get_val("fasting") or get_val("glucose")
        hba1c = get_val("hba1c") or get_val("glycated")

        # Conflict 2A: Hyperkalemia + ACE Inhibitor / ARB / Spironolactone
        if potassium_val and potassium_val > 5.2:
            ace_arb_drugs = ["lisinopril", "enalapril", "ramipril", "losartan", "valsartan", "spironolactone"]
            found_ace = [m for m in active_med_names if any(d in m for d in ace_arb_drugs)]
            if found_ace:
                conflicts.append({
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "conflict_type": "DRUG_LAB",
                    "severity": ConflictSeverity.CRITICAL if potassium_val >= 5.5 else ConflictSeverity.WARNING,
                    "title": f"Elevated Potassium ({potassium_val} mEq/L) with RAAS Inhibitor",
                    "description": (
                        f"Latest potassium level is elevated at {potassium_val} mEq/L, while patient is prescribed "
                        f"'{', '.join(found_ace)}'. RAAS inhibitors decrease aldosterone and exacerbate hyperkalemia."
                    ),
                    "recommendation": (
                        "Urgent clinical correlation: recheck serum potassium, review renal panel, and consider dose adjustment or dietary modification."
                    ),
                    "source_entities": [f"Potassium: {potassium_val}", f"Medication: {', '.join(found_ace)}"]
                })

        # Conflict 2B: Severe Renal Impairment + Metformin
        if (egfr_val and egfr_val < 30) or (creatinine_val and creatinine_val > 2.0):
            found_metformin = [m for m in active_med_names if "metformin" in m or "glucophage" in m]
            if found_metformin:
                conflicts.append({
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "conflict_type": "DRUG_LAB",
                    "severity": ConflictSeverity.CRITICAL,
                    "title": "Renal Impairment Warning: Metformin with eGFR < 30 mL/min",
                    "description": (
                        f"Patient renal markers show eGFR of {egfr_val or 'Reduced'} / Creatinine {creatinine_val or 'Elevated'}. "
                        f"Patient is currently taking '{', '.join(found_metformin)}', carrying significant risk of lactic acidosis."
                    ),
                    "recommendation": (
                        "Evaluate immediate cessation or substitution of Metformin per KDIGO clinical renal guidelines."
                    ),
                    "source_entities": [f"Renal Lab: eGFR {egfr_val}", f"Medication: {', '.join(found_metformin)}"]
                })

        # Conflict 2C: High Transaminases + Statin Therapy
        if (alt_val and alt_val > 100) or (ast_val and ast_val > 100):
            statin_drugs = ["atorvastatin", "simvastatin", "rosuvastatin", "pravastatin", "lipitor", "crestor"]
            found_statins = [m for m in active_med_names if any(s in m for s in statin_drugs)]
            if found_statins:
                conflicts.append({
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "conflict_type": "DRUG_LAB",
                    "severity": ConflictSeverity.WARNING,
                    "title": f"Hepatic Transaminase Elevation with Statin Therapy",
                    "description": (
                        f"Elevated liver enzymes (ALT: {alt_val}, AST: {ast_val}) detected alongside "
                        f"active statin prescription '{', '.join(found_statins)}'."
                    ),
                    "recommendation": (
                        "Investigate etiology of transaminitis. Monitor liver function panel and evaluate statin dosing."
                    ),
                    "source_entities": [f"ALT/AST: {alt_val}/{ast_val}", f"Medication: {', '.join(found_statins)}"]
                })

        # Conflict 2D: Renal Decline + NSAID use
        if (egfr_val and egfr_val < 60) or (creatinine_val and creatinine_val > 1.4):
            nsaid_drugs = ["ibuprofen", "naproxen", "meloxicam", "celecoxib", "diclofenac", "advil"]
            found_nsaid = [m for m in active_med_names if any(n in m for n in nsaid_drugs)]
            if found_nsaid:
                conflicts.append({
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "conflict_type": "DRUG_LAB",
                    "severity": ConflictSeverity.WARNING,
                    "title": "Nephrotoxic Risk: Chronic NSAID with Impaired Renal Function",
                    "description": (
                        f"Patient shows compromised renal status (eGFR: {egfr_val} mL/min, Cr: {creatinine_val} mg/dL) "
                        f"while taking NSAID '{', '.join(found_nsaid)}', which inhibits renal prostaglandins."
                    ),
                    "recommendation": (
                        "Recommend replacing NSAIDs with non-nephrotoxic analgesics (e.g., acetaminophen) where appropriate."
                    ),
                    "source_entities": [f"eGFR: {egfr_val}", f"Medication: {', '.join(found_nsaid)}"]
                })

        # -------------------------------------------------------------
        # 3. INTAKE vs LAB REPORT MISMATCHES
        # -------------------------------------------------------------
        norm_conditions = [c.lower() for c in conditions]
        has_diabetes_condition = any("diabetes" in c or "t2d" in c or "t1d" in c for c in norm_conditions)

        if not has_diabetes_condition:
            if (hba1c and hba1c >= 6.5) or (fasting_glucose and fasting_glucose >= 126):
                conflicts.append({
                    "id": str(uuid.uuid4()),
                    "patient_id": patient_id,
                    "conflict_type": "INTAKE_LAB_MISMATCH",
                    "severity": ConflictSeverity.WARNING,
                    "title": "Unrecorded Condition: Glycemic Lab Findings without Diabetes History",
                    "description": (
                        f"Lab reports show diagnostic diabetic glycemic values (HbA1c: {hba1c}%, "
                        f"Glucose: {fasting_glucose} mg/dL), but patient intake does NOT record a history of Diabetes."
                    ),
                    "recommendation": (
                        "Clarify whether patient was recently diagnosed or if intake condition history is incomplete."
                    ),
                    "source_entities": [f"HbA1c: {hba1c}%", "Intake Conditions: No diabetes listed"]
                })

        # -------------------------------------------------------------
        # 4. HISTORICAL DRIFT / VOLATILITY CHECK
        # -------------------------------------------------------------
        # Check tests that appear multiple times across different dates
        grouped_by_test: Dict[str, List[Dict[str, Any]]] = {}
        for item in extracted_items:
            tname = item.get("test_name", "").strip()
            if item.get("numeric_value") is not None:
                grouped_by_test.setdefault(tname, []).append(item)

        for tname, items in grouped_by_test.items():
            if len(items) >= 2:
                # Sort chronologically
                sorted_items = sorted(items, key=lambda x: x.get("test_date") or "")
                first = sorted_items[0]
                latest = sorted_items[-1]
                v1 = first["numeric_value"]
                v2 = latest["numeric_value"]
                if v1 > 0:
                    pct_change = ((v2 - v1) / v1) * 100.0
                    # Significant rapid swing > 40%
                    if abs(pct_change) >= 40.0:
                        conflicts.append({
                            "id": str(uuid.uuid4()),
                            "patient_id": patient_id,
                            "conflict_type": "HISTORICAL_DRIFT",
                            "severity": ConflictSeverity.INFO if abs(pct_change) < 75 else ConflictSeverity.WARNING,
                            "title": f"Significant Longitudinal Shift: {tname} ({pct_change:+.1f}%)",
                            "description": (
                                f"{tname} changed from {v1} {first.get('unit','')} ({first.get('test_date','')}) "
                                f"to {v2} {latest.get('unit','')} ({latest.get('test_date','')}), a {pct_change:+.1f}% shift."
                            ),
                            "recommendation": (
                                f"Verify if clinical intervention, acute event, or lab methodology change accounts for this {tname} drift."
                            ),
                            "source_entities": [f"{first.get('test_date')}: {v1}", f"{latest.get('test_date')}: {v2}"]
                        })

        return conflicts
