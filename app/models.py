"""
MedLens - Data Models and Schemas
Defines structured entities for Patient Intake, Medical Reports,
Lab Extractions, Inconsistency Alerts, Audit Logs, and Summaries.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class RangeStatus(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL_LOW = "CRITICAL_LOW"
    CRITICAL_HIGH = "CRITICAL_HIGH"
    UNREFERENCED = "UNREFERENCED"  # When source report provides no reference range


class VerificationStatus(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    VERIFIED = "VERIFIED"
    EDITED = "EDITED"
    FLAGGED = "FLAGGED"


class ConflictSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class UserRole(str, Enum):
    PATIENT = "PATIENT"
    CLINICIAN = "CLINICIAN"


class AllergyItem(BaseModel):
    allergen: str
    reaction: Optional[str] = "Unspecified"
    severity: Optional[str] = "Moderate"
    source: str = "User Intake"


class MedicationItem(BaseModel):
    name: str
    dosage: Optional[str] = ""
    frequency: Optional[str] = ""
    purpose: Optional[str] = ""
    source: str = "User Intake"


class PatientBase(BaseModel):
    name: str
    age: int
    sex: str
    blood_group: Optional[str] = "Unknown"
    phone: Optional[str] = ""
    email: Optional[str] = ""


class PatientCreate(PatientBase):
    pass


class Patient(PatientBase):
    id: str
    created_at: str


class PatientIntake(BaseModel):
    id: Optional[str] = None
    patient_id: str
    symptoms: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    allergies: List[AllergyItem] = Field(default_factory=list)
    medications: List[MedicationItem] = Field(default_factory=list)
    surgeries: List[str] = Field(default_factory=list)
    family_history: List[str] = Field(default_factory=list)
    lifestyle_notes: Optional[str] = ""
    source: str = "Patient Intake Form"
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExtractedItem(BaseModel):
    id: str
    report_id: str
    patient_id: str
    test_name: str
    canonical_name: Optional[str] = ""
    standard_code: Optional[str] = ""
    category: str = "General"
    value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = ""
    reference_range: Optional[str] = None  # Exact source range string, e.g. "70 - 99"
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    range_status: RangeStatus = RangeStatus.UNREFERENCED
    range_source_verified: bool = False  # True only if extracted directly from source text
    test_date: Optional[str] = ""
    source_snippet: str = ""  # The raw report sentence/line
    page_number: int = 1
    confidence: float = 0.95
    verification_status: VerificationStatus = VerificationStatus.UNREVIEWED
    verified_by: Optional[str] = None
    notes: Optional[str] = ""
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ExtractedItemUpdate(BaseModel):
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
    notes: Optional[str] = None
    verified_by: Optional[str] = "Dr. Reviewer"


class MedicalReport(BaseModel):
    id: str
    patient_id: str
    title: str
    filename: str
    file_type: str  # 'pdf' or 'txt'
    uploaded_at: str
    report_date: str
    facility_name: Optional[str] = "Clinical Laboratory Services"
    raw_text: str = ""
    items_count: int = 0


class ConflictAlert(BaseModel):
    id: str
    patient_id: str
    conflict_type: str  # 'DRUG_ALLERGY', 'DRUG_LAB', 'HISTORICAL_DRIFT', 'INTAKE_LAB_MISMATCH'
    severity: ConflictSeverity
    title: str
    description: str
    recommendation: str
    source_entities: List[str] = Field(default_factory=list)
    status: str = "ACTIVE"  # 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED'
    resolution_notes: Optional[str] = ""
    resolved_by: Optional[str] = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ConflictResolutionRequest(BaseModel):
    status: str = "ACKNOWLEDGED"  # 'ACKNOWLEDGED' or 'RESOLVED'
    resolution_notes: str = ""
    resolved_by: Optional[str] = "Dr. Clinician"


class ClarificationQuestion(BaseModel):
    id: str
    patient_id: str
    category: str
    question: str
    rationale: str
    answered: bool = False
    answer: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ClarificationAnswer(BaseModel):
    answer: str


class AuditLogEntry(BaseModel):
    id: str
    patient_id: str
    item_id: Optional[str] = None
    action: str  # 'EXTRACTED', 'VERIFIED', 'EDITED', 'FLAGGED', 'INTAKE_UPDATED'
    actor: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    details: str = ""


class LongitudinalDataPoint(BaseModel):
    report_id: str
    report_title: str
    date: str
    value: float
    unit: str
    range_status: RangeStatus
    reference_range: Optional[str] = ""


class LongitudinalTrend(BaseModel):
    test_name: str
    category: str
    unit: str
    data_points: List[LongitudinalDataPoint] = Field(default_factory=list)
    delta_percent: Optional[float] = None
    trend_direction: str = "STABLE"  # 'UP', 'DOWN', 'STABLE'
    clinical_note: str = ""


class ClinicalSummary(BaseModel):
    patient_id: str
    patient_name: str
    patient_friendly_summary: str
    clinician_brief: str
    key_findings: List[Dict[str, Any]] = Field(default_factory=list)
    active_conflicts_count: int = 0
    total_tests_count: int = 0
    abnormal_tests_count: int = 0
    disclaimer: str = (
        "IMPORTANT NOTICE: MedLens is an AI-powered clinical information organization "
        "and review assistance tool. It is NOT a diagnostic device, medical provider, or "
        "prescribing authority. MedLens does NOT offer medical diagnoses, treatment decisions, "
        "or dosage modifications. All clinical data, potential conflicts, and summaries "
        "must be reviewed and confirmed by a qualified, licensed healthcare professional."
    )
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
