# Sprint 1 Tool Validation

## GitLeaks

Run:

```bash
gitleaks detect .
```

Pass criteria:

- Command completes successfully.
- Output shows either no leaks or a list of detected findings.
- Result is captured for Sprint 1 validation evidence.

## Trivy Filesystem Scan

Run:

```bash
trivy fs .
```

Pass criteria:

- Command completes successfully.
- Vulnerability summary is displayed.
- Result is captured for Sprint 1 validation evidence.

## Trivy Image Scan

Run:

```bash
trivy image python:3.7
```

Pass criteria:

- Trivy pulls or inspects the image.
- Vulnerability summary is displayed.
- Result is captured for Sprint 1 validation evidence.

## SonarQube

Run SonarQube through Docker Compose:

```bash
docker compose up -d sonarqube
```

Pass criteria:

- SonarQube opens at `http://localhost:9000`.
- Login works with default credentials.
- A sample project can be created manually.

## Evidence Checklist

Add screenshots or terminal captures for:

- GitLeaks output
- Trivy filesystem scan output
- Trivy image scan output
- SonarQube login page
- Docker Compose running services
