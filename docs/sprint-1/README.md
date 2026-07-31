# Sprint 1 Documentation

Sprint 1 establishes the SecureGate AI foundation and validates core DevSecOps tools.

## Deliverables

- Docker Compose stack for frontend, backend, PostgreSQL, SonarQube, Prometheus, and Grafana
- FastAPI backend with root and health endpoints
- React + TypeScript frontend with Dashboard, Projects, Reports, and Settings pages
- PostgreSQL initial schema
- Manual GitLeaks validation guide
- Manual Trivy validation guide
- SonarQube setup guide
- Monitoring setup guide

## Service URLs

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Backend health: http://localhost:8000/health
- PostgreSQL: localhost:5432
- SonarQube: http://localhost:9000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Sprint Achievements

- Project folder structure created.
- Core application services containerized.
- Manual scanner validation instructions created.
- Initial database schema defined.
- Monitoring services provisioned with a Prometheus datasource for Grafana.

## Validation Screenshot Placeholders

Add screenshots after local validation:

- `frontend-running.png`
- `backend-health.png`
- `postgres-running.png`
- `sonarqube-login.png`
- `prometheus-targets.png`
- `grafana-home.png`
- `gitleaks-output.png`
- `trivy-fs-output.png`
- `trivy-image-output.png`
