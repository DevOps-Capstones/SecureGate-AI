# SecureGate AI Sprint 1 Architecture

## Overview

Sprint 1 creates a local development foundation for SecureGate AI. The platform starts the application shell, database, code quality service, and monitoring tools through Docker Compose.

## Components

### Frontend

- React
- TypeScript
- Vite
- React Router

The frontend provides four mock-data pages:

- Dashboard
- Projects
- Reports
- Settings

No backend integration is implemented in Sprint 1.

### Backend

- FastAPI
- Python 3.11
- Uvicorn

Endpoints:

- `GET /`
- `GET /health`

Scanning services, reports, scoring, recommendations, and notifications are not implemented in Sprint 1.

### Database

- PostgreSQL 16
- Initial schema mounted through Docker Compose

Tables:

- `projects`
- `scans`
- `reports`

### Security Tools

Manual validation only:

- GitLeaks for secret scanning
- Trivy filesystem scanning
- Trivy image scanning
- SonarQube for static analysis platform validation

### Monitoring

- Prometheus
- Grafana

Sprint 1 provides starter service deployment and a Grafana datasource. Vulnerability metrics and dashboards are planned for later sprints.

## Local Service Flow

```text
Browser
  |
  |-- localhost:5173 --> React frontend
  |
  |-- localhost:8000 --> FastAPI backend

FastAPI backend
  |
  |-- postgres:5432 --> PostgreSQL

Grafana
  |
  |-- prometheus:9090 --> Prometheus
```

## Docker Network

All Compose services run on the `securegate-network` bridge network.
