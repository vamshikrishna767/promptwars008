"""
MedLens - Strict Source-Based Reference Range Evaluator
Rule: The system MUST NOT invent reference ranges.
Only evaluates Low / Normal / High when an authentic reference interval
or cutoff was extracted directly from the source medical report.
"""

import re
from typing import Optional, Tuple, Dict, Any
from app.models import RangeStatus


class ReferenceRangeEvaluator:
    @staticmethod
    def parse_source_range(range_str: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Parses reference range text from the report.
        Supports:
        - "70 - 99" or "70.0-99.0" or "70 to 99"
        - "< 100" or "<= 5.7"
        - "> 60" or ">= 90"
        - Qualitative strings like "Negative", "Non-Reactive"
        Returns (low_bound, high_bound, qualitative_target)
        """
        if not range_str or not range_str.strip():
            return None, None, None

        cleaned = range_str.strip().replace("–", "-").replace("—", "-")

        # Range pattern: low - high
        interval_match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(?:-|to)\s*([0-9]+(?:\.[0-9]+)?)$", cleaned, re.IGNORECASE)
        if interval_match:
            try:
                low = float(interval_match.group(1))
                high = float(interval_match.group(2))
                return low, high, None
            except ValueError:
                pass

        # Upper bound only: < X or <= X
        upper_match = re.match(r"^(?:<|<=|less than)\s*([0-9]+(?:\.[0-9]+)?)$", cleaned, re.IGNORECASE)
        if upper_match:
            try:
                high = float(upper_match.group(1))
                return None, high, None
            except ValueError:
                pass

        # Lower bound only: > X or >= X
        lower_match = re.match(r"^(?:>|>=|greater than)\s*([0-9]+(?:\.[0-9]+)?)$", cleaned, re.IGNORECASE)
        if lower_match:
            try:
                low = float(lower_match.group(1))
                return low, None, None
            except ValueError:
                pass

        # Qualitative target (e.g. Negative, Non-Reactive)
        return None, None, cleaned

    @staticmethod
    def evaluate(
        numeric_value: Optional[float],
        text_value: str,
        source_reference_range: Optional[str]
    ) -> Dict[str, Any]:
        """
        Evaluates the value strictly against the source-provided reference range.
        If source_reference_range is absent or empty:
        Status is strictly UNREFERENCED. System will NEVER invent a range.
        """
        if not source_reference_range or not source_reference_range.strip():
            return {
                "range_status": RangeStatus.UNREFERENCED,
                "range_source_verified": False,
                "range_low": None,
                "range_high": None,
                "note": "No reference range provided in source document. Evaluation omitted to prevent false assumptions."
            }

        low, high, qualitative = ReferenceRangeEvaluator.parse_source_range(source_reference_range)

        # 1. Numeric evaluation
        if numeric_value is not None:
            if low is not None and high is not None:
                # Interval check
                if numeric_value < low:
                    # Critical low if < 70% of lower bound
                    is_critical = numeric_value < (low * 0.75) if low > 0 else False
                    return {
                        "range_status": RangeStatus.CRITICAL_LOW if is_critical else RangeStatus.LOW,
                        "range_source_verified": True,
                        "range_low": low,
                        "range_high": high,
                        "note": f"Value {numeric_value} is below source reference range ({low} - {high})"
                    }
                elif numeric_value > high:
                    # Critical high if > 1.4x of high bound
                    is_critical = numeric_value > (high * 1.4)
                    return {
                        "range_status": RangeStatus.CRITICAL_HIGH if is_critical else RangeStatus.HIGH,
                        "range_source_verified": True,
                        "range_low": low,
                        "range_high": high,
                        "note": f"Value {numeric_value} exceeds source reference range ({low} - {high})"
                    }
                else:
                    return {
                        "range_status": RangeStatus.NORMAL,
                        "range_source_verified": True,
                        "range_low": low,
                        "range_high": high,
                        "note": f"Value {numeric_value} falls within source reference range ({low} - {high})"
                    }

            elif high is not None and low is None:
                # Upper limit only (e.g. < 100)
                if numeric_value > high:
                    is_critical = numeric_value > (high * 1.5)
                    return {
                        "range_status": RangeStatus.CRITICAL_HIGH if is_critical else RangeStatus.HIGH,
                        "range_source_verified": True,
                        "range_low": None,
                        "range_high": high,
                        "note": f"Value {numeric_value} exceeds source cutoff (< {high})"
                    }
                else:
                    return {
                        "range_status": RangeStatus.NORMAL,
                        "range_source_verified": True,
                        "range_low": None,
                        "range_high": high,
                        "note": f"Value {numeric_value} is within source cutoff (< {high})"
                    }

            elif low is not None and high is None:
                # Lower limit only (e.g. > 60)
                if numeric_value < low:
                    is_critical = numeric_value < (low * 0.6)
                    return {
                        "range_status": RangeStatus.CRITICAL_LOW if is_critical else RangeStatus.LOW,
                        "range_source_verified": True,
                        "range_low": low,
                        "range_high": None,
                        "note": f"Value {numeric_value} is below source threshold (> {low})"
                    }
                else:
                    return {
                        "range_status": RangeStatus.NORMAL,
                        "range_source_verified": True,
                        "range_low": low,
                        "range_high": None,
                        "note": f"Value {numeric_value} meets source threshold (> {low})"
                    }

        # 2. Qualitative evaluation (e.g., Negative, Non-Reactive, Absent)
        norm_val = text_value.strip().lower()
        if qualitative:
            norm_target = qualitative.lower()
            if norm_val == norm_target or ("negative" in norm_target and "negative" in norm_val):
                return {
                    "range_status": RangeStatus.NORMAL,
                    "range_source_verified": True,
                    "range_low": None,
                    "range_high": None,
                    "note": f"Result matches source reference observation ({qualitative})"
                }
            elif "positive" in norm_val and "negative" in norm_target:
                return {
                    "range_status": RangeStatus.HIGH,
                    "range_source_verified": True,
                    "range_low": None,
                    "range_high": None,
                    "note": f"Reactive/Positive result differs from source reference ({qualitative})"
                }

        # Fallback if unparsable format but text exists
        return {
            "range_status": RangeStatus.UNREFERENCED,
            "range_source_verified": True,
            "range_low": low,
            "range_high": high,
            "note": f"Source reference text recorded: '{source_reference_range}', but automated bound comparison is indeterminate."
        }
