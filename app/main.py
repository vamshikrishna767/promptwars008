"""
MedLens - FastAPI Application Entrypoint
Provides REST endpoints for Patient Intake, Medical Report Processing,
Reference-Range Aware Extraction, Conflict Detection, Human Verification,
Longitudinal Trend Analytics, and PDF/JSON Export.
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db, DatabaseRepo
from app.models import (
    PatientCreate, PatientIntake, ExtractedItemUpdate,
    ClarificationAnswer, UserRole, ConflictResolutionRequest
)
from app.services.extractor import MedicalReportExtractor
from app.services.reference_range import ReferenceRangeEvaluator
from app.services.conflicts import ConflictDetector
from app.services.clarifications import ClarificationEngine
from app.services.longitudinal import LongitudinalTracker
from app.services.summary import ClinicalSummaryEngine
from app.services.pdf_export import ClinicalPDFExporter
from app.sample_data import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & seed realistic sample clinical cases
    init_db()
    seed_database()
    yield


app = FastAPI(
    title="MedLens — AI Clinical Insight Platform",
    description="AI-Powered Clinical Information Intelligence with Reference-Range Awareness & Traceability",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# -------------------------------------------------------------
# 1. PATIENT MANAGEMENT & INTAKE APIS
# -------------------------------------------------------------
@app.get("/api/patients")
async def get_patients():
    return DatabaseRepo.get_all_patients()


@app.post("/api/patients")
async def create_patient(payload: PatientCreate):
    p = DatabaseRepo.create_patient(payload.model_dump())
    return p


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str):
    p = DatabaseRepo.get_patient(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return p


@app.get("/api/patients/{patient_id}/intake")
async def get_patient_intake(patient_id: str):
    intake = DatabaseRepo.get_patient_intake(patient_id)
    if not intake:
        # Return empty template
        return {
            "patient_id": patient_id,
            "symptoms": [],
            "conditions": [],
            "allergies": [],
            "medications": [],
            "surgeries": [],
            "family_history": [],
            "lifestyle_notes": "",
            "source": "Patient Intake Form"
        }
    return intake


@app.post("/api/patients/{patient_id}/intake")
async def save_patient_intake(patient_id: str, intake: PatientIntake, actor: str = Query("Patient / Clinician")):
    p = DatabaseRepo.get_patient(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    saved = DatabaseRepo.save_patient_intake(patient_id, intake.model_dump(), actor=actor)

    # Re-evaluate conflicts and clarification prompts
    items = DatabaseRepo.get_extracted_items(patient_id)
    conflicts = ConflictDetector.detect_conflicts(patient_id, saved, items)
    DatabaseRepo.save_conflicts(patient_id, conflicts)

    clarifications = ClarificationEngine.generate_questions(patient_id, saved, items)
    DatabaseRepo.save_clarifications(patient_id, clarifications)

    return saved


# -------------------------------------------------------------
# 2. MEDICAL REPORT PROCESSING & EXTRACTION
# -------------------------------------------------------------
@app.get("/api/patients/{patient_id}/reports")
async def get_patient_reports(patient_id: str):
    return DatabaseRepo.get_patient_reports(patient_id)


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    rep = DatabaseRepo.get_report(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    return rep


@app.post("/api/patients/{patient_id}/reports/upload")
async def upload_medical_report(
    patient_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    report_date: Optional[str] = Form(None),
    facility_name: Optional[str] = Form(None)
):
    patient = DatabaseRepo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    content = await file.read()
    filename = file.filename or "uploaded_report"
    file_lower = filename.lower()

    if file_lower.endswith(".pdf"):
        file_type = "pdf"
        raw_text = MedicalReportExtractor.extract_text_from_pdf(content)
    else:
        file_type = "txt"
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = content.decode("latin-1", errors="ignore")

    rep_title = title or (filename.rsplit(".", 1)[0].replace("_", " ").title())
    detected_date = report_date or MedicalReportExtractor.detect_report_date(raw_text) or "2025-09-01"
    detected_fac = facility_name or MedicalReportExtractor.detect_facility(raw_text)

    # Save report
    rep = DatabaseRepo.create_report({
        "patient_id": patient_id,
        "title": rep_title,
        "filename": filename,
        "file_type": file_type,
        "report_date": detected_date,
        "facility_name": detected_fac,
        "raw_text": raw_text
    })

    # Run extraction
    extracted_items = MedicalReportExtractor.parse_report_text(
        report_id=rep["id"],
        patient_id=patient_id,
        raw_text=raw_text,
        default_date=detected_date
    )
    DatabaseRepo.save_extracted_items(extracted_items, actor="AI Extraction Pipeline")

    # Update conflicts & clarifications
    intake = DatabaseRepo.get_patient_intake(patient_id)
    all_items = DatabaseRepo.get_extracted_items(patient_id)
    conflicts = ConflictDetector.detect_conflicts(patient_id, intake, all_items)
    DatabaseRepo.save_conflicts(patient_id, conflicts)

    clarifications = ClarificationEngine.generate_questions(patient_id, intake, all_items)
    DatabaseRepo.save_clarifications(patient_id, clarifications)

    return {
        "report": rep,
        "items_extracted_count": len(extracted_items),
        "conflicts_count": len(conflicts),
        "items": extracted_items
    }


class ReportPasteRequest(BaseModel):
    title: Optional[str] = "Pasted Laboratory Report"
    raw_text: str
    report_date: Optional[str] = None
    facility_name: Optional[str] = None


@app.post("/api/patients/{patient_id}/reports/paste")
async def paste_medical_report(patient_id: str, payload: ReportPasteRequest):
    patient = DatabaseRepo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    raw_text = payload.raw_text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Report text cannot be empty")

    detected_date = payload.report_date or MedicalReportExtractor.detect_report_date(raw_text) or "2025-09-01"
    detected_fac = payload.facility_name or MedicalReportExtractor.detect_facility(raw_text)

    rep = DatabaseRepo.create_report({
        "patient_id": patient_id,
        "title": payload.title or "Pasted Laboratory Report",
        "filename": "pasted_report.txt",
        "file_type": "txt",
        "report_date": detected_date,
        "facility_name": detected_fac,
        "raw_text": raw_text
    })

    extracted_items = MedicalReportExtractor.parse_report_text(
        report_id=rep["id"],
        patient_id=patient_id,
        raw_text=raw_text,
        default_date=detected_date
    )
    DatabaseRepo.save_extracted_items(extracted_items, actor="Pasted Report Pipeline")

    intake = DatabaseRepo.get_patient_intake(patient_id)
    all_items = DatabaseRepo.get_extracted_items(patient_id)
    conflicts = ConflictDetector.detect_conflicts(patient_id, intake, all_items)
    DatabaseRepo.save_conflicts(patient_id, conflicts)

    clarifications = ClarificationEngine.generate_questions(patient_id, intake, all_items)
    DatabaseRepo.save_clarifications(patient_id, clarifications)

    return {
        "report": rep,
        "items_extracted_count": len(extracted_items),
        "conflicts_count": len(conflicts),
        "items": extracted_items
    }


# -------------------------------------------------------------
# 3. STRUCTURED MEDICAL RECORD & HUMAN-IN-THE-LOOP VERIFICATION
# -------------------------------------------------------------
@app.get("/api/patients/{patient_id}/extracted")
async def get_extracted_items(
    patient_id: str,
    report_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None
):
    items = DatabaseRepo.get_extracted_items(patient_id, report_id)
    if category and category != "ALL":
        items = [it for it in items if it.get("category", "").lower() == category.lower()]
    if status and status != "ALL":
        items = [it for it in items if it.get("range_status", "").upper() == status.upper()]
    return items


@app.patch("/api/extracted/{item_id}")
async def update_extracted_item(
    item_id: str,
    payload: ExtractedItemUpdate,
    actor: str = Query("Dr. Reviewer")
):
    updates = {}
    if payload.value is not None:
        updates["value"] = payload.value
        try:
            updates["numeric_value"] = float(payload.value)
        except ValueError:
            updates["numeric_value"] = None

    if payload.unit is not None:
        updates["unit"] = payload.unit

    if payload.reference_range is not None:
        updates["reference_range"] = payload.reference_range
        # Re-evaluate reference range
        if payload.value is not None:
            eval_res = ReferenceRangeEvaluator.evaluate(
                numeric_value=updates.get("numeric_value"),
                text_value=payload.value,
                source_reference_range=payload.reference_range
            )
            updates["range_status"] = eval_res["range_status"]

    if payload.verification_status is not None:
        updates["verification_status"] = payload.verification_status.value

    if payload.notes is not None:
        updates["notes"] = payload.notes

    if payload.verified_by is not None:
        updates["verified_by"] = payload.verified_by

    updated = DatabaseRepo.update_extracted_item(item_id, updates, actor=actor)
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")

    # Refresh conflicts
    patient_id = updated["patient_id"]
    intake = DatabaseRepo.get_patient_intake(patient_id)
    all_items = DatabaseRepo.get_extracted_items(patient_id)
    conflicts = ConflictDetector.detect_conflicts(patient_id, intake, all_items)
    DatabaseRepo.save_conflicts(patient_id, conflicts)

    return updated


# -------------------------------------------------------------
# 4. CLINICAL INCONSISTENCIES & CLARIFICATIONS
# -------------------------------------------------------------
@app.get("/api/patients/{patient_id}/conflicts")
async def get_conflicts(patient_id: str):
    return DatabaseRepo.get_conflicts(patient_id)


@app.post("/api/conflicts/{conflict_id}/resolve")
async def resolve_conflict_endpoint(conflict_id: str, payload: ConflictResolutionRequest):
    updated = DatabaseRepo.resolve_conflict(
        conflict_id=conflict_id,
        status=payload.status,
        resolution_notes=payload.resolution_notes,
        resolved_by=payload.resolved_by or "Dr. Clinician"
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return updated


@app.get("/api/patients/{patient_id}/clarifications")
async def get_clarifications(patient_id: str):
    return DatabaseRepo.get_clarifications(patient_id)


@app.post("/api/clarifications/{question_id}/answer")
async def answer_clarification(question_id: str, payload: ClarificationAnswer):
    updated = DatabaseRepo.answer_clarification(question_id, payload.answer)
    if not updated:
        raise HTTPException(status_code=404, detail="Clarification question not found")
    return updated


# -------------------------------------------------------------
# 5. LONGITUDINAL COMPARISON & DELTA TRACKING
# -------------------------------------------------------------
@app.get("/api/patients/{patient_id}/longitudinal")
async def get_longitudinal_trends(patient_id: str):
    reports = DatabaseRepo.get_patient_reports(patient_id)
    items = DatabaseRepo.get_extracted_items(patient_id)
    trends = LongitudinalTracker.analyze_trends(items, reports)
    return {
        "patient_id": patient_id,
        "reports_count": len(reports),
        "biomarkers": trends
    }


# -------------------------------------------------------------
# 6. AI-POWERED CLINICAL SUMMARY & AUDIT TRAIL
# -------------------------------------------------------------
@app.get("/api/patients/{patient_id}/summary")
async def get_clinical_summary(patient_id: str):
    patient = DatabaseRepo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    intake = DatabaseRepo.get_patient_intake(patient_id)
    items = DatabaseRepo.get_extracted_items(patient_id)
    conflicts = DatabaseRepo.get_conflicts(patient_id)

    summary = ClinicalSummaryEngine.generate_summary(patient, intake, items, conflicts)
    return summary


@app.get("/api/patients/{patient_id}/audit-logs")
async def get_audit_logs(patient_id: str):
    return DatabaseRepo.get_audit_logs(patient_id)


# -------------------------------------------------------------
# 7. EXPORT (PDF & JSON)
# -------------------------------------------------------------
@app.get("/api/patients/{patient_id}/export/pdf")
async def export_pdf(patient_id: str):
    patient = DatabaseRepo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    intake = DatabaseRepo.get_patient_intake(patient_id) or {}
    reports = DatabaseRepo.get_patient_reports(patient_id)
    items = DatabaseRepo.get_extracted_items(patient_id)
    conflicts = DatabaseRepo.get_conflicts(patient_id)
    summary = ClinicalSummaryEngine.generate_summary(patient, intake, items, conflicts)

    pdf_bytes = ClinicalPDFExporter.generate_pdf(patient, intake, reports, items, conflicts, summary)
    clean_name = patient["name"].replace(" ", "_").lower()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=medlens_{clean_name}_record.pdf"}
    )


@app.get("/api/patients/{patient_id}/export/json")
async def export_json(patient_id: str):
    patient = DatabaseRepo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    intake = DatabaseRepo.get_patient_intake(patient_id) or {}
    reports = DatabaseRepo.get_patient_reports(patient_id)
    items = DatabaseRepo.get_extracted_items(patient_id)
    conflicts = DatabaseRepo.get_conflicts(patient_id)
    summary = ClinicalSummaryEngine.generate_summary(patient, intake, items, conflicts)
    trends = LongitudinalTracker.analyze_trends(items, reports)

    export_payload = {
        "resourceType": "Bundle",
        "type": "document",
        "meta": {
            "generator": "MedLens AI Clinical Intelligence Platform v2.0",
            "exportTimestamp": summary["generated_at"],
            "disclaimer": summary["disclaimer"]
        },
        "patient": patient,
        "clinicalIntake": intake,
        "diagnosticReports": reports,
        "extractedBiomarkers": items,
        "conflictAlerts": conflicts,
        "longitudinalBiomarkers": trends,
        "clinicalSummary": summary
    }
    return JSONResponse(content=export_payload)
