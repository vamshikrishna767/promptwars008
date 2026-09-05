# MedLens — AI Clinical Information Intelligence

MedLens is an AI-powered clinical information intelligence platform that transforms fragmented patient intake and medical reports into a structured, reviewable, traceable, and reference-range aware patient record.

---

## Key Capabilities & Core Requirements

### 1. Patient Information Intake
- Captures comprehensive clinical details: Age, Biological Sex, Blood Group, Active Symptoms, Diagnosed Chronic Conditions, Known Drug Allergies (with reaction and severity), Active Pharmacotherapy (name, dosage, schedule, purpose), Surgical History, and Family Medical History.
- Clear Provenance: All intake information is explicitly labeled as `[Source: Patient Intake / Self-Reported]`.

### 2. Medical Report Processing (PDF & Text)
- Multi-format report extraction engine supporting PDF laboratory uploads and tabular plain text reports.
- Extracts test names, values, units, reference intervals, collection dates, clinical categories, and raw document excerpts.
- Features a multi-pass parsing pipeline that extracts both single-line tabular rows and sequential PDF table cell streams.

### 3. Structured Medical Record
- Formats lab parameters into clean panels (Hematology, Metabolic, Renal, Lipid, Hepatic, Thyroid, Iron, Urinalysis).
- Eliminates raw, unformatted AI text by organizing everything into structured cards and interactive tables.

### 4. Strict Reference-Range Awareness (Never Invent Ranges)
- Evaluates Low, Normal, High, and Critical bounds **strictly against reference intervals provided in the source report**.
- **The system never invents or assumes reference ranges.** Unreferenced tests (e.g. Troponin I without range) are explicitly tagged as `Range: Not Provided in Source` with status `NO SOURCE RANGE`.

### 5. Source Provenance & Side-by-Side Document Viewer
- Visual split-screen: The raw source report is displayed on the left, and structured parameters appear on the right.
- Clicking **"Inspect Source"** on any biomarker automatically scrolls to and highlights the exact snippet in the source document.
- Every extracted parameter includes an extraction confidence score (e.g. 96%).

### 6. AI-Powered Dual-Perspective Summary & Responsible AI
- **Patient-Friendly Summary**: Accessible language, plain explanations of test roles, reassurance, and suggested questions to ask at the next doctor's visit.
- **Clinician Brief**: Structured SBAR format highlighting abnormal findings, unreferenced values, and clinical safety flags.
- **Strict Non-Diagnostic Guardrail**: Prominently displays an inescapable medical disclaimer stating MedLens is an assistive organization tool and does not provide medical diagnoses, prescribe drugs, or adjust dosages.

---

## High-Value Clinical Features

- **Clinical Inconsistency & Conflict Detector**:
  - *Drug-Allergy Conflicts*: e.g. Penicillin allergy vs Amoxicillin prescription.
  - *Drug-Lab Contraindications*: e.g. Hyperkalemia (K > 5.2) with ACE inhibitors; Metformin with eGFR < 30 mL/min; Chronic NSAID with renal impairment.
  - *Intake-Lab Mismatches*: e.g. Patient denies diabetes history, but HbA1c is 9.4%.
  - *Historical Drifts*: Sharp >40% longitudinal biomarker swings across sequential reports.
- **Context-Aware Clarification Prompts**:
  - Formulates targeted questions when data is ambiguous (e.g., unspecified allergy reaction type, missing medication schedule, fasting status, or outdated chronic monitoring).
  - Users and clinicians can submit answers directly in the UI, updating the clinical record.
- **Human-in-the-Loop Verification & Audit Trail**:
  - Clinicians can verify, edit values/ranges, or flag inaccurate readings.
  - Immutable audit trail logs all timestamps, actors, previous values, and review notes.
- **Longitudinal Trend Analytics & Delta Tracking**:
  - Compares biomarkers across sequential reports over time.
  - Computes Net Delta ($\Delta\%$), clinical direction (Favorable vs Unfavorable progression), and renders interactive Chart.js graphs.
- **Role-Based Perspectives (Access Control)**:
  - Instant toggle between **Clinician Review Mode** (advanced controls, verification tools, raw snippets) and **Patient View** (simplified status badges, educational notes).
- **Export Capabilities**:
  - One-click server-generated printable PDF Clinical Summary (ReportLab).
  - Export to FHIR/JSON structured clinical document bundle.

---

## Preloaded Patient Cases

1. **Sarah Jenkins (54F)**:
   - *Intake*: Type 2 Diabetes, Hypertension, Hyperlipidemia; Severe Penicillin allergy; taking Metformin, Lisinopril, Atorvastatin, and Amoxicillin (dental prescription).
   - *Reports*: Baseline panel (Jan 2025) vs Deteriorating panel (Aug 2025) with HbA1c rising from 7.1% to 9.4%, elevated ALT/AST, unreferenced Troponin I.
   - *Active Conflict*: Critical Penicillin vs Amoxicillin conflict.
2. **Robert Chen (68M)**:
   - *Intake*: CKD Stage 3b, Congestive Heart Failure, Hypertension; Sulfa allergy; Lisinopril, Furosemide, Naproxen, Potassium Chloride.
   - *Reports*: Progressive renal decline (Creatinine 1.5 -> 2.4 mg/dL, eGFR 48 -> 26 mL/min, Potassium 4.8 -> 5.8 mEq/L).
   - *Active Conflicts*: Hyperkalemia with ACE inhibitor & Potassium supplement; Nephrotoxic NSAID with renal failure.
3. **Maya Patel (32F)**:
   - *Intake*: Fatigue, cold intolerance; no diagnosed chronic conditions; taking Levothyroxine and Ferrous Sulfate.
   - *Reports*: Severe Iron Deficiency Anemia & Subclinical Hypothyroidism; post-treatment check showing +300% Ferritin recovery.
   - *Active Conflict*: Intake-Lab mismatch (taking Levothyroxine without diagnosed thyroid condition).

---

## Quick Start Guide

### 1. Requirements
- Python 3.11+
- Installed packages: `fastapi`, `uvicorn`, `pydantic`, `pypdf`, `reportlab`, `httpx`

### 2. Run the Application
```bash
py -3.11 run.py
```
Open your browser at: **`http://127.0.0.1:8000`**

### 3. Run Automated Tests
```bash
py -3.11 -m unittest discover -s tests -v
```

### 4. Interactive API Documentation
Swagger UI is accessible at: **`http://127.0.0.1:8000/docs`**
