# SecureGate AI

Enterprise DevSecOps Security Orchestration Platform.

This repository contains the Sprint 1 foundation for SecureGate AI. Sprint 1 validates the core platform services and manual security tools only.

## Sprint-1 (Phase-02) Scope

Included:

- React + TypeScript frontend dashboard
- FastAPI backend service
- PostgreSQL database with initial schema
- SonarQube service
- Prometheus service
- Grafana service
- Manual GitLeaks validation guide
- Manual Trivy filesystem and image scan guide
- Docker Compose orchestration
- Sprint 1 documentation

## Quick Start

From the `securegate-ai` directory:

```bash
docker compose up -d --build
```

**you should see:**

✅ Frontend \
✅ Backend \
✅ PostgreSQL \
✅ SonarQube \
✅ Prometheus \
✅ Grafana 

running successfully.

<img width="2512" height="1350" alt="image" src="https://github.com/user-attachments/assets/99b6886a-0b0c-4051-8222-111b494f84e5" />


-----

check:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Backend health: http://localhost:8000/health
- PostgreSQL: http://localhost:5432
- SonarQube: http://localhost:9000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

Default `Grafana` credentials:

- Username: `admin`
- Password: `admin`
- New Password `admin123`

Default `SonarQube` credentials:

- Username: `admin`
- Password: `admin`
- New Password `admin123`


SonarQube may require a password change on first login.

----

## What Sprint 1 Demonstrates

`React Dashboard`

Open:

```
http://localhost:5173
```

You should see:
SecureGate AI Dashboard

✅ Dashboard \
✅ Projects \
✅ Reports \
✅ Settings

using dummy/mock data.

<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/8c4eb11c-d909-4ecf-83fc-8fb3d944a48c" />

<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/406028a1-e776-4564-9494-4a2e5418a856" />

<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/1373e2af-f17b-43ab-b526-fba1b0e801fe" />

<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/24c5a937-bfa3-464a-86ec-0c178d0598b2" />

----

## FastAPI Backend

Open:
```
http://localhost:8000/docs
```

You should see `Swagger UI`.

Endpoints:
```
GET /
GET /health
```

<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/cec40c15-b254-45cd-9279-dc07d4a3b359" />



---

## Grafana

Open:
```
http://localhost:3000
```

✅ Login works. \
✅ No real dashboards yet. \
✅ Only setup completed.

<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/e7c426b6-557b-44d2-9a12-83072aa019ad" />


----

## Prometheus

Open:
```
http://localhost:9090
```

✅ Prometheus is collecting metrics. \
✅ Nothing exciting yet. \
✅ Just working.


<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/a465df12-7a53-4c1b-a9d6-ab7fa4669943" />


----

## SonarQube

Open:
```
http://localhost:9000
```

You can:

✅ Login \
✅ Create a project \
✅ Generate token \
✅ Scan a test repository


### Example results:

```
Code Smells: 25

Bugs: 3

Security Hotspots: 4

Coverage: 78% 
```


<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/6b3c4cf2-335e-45e4-b90f-2bc21e6fbddf" />


----

## PostgreSQL

✅ Database running. \
✅ Tables exist: \
    ✅ projects \
    ✅ scans \
    ✅ reports

You can verify:
```
SELECT * FROM projects;
```

<img width="2272" height="1242" alt="image" src="https://github.com/user-attachments/assets/f848cc44-2ed4-471f-a84e-d1b757f2f09c" />


----


## Manual Tool Validation

GitLeaks:

```bash
gitleaks detect .
```

<img width="1774" height="788" alt="image" src="https://github.com/user-attachments/assets/3f68bff6-89d0-4a37-b6c0-6dde57fa0f14" />



Trivy filesystem scan:

```bash
trivy fs .
```

<img width="2480" height="798" alt="image" src="https://github.com/user-attachments/assets/5a66b70b-8485-48d0-bded-d8f139f92c6a" />



Trivy image scan:

```bash
trivy image python:3.7
```

<img width="2494" height="910" alt="image" src="https://github.com/user-attachments/assets/2d44fe63-bea7-4821-92d0-9bdbf9c4eb22" />


---

### For more Validation Check:

`docs/sprint-1/Tool-Validation.md`, \
`scanners/gitleaks/README.md`, and \
`scanners/trivy/README.md` for detailed validation steps.

---

## Project Tree (Sprint-1 Pahse-02)

```text
securegate-ai/
├── backend/
├── database/
├── docker/
├── docs/
│   └── sprint-1/
├── frontend/
├── monitoring/
│   ├── grafana/
│   └── prometheus/
├── reports/
├── scanners/
│   ├── gitleaks/
│   ├── sonarqube/
│   └── trivy/
├── scripts/
├── docker-compose.yml
└── README.md
```

----

## Summary 

Sprint 1 delivers a fully containerized SecureGate AI foundation with all core services deployed and all security scanning tools validated independently, ready for CI/CD automation in Sprint 2. 
