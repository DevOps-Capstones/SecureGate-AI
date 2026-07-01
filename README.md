# SecureGate AI - Sprint 04

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

----

## Sprint 3

Sprint 3 calculates a 0-100 security score, records `APPROVED` or `REJECTED` deployment decisions, generates prioritized rule-based recommendations, and stores a canonical master report. Reports are available as PDF, DOCX, and JSON, with 12-month history filters in the dashboard.

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/003_sprint_3_security_decision_engine.sql
docker compose restart backend
```

Export endpoints are documented at `http://localhost:8000/docs` under `reports`.

----

Future Enhancement:

Scanner execution, CI workflow files, Jenkins, notifications, LLM recommendations, and monitoring dashboards.


## Sprint 4 Workflow Automation

Sprint 4 adds API-key protected GitHub Actions automation, lifecycle tracking, stored report delivery, Slack/SMTP notification history, automatic dashboard refresh, and audit visibility.

Set these variables for automation:

```bash
SECUREGATE_API_KEY=replace-with-a-long-token
PUBLIC_BACKEND_URL=http://localhost:8000
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=security@example.com
SMTP_PASSWORD=replace-me
SMTP_FROM=security@example.com
```

Pipeline endpoints:

- `POST /api/v1/pipeline/start`
- `POST /api/v1/pipeline/complete`

Report uploads remain under `POST /api/v1/scans/{scan_id}/{tool}` and now require `Authorization: Bearer <SECUREGATE_API_KEY>` for GitHub Actions automation.

Stored reports are served from `storage/scans/<scan_id>/` through:

- `GET /api/v1/reports/{scan_id}/pdf`
- `GET /api/v1/reports/{scan_id}/docx`
- `GET /api/v1/reports/{scan_id}/json`

Detailed Sprint 4 guidance is in `docs/sprint-4/README.md`. Independent runner examples are available at `examples/github-actions/securegate.yml` and `examples/jenkins/Jenkinsfile.securegate`.


## Project Registry and Health Dashboard

SecureGate AI now registers projects with generated IDs such as `PRJ-YYYYMMDD-0001`. A registered project maps to one GitHub repository URL. GitHub Actions still submits `project_name` and `repository_url`; SecureGate AI attaches scans to the matching registered project or creates one automatically if needed, when the scan pipeline runs.

Use `Projects -> Register your project` in the frontend, then choose one runner: copy either `examples/github-actions/securegate.yml` or `examples/jenkins/Jenkinsfile.securegate` into the repository pipeline. Do not chain GitHub Actions to Jenkins; both templates perform scanning, Docker image build, image scanning, report upload, dashboard update, notification triggering, and SecureGate decision enforcement independently. When approved and Docker Hub credentials exist, the runner pushes the image, rescans the pushed artifact, and uploads the refreshed image report.

----

## Updated Dashboard

<img width="2556" height="1534" alt="image" src="https://github.com/user-attachments/assets/68a9b54c-c954-48ab-ae8c-de9d1086b86a" />

<img width="2560" height="1516" alt="image" src="https://github.com/user-attachments/assets/31ed046f-b277-4914-aeee-ff71cf28a857" />

<img width="2558" height="1522" alt="image" src="https://github.com/user-attachments/assets/6b9c7b97-d2ed-4c40-916d-7d0e05e80374" />

<img width="2560" height="1504" alt="image" src="https://github.com/user-attachments/assets/00168fe3-9001-45a3-8b37-f17620048bc1" />

<img width="2560" height="1530" alt="image" src="https://github.com/user-attachments/assets/89ded675-60a7-464b-9b44-d1860936ac56" />

<img width="2560" height="1510" alt="image" src="https://github.com/user-attachments/assets/27661c88-8bd6-4f0b-a6c1-e6a2ab5348a4" />



<img width="2538" height="1212" alt="image" src="https://github.com/user-attachments/assets/237a5a7c-39ff-4ed1-ba09-62bf6d900d5b" />

<img width="2532" height="1336" alt="image" src="https://github.com/user-attachments/assets/d0343294-f55a-4f60-a6e4-c4390f8b9e0d" />

<img width="2560" height="1504" alt="image" src="https://github.com/user-attachments/assets/922680c4-d149-41aa-a9e0-9ee43e3e35a9" />


------

## Sprint 05 Implemntation:

Sprint 5 will transform SecureGate AI from an automated DevSecOps pipeline integration platform into a Security Operations & Monitoring Platform by adding enterprise-grade monitoring, alerting, metrics collection, historical analytics, and Grafana dashboards. 

------




