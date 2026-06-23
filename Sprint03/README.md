# SecureGate AI

SecureGate AI is a DevSecOps report ingestion, security decision, and reporting platform.

Sprint 1 established React, FastAPI, PostgreSQL, SonarQube, Prometheus, Grafana, Docker Compose, and manual tool validation. In Sprint 2, CI/CD executes security tools and sends JSON output to SecureGate AI. The platform does not clone repositories or execute scanners.

## Quick Start

```bash
cd /Users/saimausman/Desktop/securegate-ai
docker compose up -d --build
```

Frontend: http://localhost:5173  
Backend and Swagger: http://localhost:8000 and http://localhost:8000/docs  
PostgreSQL: localhost:5432  
SonarQube: http://localhost:9000  
Prometheus: http://localhost:9090  
Grafana: http://localhost:3000

## Sprint 2 API

Create metadata with `POST /api/v1/scans`. Upload vendor JSON through:

- `POST /api/v1/scans/{scan_id}/gitleaks`
- `POST /api/v1/scans/{scan_id}/trivy-fs`
- `POST /api/v1/scans/{scan_id}/trivy-image`
- `POST /api/v1/scans/{scan_id}/sonarqube`

Upgrade an existing Sprint 1 database:

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/002_sprint_2_report_ingestion.sql
docker compose restart backend
```

Fresh database volumes execute migrations automatically.

## Verification

```bash
docker compose config --quiet
python3 -m compileall -q backend/app
cd frontend && npm run build
```

## Sprint 3

Sprint 3 calculates a 0-100 security score, records `APPROVED` or `REJECTED` deployment decisions, generates prioritized rule-based recommendations, and stores a canonical master report. Reports are available as PDF, DOCX, and JSON, with 12-month history filters in the dashboard.

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/003_sprint_3_security_decision_engine.sql
docker compose restart backend
```

Export endpoints are documented at `http://localhost:8000/docs` under `reports`.

Sprint 3 excludes scanner execution, CI workflow files, Jenkins, notifications, LLM recommendations, and monitoring dashboards.
