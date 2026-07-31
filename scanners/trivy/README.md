# Trivy Manual Validation

Trivy scans container images, filesystems, Git repositories, and configuration files for vulnerabilities and misconfigurations.

Sprint 1 validates Trivy manually only. It is not connected to the FastAPI backend or any CI/CD pipeline yet.

## Installation

macOS with Homebrew:

```bash
brew install aquasecurity/trivy/trivy
```

Linux:

```bash
sudo apt-get update
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo gpg --dearmor -o /usr/share/keyrings/trivy.gpg
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy
```

Docker:

```bash
docker run --rm -v "$PWD:/workspace" aquasec/trivy:latest fs /workspace
```

## Filesystem Scan Example

Run from the repository root:

```bash
trivy fs .
```

Expected output shape:

```text
Report Summary
Target: package-lock.json
Vulnerabilities: LOW, MEDIUM, HIGH, CRITICAL
```

## Image Scan Example

```bash
trivy image python:3.7
```

Expected output shape:

```text
python:3.7 (debian 11.x)
Total: 100+ (UNKNOWN: 0, LOW: 20, MEDIUM: 40, HIGH: 30, CRITICAL: 10)
```

## Useful Sprint 1 Options

Scan only high and critical vulnerabilities:

```bash
trivy image --severity HIGH,CRITICAL python:3.7
```

Generate JSON output for later inspection:

```bash
trivy image --format json --output reports/trivy-python-3.7.json python:3.7
```

## Sprint 1 Validation Checklist

- Trivy is installed.
- `trivy fs .` runs successfully.
- `trivy image python:3.7` runs successfully.
- Output is captured as a screenshot or terminal copy for documentation.
