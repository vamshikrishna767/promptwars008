"""
MedLens - SQLite Database Layer
Handles persistent storage for Patients, Intake records, Reports,
Lab Extractions, Inconsistency Alerts, Clarification Questions, and Audit Logs.
"""

import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "medlens.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Patients Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        sex TEXT NOT NULL,
        blood_group TEXT,
        phone TEXT,
        email TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Intake Data Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_intake (
        id TEXT PRIMARY KEY,
        patient_id TEXT UNIQUE NOT NULL,
        symptoms_json TEXT,
        conditions_json TEXT,
        allergies_json TEXT,
        medications_json TEXT,
        surgeries_json TEXT,
        family_history_json TEXT,
        lifestyle_notes TEXT,
        source TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    )
    """)

    # Medical Reports Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medical_reports (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        report_date TEXT NOT NULL,
        facility_name TEXT,
        raw_text TEXT,
        items_count INTEGER DEFAULT 0,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    )
    """)

    # Extracted Lab Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extracted_items (
        id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        patient_id TEXT NOT NULL,
        test_name TEXT NOT NULL,
        category TEXT NOT NULL,
        value TEXT NOT NULL,
        numeric_value REAL,
        unit TEXT,
        reference_range TEXT,
        range_low REAL,
        range_high REAL,
        range_status TEXT NOT NULL,
        range_source_verified INTEGER DEFAULT 0,
        test_date TEXT,
        source_snippet TEXT,
        page_number INTEGER DEFAULT 1,
        confidence REAL DEFAULT 0.95,
        verification_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
        verified_by TEXT,
        notes TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (report_id) REFERENCES medical_reports(id) ON DELETE CASCADE,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    )
    """)

    # Inconsistency and Conflict Alerts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conflict_alerts (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        conflict_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        source_entities_json TEXT,
        status TEXT DEFAULT 'ACTIVE',
        resolution_notes TEXT,
        resolved_by TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    )
    """)

    # Safe migrations for existing DB
    try:
        cursor.execute("ALTER TABLE conflict_alerts ADD COLUMN resolution_notes TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE conflict_alerts ADD COLUMN resolved_by TEXT")
    except sqlite3.OperationalError:
        pass

    # Clarification Questions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clarification_questions (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        category TEXT NOT NULL,
        question TEXT NOT NULL,
        rationale TEXT NOT NULL,
        answered INTEGER DEFAULT 0,
        answer TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    )
    """)

    # Audit Log Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        item_id TEXT,
        action TEXT NOT NULL,
        actor TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        timestamp TEXT NOT NULL,
        details TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()


# Repository Methods
class DatabaseRepo:
    @staticmethod
    def get_all_patients() -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients ORDER BY name ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_patient(patient_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create_patient(data: Dict[str, Any]) -> Dict[str, Any]:
        patient_id = data.get("id") or str(uuid.uuid4())
        created_at = data.get("created_at") or datetime.utcnow().isoformat()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO patients (id, name, age, sex, blood_group, phone, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            data["name"],
            data["age"],
            data["sex"],
            data.get("blood_group", "Unknown"),
            data.get("phone", ""),
            data.get("email", ""),
            created_at
        ))
        conn.commit()
        conn.close()
        return DatabaseRepo.get_patient(patient_id)

    @staticmethod
    def get_patient_intake(patient_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_intake WHERE patient_id = ?", (patient_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["symptoms"] = json.loads(d["symptoms_json"] or "[]")
        d["conditions"] = json.loads(d["conditions_json"] or "[]")
        d["allergies"] = json.loads(d["allergies_json"] or "[]")
        d["medications"] = json.loads(d["medications_json"] or "[]")
        d["surgeries"] = json.loads(d["surgeries_json"] or "[]")
        d["family_history"] = json.loads(d["family_history_json"] or "[]")
        return d

    @staticmethod
    def save_patient_intake(patient_id: str, intake_data: Dict[str, Any], actor: str = "Clinician Intake") -> Dict[str, Any]:
        intake_id = intake_data.get("id") or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        symptoms_json = json.dumps(intake_data.get("symptoms", []))
        conditions_json = json.dumps(intake_data.get("conditions", []))
        allergies_json = json.dumps(intake_data.get("allergies", []))
        medications_json = json.dumps(intake_data.get("medications", []))
        surgeries_json = json.dumps(intake_data.get("surgeries", []))
        family_history_json = json.dumps(intake_data.get("family_history", []))
        lifestyle_notes = intake_data.get("lifestyle_notes", "")
        source = intake_data.get("source", "Patient Intake Form")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO patient_intake (
                id, patient_id, symptoms_json, conditions_json, allergies_json,
                medications_json, surgeries_json, family_history_json, lifestyle_notes,
                source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(patient_id) DO UPDATE SET
                symptoms_json=excluded.symptoms_json,
                conditions_json=excluded.conditions_json,
                allergies_json=excluded.allergies_json,
                medications_json=excluded.medications_json,
                surgeries_json=excluded.surgeries_json,
                family_history_json=excluded.family_history_json,
                lifestyle_notes=excluded.lifestyle_notes,
                source=excluded.source,
                updated_at=excluded.updated_at
        """, (
            intake_id, patient_id, symptoms_json, conditions_json, allergies_json,
            medications_json, surgeries_json, family_history_json, lifestyle_notes,
            source, now
        ))
        conn.commit()
        conn.close()

        DatabaseRepo.log_audit(
            patient_id=patient_id,
            action="INTAKE_UPDATED",
            actor=actor,
            details=f"Updated intake: {len(intake_data.get('medications', []))} meds, {len(intake_data.get('allergies', []))} allergies"
        )
        return DatabaseRepo.get_patient_intake(patient_id)

    @staticmethod
    def create_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
        report_id = report_data.get("id") or str(uuid.uuid4())
        uploaded_at = report_data.get("uploaded_at") or datetime.utcnow().isoformat()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO medical_reports (
                id, patient_id, title, filename, file_type, uploaded_at,
                report_date, facility_name, raw_text, items_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id,
            report_data["patient_id"],
            report_data["title"],
            report_data["filename"],
            report_data.get("file_type", "txt"),
            uploaded_at,
            report_data.get("report_date", datetime.utcnow().strftime("%Y-%m-%d")),
            report_data.get("facility_name", "Clinical Laboratory"),
            report_data.get("raw_text", ""),
            report_data.get("items_count", 0)
        ))
        conn.commit()
        conn.close()
        return DatabaseRepo.get_report(report_id)

    @staticmethod
    def get_report(report_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_patient_reports(patient_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_reports WHERE patient_id = ? ORDER BY report_date DESC", (patient_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def save_extracted_items(items: List[Dict[str, Any]], actor: str = "AI Extraction Engine"):
        if not items:
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        report_id = items[0]["report_id"]
        patient_id = items[0]["patient_id"]

        for it in items:
            item_id = it.get("id") or str(uuid.uuid4())
            cursor.execute("""
                INSERT OR REPLACE INTO extracted_items (
                    id, report_id, patient_id, test_name, category, value,
                    numeric_value, unit, reference_range, range_low, range_high,
                    range_status, range_source_verified, test_date, source_snippet,
                    page_number, confidence, verification_status, verified_by, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id,
                it["report_id"],
                it["patient_id"],
                it["test_name"],
                it.get("category", "General"),
                str(it["value"]),
                it.get("numeric_value"),
                it.get("unit", ""),
                it.get("reference_range"),
                it.get("range_low"),
                it.get("range_high"),
                it.get("range_status", "UNREFERENCED"),
                1 if it.get("range_source_verified") else 0,
                it.get("test_date", ""),
                it.get("source_snippet", ""),
                it.get("page_number", 1),
                it.get("confidence", 0.95),
                it.get("verification_status", "UNREVIEWED"),
                it.get("verified_by"),
                it.get("notes", ""),
                now
            ))

        # Update report items_count
        cursor.execute("SELECT COUNT(*) FROM extracted_items WHERE report_id = ?", (report_id,))
        count = cursor.fetchone()[0]
        cursor.execute("UPDATE medical_reports SET items_count = ? WHERE id = ?", (count, report_id))

        conn.commit()
        conn.close()

        DatabaseRepo.log_audit(
            patient_id=patient_id,
            action="EXTRACTED",
            actor=actor,
            details=f"Extracted {len(items)} clinical parameters from report {report_id}"
        )

    @staticmethod
    def get_extracted_items(patient_id: str, report_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        if report_id:
            cursor.execute("""
                SELECT * FROM extracted_items 
                WHERE patient_id = ? AND report_id = ? 
                ORDER BY category ASC, test_name ASC
            """, (patient_id, report_id))
        else:
            cursor.execute("""
                SELECT * FROM extracted_items 
                WHERE patient_id = ? 
                ORDER BY test_date DESC, category ASC, test_name ASC
            """, (patient_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        for r in rows:
            r["range_source_verified"] = bool(r["range_source_verified"])
        return rows

    @staticmethod
    def update_extracted_item(item_id: str, updates: Dict[str, Any], actor: str = "Dr. Reviewer") -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM extracted_items WHERE id = ?", (item_id,))
        curr = cursor.fetchone()
        if not curr:
            conn.close()
            return None
        curr_dict = dict(curr)
        old_val = f"{curr_dict['value']} {curr_dict['unit'] or ''}".strip()

        # Build update query dynamically
        fields = []
        params = []
        for k, v in updates.items():
            if k in ["value", "unit", "reference_range", "verification_status", "notes", "verified_by", "range_status", "numeric_value"]:
                fields.append(f"{k} = ?")
                params.append(v)

        fields.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(item_id)

        cursor.execute(f"UPDATE extracted_items SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        conn.close()

        new_val = f"{updates.get('value', curr_dict['value'])} {updates.get('unit', curr_dict['unit'] or '')}".strip()
        status_action = updates.get("verification_status", "EDITED")

        DatabaseRepo.log_audit(
            patient_id=curr_dict["patient_id"],
            item_id=item_id,
            action=status_action,
            actor=actor,
            old_value=old_val,
            new_value=new_val,
            details=f"Item {curr_dict['test_name']} marked as {status_action} with note: {updates.get('notes', '')}"
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM extracted_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        conn.close()
        res = dict(row)
        res["range_source_verified"] = bool(res["range_source_verified"])
        return res

    @staticmethod
    def save_conflicts(patient_id: str, conflicts: List[Dict[str, Any]]):
        conn = get_db_connection()
        cursor = conn.cursor()
        # Preserve existing statuses and resolution notes
        cursor.execute("SELECT title, status, resolution_notes, resolved_by FROM conflict_alerts WHERE patient_id = ?", (patient_id,))
        existing_resolutions = {r["title"]: (r["status"], r["resolution_notes"], r["resolved_by"]) for r in cursor.fetchall()}

        cursor.execute("DELETE FROM conflict_alerts WHERE patient_id = ?", (patient_id,))
        now = datetime.utcnow().isoformat()
        for c in conflicts:
            cid = c.get("id") or str(uuid.uuid4())
            entities_json = json.dumps(c.get("source_entities", []))
            prev = existing_resolutions.get(c["title"])
            status = prev[0] if prev else c.get("status", "ACTIVE")
            res_notes = prev[1] if prev else c.get("resolution_notes", "")
            res_by = prev[2] if prev else c.get("resolved_by", "")

            cursor.execute("""
                INSERT INTO conflict_alerts (
                    id, patient_id, conflict_type, severity, title,
                    description, recommendation, source_entities_json, status,
                    resolution_notes, resolved_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cid, patient_id, c["conflict_type"], c["severity"], c["title"],
                c["description"], c["recommendation"], entities_json, status,
                res_notes, res_by, now
            ))
        conn.commit()
        conn.close()

    @staticmethod
    def resolve_conflict(conflict_id: str, status: str, resolution_notes: str, resolved_by: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conflict_alerts
            SET status = ?, resolution_notes = ?, resolved_by = ?
            WHERE id = ?
        """, (status, resolution_notes, resolved_by, conflict_id))
        conn.commit()
        cursor.execute("SELECT * FROM conflict_alerts WHERE id = ?", (conflict_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            r = dict(row)
            r["source_entities"] = json.loads(r["source_entities_json"] or "[]")
            DatabaseRepo.log_audit(
                patient_id=r["patient_id"],
                action=f"CONFLICT_{status.upper()}",
                actor=resolved_by,
                details=f"Conflict '{r['title']}' marked as {status}. Notes: {resolution_notes}"
            )
            return r
        return None

    @staticmethod
    def get_conflicts(patient_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conflict_alerts WHERE patient_id = ? ORDER BY severity ASC", (patient_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        for r in rows:
            r["source_entities"] = json.loads(r["source_entities_json"] or "[]")
        return rows

    @staticmethod
    def save_clarifications(patient_id: str, questions: List[Dict[str, Any]]):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        # Keep existing answers if available
        cursor.execute("SELECT question, answer, answered FROM clarification_questions WHERE patient_id = ?", (patient_id,))
        existing_answers = {r["question"]: (r["answer"], r["answered"]) for r in cursor.fetchall()}

        cursor.execute("DELETE FROM clarification_questions WHERE patient_id = ?", (patient_id,))
        for q in questions:
            qid = q.get("id") or str(uuid.uuid4())
            prev = existing_answers.get(q["question"])
            ans = prev[0] if prev else q.get("answer")
            answered = prev[1] if prev else (1 if q.get("answered") else 0)

            cursor.execute("""
                INSERT INTO clarification_questions (
                    id, patient_id, category, question, rationale, answered, answer, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                qid, patient_id, q["category"], q["question"], q["rationale"], answered, ans, now
            ))
        conn.commit()
        conn.close()

    @staticmethod
    def get_clarifications(patient_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clarification_questions WHERE patient_id = ?", (patient_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        for r in rows:
            r["answered"] = bool(r["answered"])
        return rows

    @staticmethod
    def answer_clarification(question_id: str, answer: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clarification_questions 
            SET answered = 1, answer = ? 
            WHERE id = ?
        """, (answer, question_id))
        conn.commit()
        cursor.execute("SELECT * FROM clarification_questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            res = dict(row)
            res["answered"] = bool(res["answered"])
            return res
        return None

    @staticmethod
    def log_audit(patient_id: str, action: str, actor: str, item_id: Optional[str] = None,
                  old_value: Optional[str] = None, new_value: Optional[str] = None, details: str = ""):
        conn = get_db_connection()
        cursor = conn.cursor()
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO audit_logs (
                id, patient_id, item_id, action, actor, old_value, new_value, timestamp, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (entry_id, patient_id, item_id, action, actor, old_value, new_value, now, details))
        conn.commit()
        conn.close()

    @staticmethod
    def get_audit_logs(patient_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE patient_id = ? ORDER BY timestamp DESC LIMIT 100", (patient_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
