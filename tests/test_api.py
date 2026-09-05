"""
Integration Tests for MedLens FastAPI Endpoints
Validates patient retrieval, intake updating, report extraction,
human-in-the-loop verification patch, longitudinal trends, and PDF export.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.sample_data import seed_database


class TestMedLensAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database()
        cls.client = TestClient(app)

    def test_get_patients(self):
        resp = self.client.get("/api/patients")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data), 3)

    def test_get_patient_intake(self):
        resp = self.client.get("/api/patients/patient-sarah-jenkins/intake")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("symptoms", data)
        self.assertTrue(any(a["allergen"] == "Penicillin" for a in data.get("allergies", [])))

    def test_get_extracted_items_and_provenance(self):
        resp = self.client.get("/api/patients/patient-sarah-jenkins/extracted")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertGreaterEqual(len(items), 10)
        # Check source snippet and reference range presence
        first = items[0]
        self.assertIn("source_snippet", first)
        self.assertIn("range_status", first)

    def test_human_verification_patch(self):
        # Retrieve an item
        resp = self.client.get("/api/patients/patient-sarah-jenkins/extracted")
        items = resp.json()
        target_item = items[0]
        item_id = target_item["id"]

        # Clinician verifies and updates note
        patch_payload = {
            "verification_status": "VERIFIED",
            "notes": "Clinician verified against raw hospital lab sheet.",
            "verified_by": "Dr. House"
        }
        patch_resp = self.client.patch(f"/api/extracted/{item_id}", json=patch_payload)
        self.assertEqual(patch_resp.status_code, 200)
        updated = patch_resp.json()
        self.assertEqual(updated["verification_status"], "VERIFIED")
        self.assertEqual(updated["verified_by"], "Dr. House")

    def test_conflicts_endpoint(self):
        resp = self.client.get("/api/patients/patient-sarah-jenkins/conflicts")
        self.assertEqual(resp.status_code, 200)
        conflicts = resp.json()
        # Sarah has Penicillin allergy vs Amoxicillin med -> Critical conflict
        self.assertTrue(any("Penicillin" in c["title"] for c in conflicts))

    def test_longitudinal_endpoint(self):
        resp = self.client.get("/api/patients/patient-sarah-jenkins/longitudinal")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("biomarkers", data)
        # Check that HbA1c or Glucose has multi-point trends
        multi_points = [b for b in data["biomarkers"] if b["points_count"] >= 2]
        self.assertGreaterEqual(len(multi_points), 1)

    def test_pdf_export_endpoint(self):
        resp = self.client.get("/api/patients/patient-sarah-jenkins/export/pdf")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertGreater(len(resp.content), 1000)

    def test_json_export_endpoint(self):
        resp = self.client.get("/api/patients/patient-sarah-jenkins/export/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["resourceType"], "Bundle")
        self.assertIn("disclaimer", data["meta"])


if __name__ == "__main__":
    unittest.main()
