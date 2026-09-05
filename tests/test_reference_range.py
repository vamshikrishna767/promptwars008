"""
Unit Tests for ReferenceRangeEvaluator
Validates that MedLens strictly evaluates reference ranges provided in source
and NEVER invents or assumes a range if absent.
"""

import unittest
from app.services.reference_range import ReferenceRangeEvaluator
from app.models import RangeStatus


class TestReferenceRangeEvaluator(unittest.TestCase):
    def test_interval_evaluation(self):
        # 70 - 99 mg/dL
        # Normal
        res_normal = ReferenceRangeEvaluator.evaluate(85.0, "85", "70 - 99")
        self.assertEqual(res_normal["range_status"], RangeStatus.NORMAL)
        self.assertTrue(res_normal["range_source_verified"])

        # High
        res_high = ReferenceRangeEvaluator.evaluate(126.0, "126", "70 - 99")
        self.assertEqual(res_high["range_status"], RangeStatus.HIGH)

        # Low
        res_low = ReferenceRangeEvaluator.evaluate(55.0, "55", "70 - 99")
        self.assertEqual(res_low["range_status"], RangeStatus.LOW)

    def test_upper_bound_cutoff(self):
        # < 100
        res_norm = ReferenceRangeEvaluator.evaluate(88.0, "88", "< 100")
        self.assertEqual(res_norm["range_status"], RangeStatus.NORMAL)

        res_high = ReferenceRangeEvaluator.evaluate(145.0, "145", "< 100")
        self.assertEqual(res_high["range_status"], RangeStatus.HIGH)

    def test_lower_bound_cutoff(self):
        # > 60 (e.g. eGFR)
        res_norm = ReferenceRangeEvaluator.evaluate(85.0, "85", "> 60")
        self.assertEqual(res_norm["range_status"], RangeStatus.NORMAL)

        res_low = ReferenceRangeEvaluator.evaluate(45.0, "45", "> 60")
        self.assertEqual(res_low["range_status"], RangeStatus.LOW)

    def test_qualitative_evaluation(self):
        res_neg = ReferenceRangeEvaluator.evaluate(None, "Negative", "Negative")
        self.assertEqual(res_neg["range_status"], RangeStatus.NORMAL)

        res_pos = ReferenceRangeEvaluator.evaluate(None, "Positive", "Negative")
        self.assertEqual(res_pos["range_status"], RangeStatus.HIGH)

    def test_strict_non_invention_of_ranges(self):
        # When reference range is None or empty string, system MUST NOT invent a range
        res_none = ReferenceRangeEvaluator.evaluate(15.2, "15.2", None)
        self.assertEqual(res_none["range_status"], RangeStatus.UNREFERENCED)
        self.assertFalse(res_none["range_source_verified"])
        self.assertIn("No reference range provided", res_none["note"])

        res_empty = ReferenceRangeEvaluator.evaluate(15.2, "15.2", "")
        self.assertEqual(res_empty["range_status"], RangeStatus.UNREFERENCED)
        self.assertFalse(res_empty["range_source_verified"])


if __name__ == "__main__":
    unittest.main()
