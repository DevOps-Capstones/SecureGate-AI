import unittest

from app.services.sonarqube import extract_quality_gate_status, normalize_sonarqube_report


class SonarQubeTests(unittest.TestCase):
    def test_extracts_project_status_from_sonarqube_api_payload(self):
        payload = {"projectStatus": {"status": "ERROR"}}
        self.assertEqual(extract_quality_gate_status(payload), "ERROR")

    def test_maps_pass_alias_to_ok(self):
        payload = {"qualityGateStatus": "PASSED"}
        self.assertEqual(extract_quality_gate_status(payload), "OK")

    def test_normalizes_sonar_issues(self):
        payload = {"issues": [{"severity": "MAJOR", "rule": "typescript:S123", "component": "app.ts", "message": "Fix this."}]}
        findings = normalize_sonarqube_report(payload)
        self.assertEqual(findings[0]["severity"], "HIGH")
        self.assertEqual(findings[0]["source_tool"], "SonarQube")


if __name__ == "__main__":
    unittest.main()
