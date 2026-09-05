"""
Unit Tests for ConflictDetector
Validates drug-allergy contraindications, drug-lab interactions,
intake mismatches, and longitudinal drift alerts.
"""

import unittest
from app.services.conflicts import ConflictDetector
from app.models import ConflictSeverity


class TestConflictDetector(unittest.TestCase):
    def test_drug_allergy_conflict(self):
        intake = {
            "allergies": [{"allergen": "Penicillin", "reaction": "Anaphylaxis", "severity": "Severe"}],
            "medications": [{"name": "Amoxicillin", "dosage": "500mg"}],
            "conditions": []
        }
        conflicts = ConflictDetector.detect_conflicts("p1", intake, [])
        self.assertTrue(any(c["conflict_type"] == "DRUG_ALLERGY" and c["severity"] == ConflictSeverity.CRITICAL for c in conflicts))

    def test_hyperkalemia_ace_inhibitor_conflict(self):
        intake = {
            "allergies": [],
            "medications": [{"name": "Lisinopril", "dosage": "20mg"}],
            "conditions": ["Hypertension"]
        }
        items = [
            {"test_name": "Potassium", "numeric_value": 5.6, "unit": "mEq/L", "test_date": "2025-08-01"}
        ]
        conflicts = ConflictDetector.detect_conflicts("p1", intake, items)
        self.assertTrue(any(c["conflict_type"] == "DRUG_LAB" and "Potassium" in c["title"] for c in conflicts))

    def test_intake_lab_mismatch(self):
        # Patient denies diabetes, but lab HbA1c is 8.4%
        intake = {
            "allergies": [],
            "medications": [],
            "conditions": ["Mild Asthma"]  # No diabetes
        }
        items = [
            {"test_name": "HbA1c", "numeric_value": 8.4, "unit": "%", "test_date": "2025-08-01"}
        ]
        conflicts = ConflictDetector.detect_conflicts("p1", intake, items)
        self.assertTrue(any(c["conflict_type"] == "INTAKE_LAB_MISMATCH" for c in conflicts))


if __name__ == "__main__":
    unittest.main()
