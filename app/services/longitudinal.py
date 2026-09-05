"""
MedLens - Longitudinal Report Comparison and Biomarker Delta Tracker
Aggregates laboratory biomarkers across sequential patient reports,
calculates percentage variations, tracks progression trends,
and provides contextual clinical interpretations.
"""

from typing import List, Dict, Any, Optional
from app.models import LongitudinalTrend, LongitudinalDataPoint, RangeStatus


# Biomarkers where an increase is clinically unfavorable vs favorable
TREND_RULES = {
    # Increase is unfavorable (higher is worse)
    "hba1c": "LOWER_IS_BETTER",
    "fasting blood sugar": "LOWER_IS_BETTER",
    "fasting glucose": "LOWER_IS_BETTER",
    "ldl": "LOWER_IS_BETTER",
    "total cholesterol": "LOWER_IS_BETTER",
    "triglycerides": "LOWER_IS_BETTER",
    "creatinine": "LOWER_IS_BETTER",
    "bun": "LOWER_IS_BETTER",
    "alt": "LOWER_IS_BETTER",
    "ast": "LOWER_IS_BETTER",
    "crp": "LOWER_IS_BETTER",
    "potassium": "NEUTRAL_RANGE",

    # Increase is favorable (higher is better)
    "egfr": "HIGHER_IS_BETTER",
    "hdl": "HIGHER_IS_BETTER",
    "hemoglobin": "NORMAL_RANGE",
    "platelets": "NORMAL_RANGE",
    "ferritin": "NORMAL_RANGE"
}


class LongitudinalTracker:
    @staticmethod
    def analyze_trends(
        extracted_items: List[Dict[str, Any]],
        reports: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        report_map = {r["id"]: r for r in reports}

        # Group items by test name
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for it in extracted_items:
            tname = it.get("test_name", "").strip()
            if it.get("numeric_value") is not None:
                grouped.setdefault(tname, []).append(it)

        trends = []

        for test_name, items in grouped.items():
            # Only include tests with at least one data point; multi-point tests show trends
            # Sort chronologically
            sorted_items = sorted(items, key=lambda x: (x.get("test_date") or "", x.get("updated_at") or ""))
            
            data_points = []
            for it in sorted_items:
                rep_title = report_map.get(it["report_id"], {}).get("title", "Lab Report")
                data_points.append({
                    "report_id": it["report_id"],
                    "report_title": rep_title,
                    "date": it.get("test_date") or "Unknown Date",
                    "value": it["numeric_value"],
                    "unit": it.get("unit", ""),
                    "range_status": it.get("range_status", RangeStatus.UNREFERENCED),
                    "reference_range": it.get("reference_range", "")
                })

            delta_pct = None
            delta_val = None
            formatted_change = "-"
            trend_dir = "STABLE"
            interpretation = "Single measurement recorded."

            if len(data_points) >= 2:
                v_first = data_points[0]["value"]
                v_last = data_points[-1]["value"]
                delta_val = round(v_last - v_first, 2)
                if v_first != 0:
                    delta_pct = round(((v_last - v_first) / v_first) * 100.0, 1)

                if delta_val > 0:
                    formatted_change = f"↑ {delta_val:g}"
                    trend_dir = "UP"
                elif delta_val < 0:
                    formatted_change = f"↓ {abs(delta_val):g}"
                    trend_dir = "DOWN"
                else:
                    formatted_change = "→ 0.0"
                    trend_dir = "STABLE"

                if abs(delta_pct or 0) < 3.0:
                    trend_dir = "STABLE"

                # Check clinical connotation
                low_name = test_name.lower()
                rule = "NEUTRAL_RANGE"
                for k, r in TREND_RULES.items():
                    if k in low_name:
                        rule = r
                        break

                if rule == "LOWER_IS_BETTER":
                    if trend_dir == "UP":
                        interpretation = f"Increased by {formatted_change} ({delta_pct:+.1f}%) across reports (Unfavorable progression - review therapy)."
                    elif trend_dir == "DOWN":
                        interpretation = f"Decreased by {formatted_change} ({delta_pct:+.1f}%) across reports (Favorable therapeutic response)."
                    else:
                        interpretation = "Biomarker remains stable across monitoring intervals."
                elif rule == "HIGHER_IS_BETTER":
                    if trend_dir == "DOWN":
                        interpretation = f"Decreased by {formatted_change} ({delta_pct:+.1f}%) across reports (Concerning decline - renal/lipid monitoring)."
                    elif trend_dir == "UP":
                        interpretation = f"Increased by {formatted_change} ({delta_pct:+.1f}%) across reports (Favorable improvement)."
                    else:
                        interpretation = "Biomarker remains stable across monitoring intervals."
                else:
                    sign = f"{delta_pct:+.1f}%" if delta_pct is not None else "0%"
                    interpretation = f"Longitudinal shift: {formatted_change} ({sign}). Evaluate within patient clinical context."

            category = sorted_items[0].get("category", "General Diagnostics")
            unit = sorted_items[0].get("unit", "")

            trends.append({
                "test_name": test_name,
                "category": category,
                "unit": unit,
                "data_points": data_points,
                "delta_value": delta_val,
                "formatted_change": formatted_change,
                "delta_percent": delta_pct,
                "trend_direction": trend_dir,
                "clinical_note": interpretation,
                "points_count": len(data_points)
            })

        # Sort multi-point tests first, then by name
        trends.sort(key=lambda x: (x["points_count"] < 2, x["test_name"]))
        return trends
