# SecureGate AI - Sprint-02

SecureGate AI is a DevSecOps report ingestion and security visibility platform.

Sprint 1 established React, FastAPI, PostgreSQL, SonarQube, Prometheus, Grafana, Docker Compose, and manual tool validation. 

In Sprint 2, CI/CD executes security tools and sends JSON output to SecureGate AI. The platform does not clone repositories or execute scanners.

---

## Quick Start

```bash
cd /Users/saimausman/Desktop/securegate-ai
docker compose up -d --build
```

- Frontend: http://localhost:5173  
- Backend and Swagger: http://localhost:8000 and http://localhost:8000/docs  
- PostgreSQL: localhost:5432  
- SonarQube: http://localhost:9000  
- Prometheus: http://localhost:9090  
- Grafana: http://localhost:3000


<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/3ad0f3b7-b54f-4339-8dec-44dd62310cc0" />


<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/d12cfd33-43c2-41b4-abcc-a9dc1bc772bb" />


<img width="2536" height="852" alt="image" src="https://github.com/user-attachments/assets/876eae98-a83f-4c68-8321-cb832899eced" />


----

## Sprint 2 API

Create metadata with `POST /api/v1/scans`. Upload vendor JSON through:

- `POST /api/v1/scans/{scan_id}/gitleaks`
- `POST /api/v1/scans/{scan_id}/trivy-fs`
- `POST /api/v1/scans/{scan_id}/trivy-image`
- `POST /api/v1/scans/{scan_id}/sonarqube`

<img width="1280" height="367" alt="Screenshot 2026-06-23 at 12 22 37 AM" src="https://github.com/user-attachments/assets/2fca2fc6-640d-4ec2-b944-ea179f4a2c29" />


<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/b568782a-a2ca-4737-9c5e-0a48b006b219" />

<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/03ace0f9-e4bf-46cc-8fcd-9668773dfdf1" />

<img width="2560" height="1394" alt="image" src="https://github.com/user-attachments/assets/33822818-b1f1-4593-b125-dfefc80ad195" />



----

### Upgrade an existing Sprint 1 database:

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

<img width="1258" height="448" alt="Screenshot 2026-06-23 at 12 36 06 AM" src="https://github.com/user-attachments/assets/a24d3227-0e79-42ab-a719-87c07d46260b" />


-----

## What has Sprint 2 built?

✅ Report Upload API \
✅ Scan ID Generation \
✅ Database Storage \
✅ Dashboard Scan History \
✅ Report Normalization Layer


Built **SecureGate-AI** APIs to receive reports.

POST /scans
POST /gitleaks-report
POST /trivy-report
POST /sonarqube-report

**Simulate what GitHub Actions/Jenkins Pipeline will eventually do at later stages.**

Let's manually do:

```
Postman
     ↓
SecureGate AI
```

and verify:

✅ Scan is created \
✅ Reports are uploaded \
✅ Findings are stored \
✅ Dashboard updates

-------

## Summary

Sprint 2 receives GitLeaks, Trivy filesystem, Trivy image, and SonarQube JSON reports produced by GitHub Actions. SecureGate AI stores original payloads, normalizes findings, tracks scan status, and displays scan history.

------
