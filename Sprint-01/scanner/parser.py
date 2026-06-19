import json
import os

# Path to Trivy report
REPORT_FILE = "reports/nginx-reports.json"

# Severity counters
severity_count = {
    "CRITICAL": 0,
    "HIGH": 0,
    "MEDIUM": 0,
    "LOW": 0,
    "UNKNOWN": 0
}

# Check if file exists
if not os.path.exists(REPORT_FILE):
    print(f"Error: Report file not found: {REPORT_FILE}")
    exit(1)

# Load JSON report
with open(REPORT_FILE, "r") as file:
    data = json.load(file)

total_vulnerabilities = 0

print("\nVulnerability Details")
print("=" * 80)

# Parse vulnerabilities
for result in data.get("Results", []):

    target = result.get("Target", "Unknown Target")
    vulnerabilities = result.get("Vulnerabilities", [])

    if vulnerabilities:
        print(f"\nTarget: {target}")

    for vuln in vulnerabilities:

        cve = vuln.get("VulnerabilityID", "N/A")
        severity = vuln.get("Severity", "UNKNOWN")
        package = vuln.get("PkgName", "N/A")
        installed_version = vuln.get("InstalledVersion", "N/A")
        fixed_version = vuln.get("FixedVersion", "Not Available")

        print(
            f"CVE: {cve} | "
            f"Severity: {severity} | "
            f"Package: {package}"
        )

        severity_count[severity] = severity_count.get(severity, 0) + 1
        total_vulnerabilities += 1

print("\n" + "=" * 80)
print("VULNERABILITY SUMMARY")
print("=" * 80)

print(f"Total Vulnerabilities : {total_vulnerabilities}")
print(f"Critical             : {severity_count['CRITICAL']}")
print(f"High                 : {severity_count['HIGH']}")
print(f"Medium               : {severity_count['MEDIUM']}")
print(f"Low                  : {severity_count['LOW']}")
print(f"Unknown              : {severity_count['UNKNOWN']}")

print("=" * 80)

# Optional Build Status Logic
if severity_count["CRITICAL"] > 0:
    print("\nBuild Status: FAIL (Critical vulnerabilities detected)")
elif severity_count["HIGH"] > 0:
    print("\nBuild Status: WARNING (High vulnerabilities detected)")
else:
    print("\nBuild Status: PASS")
