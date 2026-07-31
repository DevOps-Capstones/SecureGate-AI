# Sprint 1 Setup Guide

## Prerequisites

Install:

- Docker Desktop or Docker Engine
- Docker Compose v2
- GitLeaks
- Trivy

Optional:

- Node.js 22 for frontend local development outside Docker
- Python 3.11+ for backend local development outside Docker

## Start the Platform

From the `securegate-ai` directory:

```bash
docker compose up -d --build
```

Check containers:

```bash
docker compose ps
```

## Validate Backend

Open:

```text
http://localhost:8000
```

Expected:

```json
{
  "application": "SecureGate AI",
  "version": "0.1.0"
}
```

Open:

```text
http://localhost:8000/health
```

Expected:

```json
{
  "status": "healthy"
}
```

## Validate Frontend

Open:

```text
http://localhost:5173
```

Confirm these pages render:

- Dashboard
- Projects
- Reports
- Settings

## Validate PostgreSQL

Connect with a database client:

```text
Host: localhost
Port: 5432
Database: securegate
Username: securegate
Password: securegate_password
```

Confirm tables:

- `projects`
- `scans`
- `reports`

## Validate SonarQube

Open:

```text
http://localhost:9000
```

Use:

- Username: `admin`
- Password: `admin`

## Validate Prometheus

Open:

```text
http://localhost:9090
```

Navigate to:

```text
Status > Targets
```

## Validate Grafana

Open:

```text
http://localhost:3000
```

Use:

- Username: `admin`
- Password: `admin`

Confirm the Prometheus datasource exists.

## Stop the Platform

```bash
docker compose down
```

To remove volumes:

```bash
docker compose down -v
```
