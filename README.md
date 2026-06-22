# SecureGate AI

SecureGate AI is a DevSecOps report ingestion and security visibility platform.

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

Sprint 2 excludes scanner execution, CI workflow files, Jenkins, scoring, recommendations, generated reports, notifications, and AI features.
