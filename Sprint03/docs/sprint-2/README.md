# Sprint 2: Report Ingestion Platform

Sprint 2 receives GitLeaks, Trivy filesystem, Trivy image, and SonarQube JSON reports produced by GitHub Actions. SecureGate AI stores original payloads, normalizes findings, tracks scan status, and displays scan history.

```text
Create scan (RECEIVED) -> Upload JSON (PROCESSING) -> Store and normalize -> COMPLETED
```

An ingestion error creates an audit event and marks the scan `FAILED`.

## Endpoints

- `POST /api/v1/scans`
- `POST /api/v1/scans/{scan_id}/gitleaks`
- `POST /api/v1/scans/{scan_id}/trivy-fs`
- `POST /api/v1/scans/{scan_id}/trivy-image`
- `POST /api/v1/scans/{scan_id}/sonarqube`
- `GET /api/v1/scans`
- `GET /api/v1/scans/{scan_id}`
- `GET /api/v1/scans/dashboard/summary`

Create-scan request:

```json
{
  "project_name": "payment-service",
  "repository_url": "https://github.com/company/payment-service",
  "branch": "main",
  "commit_sha": "abc123"
}
```

## Migration

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/002_sprint_2_report_ingestion.sql
docker compose restart backend
```

Validate by creating a scan, uploading one report to every tool endpoint, checking raw and normalized database records, and opening the dashboard and scan details page. Swagger provides request and response examples.

No scanner execution, workflow files, scoring, recommendations, report generation, notifications, Jenkins, or AI features are included.
