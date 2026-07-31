import unittest
from types import SimpleNamespace

from app.services.recommendations import generate_recommendations
from app.services.security_gate import calculate_security_score, evaluate_scan


def finding(tool: str, severity: str):
    return SimpleNamespace(tool=tool, severity=severity)


class SecurityGateTests(unittest.TestCase):
    def test_score_uses_trivy_vulnerabilities_only(self):
        findings = [finding("trivy-fs", "CRITICAL"), finding("trivy-image", "HIGH"), finding("gitleaks", "HIGH")]
        score, counts = calculate_security_score(findings)
        self.assertEqual(score, 77)
        self.assertEqual(counts, {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 0})

    def test_secret_forces_rejection(self):
        scan = SimpleNamespace(sonar_quality_gate="OK", security_score=None, deployment_decision="PENDING", evaluated_at=None)
        result = evaluate_scan(scan, [finding("gitleaks", "HIGH")])
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["decision"], "REJECTED")

    def test_failed_quality_gate_forces_rejection(self):
        scan = SimpleNamespace(sonar_quality_gate="ERROR", security_score=None, deployment_decision="PENDING", evaluated_at=None)
        result = evaluate_scan(scan, [])
        self.assertEqual(result["decision"], "REJECTED")

    def test_clean_scan_is_approved(self):
        scan = SimpleNamespace(sonar_quality_gate="OK", security_score=None, deployment_decision="PENDING", evaluated_at=None)
        result = evaluate_scan(scan, [])
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["decision"], "APPROVED")
        self.assertTrue(generate_recommendations(scan, []))


if __name__ == "__main__":
    unittest.main()
