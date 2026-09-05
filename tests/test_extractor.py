"""
Unit Tests for MedicalReportExtractor
Validates parsing of lab text, handling unreferenced tests,
preserving source snippets, and assigning categories.
"""

import unittest
from app.services.extractor import MedicalReportExtractor
from app.models import RangeStatus


class TestMedicalReportExtractor(unittest.TestCase):
    def test_parse_tabular_lab(self):
        sample_text = """
METROPOLITAN HOSPITAL LAB
Date: 2025-05-10
TEST NAME                    RESULT   UNITS      REFERENCE RANGE
Hemoglobin                   14.5     g/dL       13.5 - 17.5
Fasting Blood Sugar          142      mg/dL      70 - 99
Troponin I                   0.01     ng/mL      
        """
        items = MedicalReportExtractor.parse_report_text("rep1", "pat1", sample_text, "2025-05-10")
        self.assertGreaterEqual(len(items), 3)

        # Check Hemoglobin
        hgb = next(it for it in items if "Hemoglobin" in it["test_name"])
        self.assertEqual(hgb["value"], "14.5")
        self.assertEqual(hgb["unit"], "g/dL")
        self.assertEqual(hgb["range_status"], RangeStatus.NORMAL)
        self.assertTrue(hgb["range_source_verified"])
        self.assertIn("14.5", hgb["source_snippet"])

        # Check Fasting Blood Sugar
        fbs = next(it for it in items if "Fasting Blood Sugar" in it["test_name"])
        self.assertIn(fbs["range_status"], [RangeStatus.HIGH, RangeStatus.CRITICAL_HIGH])

        # Check unreferenced Troponin I
        trop = next(it for it in items if "Troponin" in it["test_name"])
        self.assertEqual(trop["range_status"], RangeStatus.UNREFERENCED)
        self.assertFalse(trop["range_source_verified"])


if __name__ == "__main__":
    unittest.main()
