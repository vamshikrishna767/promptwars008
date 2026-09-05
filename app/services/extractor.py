"""
MedLens - Medical Report Extraction Engine
Extracts structured laboratory and diagnostic items from PDF or raw text reports.
Retains exact source snippet for traceability and provenance.
Evaluates reference range strictly against source text.
"""

import re
import uuid
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
from io import BytesIO

from app.services.reference_range import ReferenceRangeEvaluator
from app.models import RangeStatus, VerificationStatus

# Clinical test dictionary for classification & normalization
TEST_CATEGORIES = {
    # Hematology
    "hemoglobin": "Hematology", "hgb": "Hematology", "hematocrit": "Hematology", "hct": "Hematology",
    "wbc": "Hematology", "white blood cell": "Hematology", "rbc": "Hematology", "red blood cell": "Hematology",
    "platelets": "Hematology", "platelet count": "Hematology", "mcv": "Hematology", "mch": "Hematology", "mchc": "Hematology",
    # Metabolic & Electrolytes
    "fasting blood sugar": "Metabolic", "fasting glucose": "Metabolic", "glucose": "Metabolic", "fbs": "Metabolic",
    "sodium": "Electrolytes", "potassium": "Electrolytes", "chloride": "Electrolytes", "calcium": "Metabolic",
    "bicarbonate": "Electrolytes", "co2": "Electrolytes", "magnesium": "Electrolytes",
    # Glycemic
    "hba1c": "Glycemic Control", "glycated hemoglobin": "Glycemic Control", "hemoglobin a1c": "Glycemic Control",
    # Renal
    "creatinine": "Renal", "serum creatinine": "Renal", "blood urea nitrogen": "Renal", "bun": "Renal",
    "egfr": "Renal", "gfr": "Renal", "uric acid": "Renal",
    # Lipids
    "total cholesterol": "Lipid Panel", "cholesterol": "Lipid Panel", "hdl": "Lipid Panel",
    "ldl": "Lipid Panel", "ldl cholesterol": "Lipid Panel", "triglycerides": "Lipid Panel", "vldl": "Lipid Panel",
    # Liver
    "alt": "Hepatic", "sgpt": "Hepatic", "ast": "Hepatic", "sgot": "Hepatic",
    "alkaline phosphatase": "Hepatic", "alp": "Hepatic", "total bilirubin": "Hepatic", "bilirubin": "Hepatic",
    "albumin": "Hepatic", "total protein": "Hepatic",
    # Thyroid
    "tsh": "Thyroid", "thyroid stimulating hormone": "Thyroid", "free t4": "Thyroid", "ft4": "Thyroid", "free t3": "Thyroid",
    # Iron & Inflammation
    "ferritin": "Iron & Ferritin", "serum iron": "Iron & Ferritin", "tibc": "Iron & Ferritin",
    "crp": "Inflammation", "c-reactive protein": "Inflammation", "esr": "Inflammation",
    # Urinalysis
    "urine protein": "Urinalysis", "urine glucose": "Urinalysis", "specific gravity": "Urinalysis"
}

# Equivalent Terminology Normalization Map (e.g. Hb -> Hemoglobin -> HGB)
TERMINOLOGY_NORMALIZATION = {
    "hb": ("Hemoglobin", "HGB"),
    "hgb": ("Hemoglobin", "HGB"),
    "hemoglobin": ("Hemoglobin", "HGB"),
    "hematocrit": ("Hematocrit", "HCT"),
    "hct": ("Hematocrit", "HCT"),
    "wbc": ("White Blood Cells (WBC)", "WBC"),
    "white blood cells": ("White Blood Cells (WBC)", "WBC"),
    "white blood cell count": ("White Blood Cells (WBC)", "WBC"),
    "rbc": ("Red Blood Cells (RBC)", "RBC"),
    "red blood cells": ("Red Blood Cells (RBC)", "RBC"),
    "platelets": ("Platelet Count (PLT)", "PLT"),
    "platelet count": ("Platelet Count (PLT)", "PLT"),
    "fasting blood sugar": ("Fasting Blood Sugar", "GLU-FAST"),
    "fasting glucose": ("Fasting Blood Sugar", "GLU-FAST"),
    "fbs": ("Fasting Blood Sugar", "GLU-FAST"),
    "glucose": ("Glucose", "GLU"),
    "hba1c": ("Hemoglobin A1c (HbA1c)", "A1C"),
    "glycated hemoglobin": ("Hemoglobin A1c (HbA1c)", "A1C"),
    "hemoglobin a1c": ("Hemoglobin A1c (HbA1c)", "A1C"),
    "creatinine": ("Serum Creatinine", "CREAT"),
    "serum creatinine": ("Serum Creatinine", "CREAT"),
    "blood urea nitrogen": ("Blood Urea Nitrogen (BUN)", "BUN"),
    "bun": ("Blood Urea Nitrogen (BUN)", "BUN"),
    "egfr": ("Estimated GFR (eGFR)", "EGFR"),
    "gfr": ("Estimated GFR (eGFR)", "EGFR"),
    "potassium": ("Potassium (K)", "K"),
    "sodium": ("Sodium (Na)", "NA"),
    "alt": ("ALT (SGPT)", "ALT"),
    "sgpt": ("ALT (SGPT)", "ALT"),
    "ast": ("AST (SGOT)", "AST"),
    "sgot": ("AST (SGOT)", "AST"),
    "ldl": ("LDL Cholesterol", "LDL"),
    "ldl cholesterol": ("LDL Cholesterol", "LDL"),
    "hdl": ("HDL Cholesterol", "HDL"),
    "hdl cholesterol": ("HDL Cholesterol", "HDL"),
    "total cholesterol": ("Total Cholesterol", "CHOL"),
    "triglycerides": ("Triglycerides", "TRIG"),
    "tsh": ("TSH (Thyroid Stimulating Hormone)", "TSH"),
    "free t4": ("Free Thyroxine (FT4)", "FT4"),
    "ft4": ("Free Thyroxine (FT4)", "FT4"),
    "ferritin": ("Serum Ferritin", "FERR"),
    "crp": ("C-Reactive Protein (CRP)", "CRP"),
    "high sensitivity crp": ("High Sensitivity CRP (hs-CRP)", "HS-CRP"),
    "troponin i": ("Troponin I", "TROP-I")
}


class MedicalReportExtractor:
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """Extracts text content page-by-page from PDF bytes."""
        try:
            reader = PdfReader(BytesIO(file_bytes))
            pages_text = []
            for idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(f"--- PAGE {idx + 1} ---\n" + text)
            return "\n\n".join(pages_text)
        except Exception as e:
            return f"Error extracting PDF: {str(e)}"

    @staticmethod
    def detect_report_date(text: str) -> str:
        """Extracts specimen or report collection date from document header."""
        date_patterns = [
            r"(?:Report\s*Date|Specimen\s*Date|Collection\s*Date|Date\s*of\s*Collection|Date)[:\s]+([0-9]{4}-[0-9]{2}-[0-9]{2})",
            r"(?:Report\s*Date|Specimen\s*Date|Collection\s*Date|Date\s*of\s*Collection|Date)[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
            r"([0-9]{4}-[0-9]{2}-[0-9]{2})",
            r"([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})"
        ]
        for pat in date_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                raw_date = m.group(1).strip()
                # Normalize slash date to standard format if possible
                if "/" in raw_date or "-" in raw_date:
                    parts = re.split(r"[/-]", raw_date)
                    if len(parts) == 3:
                        if len(parts[0]) == 4:  # YYYY-MM-DD
                            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                        elif len(parts[2]) == 4:  # MM-DD-YYYY or DD-MM-YYYY
                            return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                return raw_date
        return ""

    @staticmethod
    def detect_facility(text: str) -> str:
        """Detects medical facility or laboratory brand from header."""
        facility_match = re.search(r"(?:Laboratory|Hospital|Clinic|Health|Pathology|Diagnostics)[\w\s]{3,30}", text, re.IGNORECASE)
        if facility_match:
            return facility_match.group(0).strip()
        return "Clinical Diagnostic Laboratory"

    @staticmethod
    def assign_category(test_name: str) -> str:
        low = test_name.lower().strip()
        for key, cat in TEST_CATEGORIES.items():
            if key in low:
                return cat
        return "General Diagnostics"

    @classmethod
    def normalize_name(cls, raw_name: str) -> tuple:
        low = raw_name.lower().strip()
        if low in TERMINOLOGY_NORMALIZATION:
            return TERMINOLOGY_NORMALIZATION[low]
        for k, (canonical, code) in TERMINOLOGY_NORMALIZATION.items():
            if k == low or low.startswith(k + " ") or f"({k})" in low:
                return canonical, code
        return raw_name.strip(), ""

    @classmethod
    def parse_report_text(cls, report_id: str, patient_id: str, raw_text: str, default_date: str = "") -> List[Dict[str, Any]]:
        """
        Parses text and extracts structured lab items with provenance and source reference ranges.
        Handles both tabular and colon/key-value formats.
        """
        extracted = []
        detected_date = cls.detect_report_date(raw_text) or default_date
        lines = raw_text.splitlines()

        # Regex patterns for various lab report layouts:
        # Pattern 1: Tabular with explicit bounds
        # e.g.: Fasting Blood Sugar | 126 | mg/dL | 70 - 99 | High
        # e.g.: Hemoglobin  14.2  g/dL  13.5 - 17.5
        pat_tabular = re.compile(
            r"^([A-Za-z0-9\s,\(\)/%\.-]{3,35}?)\s{2,}[:=]?\s*"
            r"([><]?\s*[0-9]+(?:\.[0-9]+)?|[A-Za-z]+)\s+"
            r"([a-zA-Z/%0-9\.\^]+)?\s+"
            r"(?:(?:Ref[:\s]*|Reference[:\s]*|Normal[:\s]*)?([0-9]+(?:\.[0-9]+)?\s*-\s*[0-9]+(?:\.[0-9]+)?|[><]=?\s*[0-9]+(?:\.[0-9]+)?|Negative|Normal))",
            re.IGNORECASE
        )

        # Pattern 2: Key-value with bracketed reference range
        # e.g.: Serum Creatinine: 1.6 mg/dL (Ref: 0.7 - 1.3 mg/dL)
        pat_keyval = re.compile(
            r"^([A-Za-z0-9\s,\(\)/%\.-]{3,35}?)\s*[:=]\s*"
            r"([0-9]+(?:\.[0-9]+)?|[A-Za-z]+)\s*"
            r"([a-zA-Z/%0-9\.\^]+)?\s*"
            r"(?:\((?:Ref|Reference|Range)?[:\s]*([^\)]+)\))?",
            re.IGNORECASE
        )

        # Pattern 3: Simple test line without reference range (either colon or multi-space)
        # e.g.: Troponin I: 0.04 ng/mL or Troponin I    0.01    ng/mL
        pat_no_range = re.compile(
            r"^([A-Za-z0-9\s,\(\)/%\.-]{3,35}?)(?:\s*[:=]\s*|\s{2,})([0-9]+(?:\.[0-9]+)?|[A-Za-z]+)\s*([a-zA-Z/%0-9\.\^]+)?$",
            re.IGNORECASE
        )

        seen_tests = set()
        page_num = 1

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("--- PAGE"):
                if "PAGE" in line_str:
                    try:
                        page_num = int(re.search(r"PAGE\s*(\d+)", line_str).group(1))
                    except Exception:
                        pass
                continue

            test_name = None
            val_str = None
            unit_str = ""
            ref_str = None
            confidence = 0.95

            # Try Tabular
            m1 = pat_tabular.search(line_str)
            if m1:
                test_name = m1.group(1).strip()
                val_str = m1.group(2).strip()
                unit_str = (m1.group(3) or "").strip()
                ref_str = (m1.group(4) or "").strip()
                confidence = 0.96
            else:
                # Try Key-Value
                m2 = pat_keyval.search(line_str)
                if m2:
                    test_name = m2.group(1).strip()
                    val_str = m2.group(2).strip()
                    unit_str = (m2.group(3) or "").strip()
                    ref_str = (m2.group(4) or "").strip() if m2.group(4) else None
                    confidence = 0.92 if ref_str else 0.88
                else:
                    # Try No-range
                    m3 = pat_no_range.search(line_str)
                    if m3:
                        test_name = m3.group(1).strip()
                        val_str = m3.group(2).strip()
                        unit_str = (m3.group(3) or "").strip()
                        ref_str = None
                        confidence = 0.85

            # Filter out non-test lines (headers, phone numbers, addresses)
            if test_name:
                low_name = test_name.lower()
                invalid_tokens = ["patient", "doctor", "dr.", "date", "hospital", "clinic", "phone", "address", "page", "specimen", "id", "mrn", "test name", "collected"]
                if any(inv == low_name or low_name.startswith(inv + " ") or low_name.startswith(inv + ":") for inv in invalid_tokens):
                    continue

                # Clean test name
                test_name = re.sub(r"\s+", " ", test_name).strip(" :-")
                if len(test_name) < 2 or test_name in seen_tests:
                    continue

                seen_tests.add(test_name)

                # Parse numeric value if possible
                num_val = None
                try:
                    num_val = float(re.sub(r"[^0-9\.]", "", val_str))
                except (ValueError, TypeError):
                    num_val = None

                # Strict source-only reference range evaluation
                eval_result = ReferenceRangeEvaluator.evaluate(
                    numeric_value=num_val,
                    text_value=val_str,
                    source_reference_range=ref_str
                )

                canonical_name, std_code = cls.normalize_name(test_name)
                category = cls.assign_category(test_name)

                item_id = str(uuid.uuid4())
                extracted.append({
                    "id": item_id,
                    "report_id": report_id,
                    "patient_id": patient_id,
                    "test_name": test_name,
                    "canonical_name": canonical_name,
                    "standard_code": std_code,
                    "category": category,
                    "value": val_str,
                    "numeric_value": num_val,
                    "unit": unit_str,
                    "reference_range": ref_str,
                    "range_low": eval_result.get("range_low"),
                    "range_high": eval_result.get("range_high"),
                    "range_status": eval_result.get("range_status", RangeStatus.UNREFERENCED),
                    "range_source_verified": eval_result.get("range_source_verified", False),
                    "test_date": detected_date,
                    "source_snippet": line_str,
                    "page_number": page_num,
                    "confidence": confidence,
                    "verification_status": VerificationStatus.UNREVIEWED,
                    "notes": eval_result.get("note", "")
                })

        # Multi-line cell sequence pass (common in PDF extracted tables)
        if len(extracted) < 3:
            clean_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("---")]
            
            def is_cell_val(s):
                return bool(re.match(r"^[><]?\s*[0-9]+(?:\.[0-9]+)?$", s) or s.lower() in ["negative", "positive", "normal", "non-reactive"])

            def is_cell_ref(s):
                return bool(re.match(r"^[0-9]+(?:\.[0-9]+)?\s*-\s*[0-9]+(?:\.[0-9]+)?$|^[><]=?\s*[0-9]+(?:\.[0-9]+)?$", s) or s.lower() in ["negative", "normal"])

            def is_cell_unit(s):
                return bool(re.match(r"^(?:mg/dL|g/dL|mEq/L|%|mL/min|U/L|ng/mL|ug/dL|10\^3/uL|pg/mL|uIU/mL|fL|pg|mL/min/1\.73m2)$", s, re.IGNORECASE))

            i = 0
            while i < len(clean_lines):
                cur = clean_lines[i]
                low_cur = cur.lower()
                invalid_tokens = ["patient", "doctor", "dr.", "date", "hospital", "clinic", "phone", "address", "page", "specimen", "id", "mrn", "test name", "collected", "result", "units", "reference range", "flag"]
                
                if (i + 1 < len(clean_lines) and 
                    is_cell_val(clean_lines[i + 1]) and 
                    len(cur) >= 2 and 
                    not any(inv == low_cur or low_cur.startswith(inv + ":") for inv in invalid_tokens) and 
                    cur not in seen_tests):
                    
                    tname = cur
                    val_str = clean_lines[i + 1]
                    unit_str = ""
                    ref_str = None
                    advance = 2

                    if i + 2 < len(clean_lines):
                        if is_cell_unit(clean_lines[i + 2]):
                            unit_str = clean_lines[i + 2]
                            advance = 3
                            if i + 3 < len(clean_lines) and is_cell_ref(clean_lines[i + 3]):
                                ref_str = clean_lines[i + 3]
                                advance = 4
                                if i + 4 < len(clean_lines) and clean_lines[i + 4].upper() in ["HIGH", "LOW", "NORMAL", "CRITICAL"]:
                                    advance = 5
                        elif is_cell_ref(clean_lines[i + 2]):
                            ref_str = clean_lines[i + 2]
                            advance = 3
                            if i + 3 < len(clean_lines) and clean_lines[i + 3].upper() in ["HIGH", "LOW", "NORMAL", "CRITICAL"]:
                                advance = 4

                    seen_tests.add(tname)
                    num_val = None
                    try:
                        num_val = float(re.sub(r"[^0-9\.]", "", val_str))
                    except (ValueError, TypeError):
                        num_val = None

                    eval_result = ReferenceRangeEvaluator.evaluate(
                        numeric_value=num_val,
                        text_value=val_str,
                        source_reference_range=ref_str
                    )
                    canonical_name, std_code = cls.normalize_name(tname)
                    cat = cls.assign_category(tname)
                    snippet = f"{tname}  {val_str} {unit_str} (Ref: {ref_str or 'None'})"

                    extracted.append({
                        "id": str(uuid.uuid4()),
                        "report_id": report_id,
                        "patient_id": patient_id,
                        "test_name": tname,
                        "canonical_name": canonical_name,
                        "standard_code": std_code,
                        "category": cat,
                        "value": val_str,
                        "numeric_value": num_val,
                        "unit": unit_str,
                        "reference_range": ref_str,
                        "range_low": eval_result.get("range_low"),
                        "range_high": eval_result.get("range_high"),
                        "range_status": eval_result.get("range_status", RangeStatus.UNREFERENCED),
                        "range_source_verified": eval_result.get("range_source_verified", False),
                        "test_date": detected_date,
                        "source_snippet": snippet,
                        "page_number": 1,
                        "confidence": 0.94 if ref_str else 0.88,
                        "verification_status": VerificationStatus.UNREVIEWED,
                        "notes": eval_result.get("note", "")
                    })
                    i += advance
                else:
                    i += 1

        return extracted
