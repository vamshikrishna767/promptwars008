"""
MedLens - Preloaded Realistic Clinical Patient Cases and Longitudinal Lab Reports
Provides realistic patient cases demonstrating:
- Multi-report longitudinal comparisons
- Drug-allergy and drug-lab conflict detection
- Reference-range evaluation (including unreferenced tests)
- Context-aware clarification prompts
"""

import uuid
from app.database import DatabaseRepo
from app.services.extractor import MedicalReportExtractor
from app.services.conflicts import ConflictDetector
from app.services.clarifications import ClarificationEngine


PATIENT_1 = {
    "id": "patient-sarah-jenkins",
    "name": "Sarah Jenkins",
    "age": 54,
    "sex": "Female",
    "blood_group": "A+",
    "phone": "+1 (555) 234-8901",
    "email": "sarah.jenkins@example.com",
    "created_at": "2025-01-10T09:00:00"
}

INTAKE_1 = {
    "id": "intake-sarah-jenkins",
    "patient_id": "patient-sarah-jenkins",
    "symptoms": ["Chronic Fatigue", "Polyuria (Frequent Urination)", "Occasional Blurred Vision", "Mild Muscle Aches"],
    "conditions": ["Type 2 Diabetes Mellitus", "Essential Hypertension", "Hyperlipidemia"],
    "allergies": [
        {"allergen": "Penicillin", "reaction": "Hives and acute lip swelling (Angioedema)", "severity": "Severe", "source": "User Intake"}
    ],
    "medications": [
        {"name": "Metformin", "dosage": "1000 mg", "frequency": "Twice daily with meals", "purpose": "Glycemic control", "source": "User Intake"},
        {"name": "Lisinopril", "dosage": "20 mg", "frequency": "Once daily morning", "purpose": "Blood pressure", "source": "User Intake"},
        {"name": "Atorvastatin", "dosage": "40 mg", "frequency": "Once daily at bedtime", "purpose": "Cholesterol", "source": "User Intake"},
        {"name": "Amoxicillin", "dosage": "500 mg", "frequency": "Three times daily", "purpose": "Prescribed by dental urgent care for toothache", "source": "User Intake"}
    ],
    "surgeries": ["Cholecystectomy (2018)", "C-Section (2001)"],
    "family_history": ["Mother: Type 2 Diabetes, Myocardial Infarction at 68", "Father: Hypertension, Stroke at 72"],
    "lifestyle_notes": "Sedentary office worker. Reports high occupational stress. Trying low-sodium diet.",
    "source": "Patient Intake Portal"
}

REPORT_1_SARAH_TEXT = """
METROPOLITAN CLINICAL LABORATORY
Accreditation: CAP / CLIA Certified #45D0982314
Patient: Sarah Jenkins | Age: 54 | Sex: Female | MRN: 902841
Specimen Date: 2025-01-15 | Report Date: 2025-01-15

TEST NAME                    RESULT   UNITS      REFERENCE RANGE   STATUS
-------------------------------------------------------------------------
Fasting Blood Sugar          138      mg/dL      70 - 99           High
HbA1c                        7.1      %          < 5.7             High
Total Cholesterol            220      mg/dL      < 200             High
Triglycerides                185      mg/dL      < 150             High
HDL Cholesterol              46       mg/dL      > 50              Low
LDL Cholesterol              137      mg/dL      < 100             High
Serum Creatinine             0.9      mg/dL      0.6 - 1.1         Normal
eGFR                         78       mL/min     > 60              Normal
Potassium                    4.4      mEq/L      3.5 - 5.1         Normal
Sodium                       140      mEq/L      135 - 145         Normal
Hemoglobin                   13.8     g/dL       12.0 - 16.0       Normal
White Blood Cells            6.4      10^3/uL    4.5 - 11.0        Normal
Platelet Count               240      10^3/uL    150 - 450         Normal
ALT (SGPT)                   34       U/L        7 - 45            Normal
AST (SGOT)                   28       U/L        8 - 40            Normal
"""

REPORT_2_SARAH_TEXT = """
METROPOLITAN CLINICAL LABORATORY
Accreditation: CAP / CLIA Certified #45D0982314
Patient: Sarah Jenkins | Age: 54 | Sex: Female | MRN: 902841
Specimen Date: 2025-08-20 | Report Date: 2025-08-20

TEST NAME                    RESULT   UNITS      REFERENCE RANGE   STATUS
-------------------------------------------------------------------------
Fasting Blood Sugar          198      mg/dL      70 - 99           High
HbA1c                        9.4      %          < 5.7             High
Total Cholesterol            245      mg/dL      < 200             High
Triglycerides                230      mg/dL      < 150             High
HDL Cholesterol              40       mg/dL      > 50              Low
LDL Cholesterol              159      mg/dL      < 100             High
Serum Creatinine             1.1      mg/dL      0.6 - 1.1         Normal
eGFR                         65       mL/min     > 60              Normal
Potassium                    4.7      mEq/L      3.5 - 5.1         Normal
ALT (SGPT)                   88       U/L        7 - 45            High
AST (SGOT)                   64       U/L        8 - 40            High
High Sensitivity CRP         4.8      mg/L       < 1.0             High
Troponin I                   0.02     ng/mL                        
"""

PATIENT_2 = {
    "id": "patient-robert-chen",
    "name": "Robert Chen",
    "age": 68,
    "sex": "Male",
    "blood_group": "O+",
    "phone": "+1 (555) 789-1234",
    "email": "robert.chen@example.com",
    "created_at": "2024-11-01T10:00:00"
}

INTAKE_2 = {
    "id": "intake-robert-chen",
    "patient_id": "patient-robert-chen",
    "symptoms": ["Shortness of breath on mild exertion", "Bilateral ankle swelling", "Lumbar stiffness"],
    "conditions": ["Chronic Kidney Disease Stage 3b", "Congestive Heart Failure", "Hypertension"],
    "allergies": [
        {"allergen": "Sulfa Drugs", "reaction": "Maculopapular rash across trunk", "severity": "Moderate", "source": "User Intake"}
    ],
    "medications": [
        {"name": "Lisinopril", "dosage": "40 mg", "frequency": "Daily", "purpose": "Cardioprotection / BP", "source": "User Intake"},
        {"name": "Furosemide", "dosage": "40 mg", "frequency": "Daily morning", "purpose": "Diuretic for edema", "source": "User Intake"},
        {"name": "Naproxen", "dosage": "500 mg", "frequency": "Twice daily as needed", "purpose": "Back stiffness", "source": "User Intake"},
        {"name": "Potassium Chloride", "dosage": "20 mEq", "frequency": "Once daily", "purpose": "Electrolyte supplement", "source": "User Intake"}
    ],
    "surgeries": ["Coronary Artery Bypass Graft (CABG) x3 (2017)"],
    "family_history": ["Father: Kidney Failure requiring dialysis", "Brother: CAD with stents"],
    "lifestyle_notes": "Restricted sodium diet (<2g/day). Tracks daily weights.",
    "source": "Cardiology Clinic Intake"
}

REPORT_1_ROBERT_TEXT = """
ST. JUDE HEALTHCARE REGIONAL LAB
Specimen Date: 2024-11-10 | Report Date: 2024-11-10
Patient: Robert Chen | Age: 68 | Sex: Male

TEST NAME                    RESULT   UNITS      REFERENCE RANGE
-----------------------------------------------------------------
Serum Creatinine             1.5      mg/dL      0.7 - 1.3
eGFR                         48       mL/min     > 60
Blood Urea Nitrogen          28       mg/dL      7 - 20
Potassium                    4.8      mEq/L      3.5 - 5.0
Sodium                       138      mEq/L      136 - 145
Hemoglobin                   11.8     g/dL       13.5 - 17.5
Hematocrit                   36.0     %          41.0 - 50.0
BNP                          320      pg/mL      < 100
"""

REPORT_2_ROBERT_TEXT = """
ST. JUDE HEALTHCARE REGIONAL LAB
Specimen Date: 2025-02-18 | Report Date: 2025-02-18
Patient: Robert Chen | Age: 68 | Sex: Male

TEST NAME                    RESULT   UNITS      REFERENCE RANGE
-----------------------------------------------------------------
Serum Creatinine             2.4      mg/dL      0.7 - 1.3
eGFR                         26       mL/min     > 60
Blood Urea Nitrogen          48       mg/dL      7 - 20
Potassium                    5.8      mEq/L      3.5 - 5.0
Sodium                       134      mEq/L      136 - 145
Hemoglobin                   10.2     g/dL       13.5 - 17.5
BNP                          680      pg/mL      < 100
"""

PATIENT_3 = {
    "id": "patient-maya-patel",
    "name": "Maya Patel",
    "age": 32,
    "sex": "Female",
    "blood_group": "B+",
    "phone": "+1 (555) 456-7890",
    "email": "maya.patel@example.com",
    "created_at": "2025-03-01T11:00:00"
}

INTAKE_3 = {
    "id": "intake-maya-patel",
    "patient_id": "patient-maya-patel",
    "symptoms": ["Extreme Exhaustion", "Cold Sensitivity", "Brittle Nails", "Lightheadedness"],
    "conditions": [],  # Denies diagnosed chronic conditions
    "allergies": [],
    "medications": [
        {"name": "Levothyroxine", "dosage": "50 mcg", "frequency": "Daily on empty stomach", "purpose": "Thyroid", "source": "User Intake"},
        {"name": "Oral Ferrous Sulfate", "dosage": "325 mg", "frequency": "Daily with Vitamin C", "purpose": "Iron supplementation", "source": "User Intake"}
    ],
    "surgeries": ["Appendectomy (2015)"],
    "family_history": ["Mother: Hashimoto's Thyroiditis", "Maternal Aunt: Pernicious Anemia"],
    "lifestyle_notes": "Vegetarian diet for 10 years. Non-smoker.",
    "source": "Women's Health Intake"
}

REPORT_1_MAYA_TEXT = """
PACIFIC DIAGNOSTIC LABORATORIES
Specimen Date: 2025-03-12 | Report Date: 2025-03-12
Patient: Maya Patel | Age: 32 | Sex: Female

TEST NAME                    RESULT   UNITS      REFERENCE RANGE
-----------------------------------------------------------------
Ferritin                     7        ng/mL      15 - 150
Hemoglobin                   9.8      g/dL       12.0 - 15.5
Hematocrit                   31.2     %          36.0 - 46.0
MCV                          72       fL         80 - 100
MCH                          23.5     pg         27.0 - 33.0
Serum Iron                   28       ug/dL      50 - 170
TIBC                         440      ug/dL      250 - 400
TSH                          6.8      uIU/mL     0.45 - 4.50
Free T4                      0.75     ng/dL      0.82 - 1.77
"""

REPORT_2_MAYA_TEXT = """
PACIFIC DIAGNOSTIC LABORATORIES
Specimen Date: 2025-06-25 | Report Date: 2025-06-25
Patient: Maya Patel | Age: 32 | Sex: Female

TEST NAME                    RESULT   UNITS      REFERENCE RANGE
-----------------------------------------------------------------
Ferritin                     32       ng/mL      15 - 150
Hemoglobin                   12.1     g/dL       12.0 - 15.5
Hematocrit                   37.5     %          36.0 - 46.0
MCV                          84       fL         80 - 100
Serum Iron                   65       ug/dL      50 - 170
TIBC                         360      ug/dL      250 - 400
TSH                          3.1      uIU/mL     0.45 - 4.50
Free T4                      1.15     ng/dL      0.82 - 1.77
"""


def seed_database():
    """Seeds the SQLite database with rich realistic clinical cases if empty."""
    existing_patients = DatabaseRepo.get_all_patients()
    if existing_patients:
        return

    # Seed Patient 1
    p1 = DatabaseRepo.create_patient(PATIENT_1)
    DatabaseRepo.save_patient_intake(p1["id"], INTAKE_1)
    
    r1_1 = DatabaseRepo.create_report({
        "id": "report-sarah-1",
        "patient_id": p1["id"],
        "title": "Baseline Comprehensive Metabolic & Lipid Panel",
        "filename": "sarah_jenkins_lab_jan2025.txt",
        "file_type": "txt",
        "uploaded_at": "2025-01-15T14:30:00",
        "report_date": "2025-01-15",
        "facility_name": "Metropolitan Clinical Laboratory",
        "raw_text": REPORT_1_SARAH_TEXT
    })
    items_1_1 = MedicalReportExtractor.parse_report_text(r1_1["id"], p1["id"], REPORT_1_SARAH_TEXT, "2025-01-15")
    DatabaseRepo.save_extracted_items(items_1_1, actor="Initial Lab Upload")

    r1_2 = DatabaseRepo.create_report({
        "id": "report-sarah-2",
        "patient_id": p1["id"],
        "title": "Follow-Up Glycemic & Hepatic Panel",
        "filename": "sarah_jenkins_lab_aug2025.txt",
        "file_type": "txt",
        "uploaded_at": "2025-08-20T16:00:00",
        "report_date": "2025-08-20",
        "facility_name": "Metropolitan Clinical Laboratory",
        "raw_text": REPORT_2_SARAH_TEXT
    })
    items_1_2 = MedicalReportExtractor.parse_report_text(r1_2["id"], p1["id"], REPORT_2_SARAH_TEXT, "2025-08-20")
    DatabaseRepo.save_extracted_items(items_1_2, actor="Follow-up Lab Upload")

    # Run conflicts & clarifications for Patient 1
    all_p1_items = DatabaseRepo.get_extracted_items(p1["id"])
    c1 = ConflictDetector.detect_conflicts(p1["id"], INTAKE_1, all_p1_items)
    DatabaseRepo.save_conflicts(p1["id"], c1)
    q1 = ClarificationEngine.generate_questions(p1["id"], INTAKE_1, all_p1_items)
    DatabaseRepo.save_clarifications(p1["id"], q1)

    # Seed Patient 2
    p2 = DatabaseRepo.create_patient(PATIENT_2)
    DatabaseRepo.save_patient_intake(p2["id"], INTAKE_2)
    r2_1 = DatabaseRepo.create_report({
        "id": "report-robert-1",
        "patient_id": p2["id"],
        "title": "Renal & Electrolyte Profile (Nov 2024)",
        "filename": "robert_chen_bmp_nov2024.txt",
        "file_type": "txt",
        "uploaded_at": "2024-11-10T11:00:00",
        "report_date": "2024-11-10",
        "facility_name": "St. Jude Healthcare Regional Lab",
        "raw_text": REPORT_1_ROBERT_TEXT
    })
    items_2_1 = MedicalReportExtractor.parse_report_text(r2_1["id"], p2["id"], REPORT_1_ROBERT_TEXT, "2024-11-10")
    DatabaseRepo.save_extracted_items(items_2_1, actor="Inpatient Admission Panel")

    r2_2 = DatabaseRepo.create_report({
        "id": "report-robert-2",
        "patient_id": p2["id"],
        "title": "Renal Function Deterioration Check (Feb 2025)",
        "filename": "robert_chen_bmp_feb2025.txt",
        "file_type": "txt",
        "uploaded_at": "2025-02-18T15:20:00",
        "report_date": "2025-02-18",
        "facility_name": "St. Jude Healthcare Regional Lab",
        "raw_text": REPORT_2_ROBERT_TEXT
    })
    items_2_2 = MedicalReportExtractor.parse_report_text(r2_2["id"], p2["id"], REPORT_2_ROBERT_TEXT, "2025-02-18")
    DatabaseRepo.save_extracted_items(items_2_2, actor="Urgent Care Lab Upload")

    all_p2_items = DatabaseRepo.get_extracted_items(p2["id"])
    c2 = ConflictDetector.detect_conflicts(p2["id"], INTAKE_2, all_p2_items)
    DatabaseRepo.save_conflicts(p2["id"], c2)
    q2 = ClarificationEngine.generate_questions(p2["id"], INTAKE_2, all_p2_items)
    DatabaseRepo.save_clarifications(p2["id"], q2)

    # Seed Patient 3
    p3 = DatabaseRepo.create_patient(PATIENT_3)
    DatabaseRepo.save_patient_intake(p3["id"], INTAKE_3)
    r3_1 = DatabaseRepo.create_report({
        "id": "report-maya-1",
        "patient_id": p3["id"],
        "title": "Fatigue Workup: Iron & Thyroid Panel (March 2025)",
        "filename": "maya_patel_iron_thyroid_mar2025.txt",
        "file_type": "txt",
        "uploaded_at": "2025-03-12T09:15:00",
        "report_date": "2025-03-12",
        "facility_name": "Pacific Diagnostic Laboratories",
        "raw_text": REPORT_1_MAYA_TEXT
    })
    items_3_1 = MedicalReportExtractor.parse_report_text(r3_1["id"], p3["id"], REPORT_1_MAYA_TEXT, "2025-03-12")
    DatabaseRepo.save_extracted_items(items_3_1, actor="Outpatient Lab Upload")

    r3_2 = DatabaseRepo.create_report({
        "id": "report-maya-2",
        "patient_id": p3["id"],
        "title": "Post-Supplementation Response Lab (June 2025)",
        "filename": "maya_patel_iron_thyroid_jun2025.txt",
        "file_type": "txt",
        "uploaded_at": "2025-06-25T10:45:00",
        "report_date": "2025-06-25",
        "facility_name": "Pacific Diagnostic Laboratories",
        "raw_text": REPORT_2_MAYA_TEXT
    })
    items_3_2 = MedicalReportExtractor.parse_report_text(r3_2["id"], p3["id"], REPORT_2_MAYA_TEXT, "2025-06-25")
    DatabaseRepo.save_extracted_items(items_3_2, actor="Outpatient Lab Upload")

    all_p3_items = DatabaseRepo.get_extracted_items(p3["id"])
    c3 = ConflictDetector.detect_conflicts(p3["id"], INTAKE_3, all_p3_items)
    DatabaseRepo.save_conflicts(p3["id"], c3)
    q3 = ClarificationEngine.generate_questions(p3["id"], INTAKE_3, all_p3_items)
    DatabaseRepo.save_clarifications(p3["id"], q3)
