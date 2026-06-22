# Sprint 2 Documentation

Sprint 2 transforms SecureGate AI from manually validated services into an automated repository scan orchestration platform.

## Implemented Features

- Repository URL submission through `POST /api/v1/scans`
- Unique scan ID generation using `SCAN-YYYYMMDD-XXXX`
- Temporary repository cloning with Git
- GitLeaks secret scan execution through subprocess
- Trivy filesystem vulnerability scan execution through subprocess
- Security gate approval logic
- PostgreSQL persistence for scan metadata and findings
- Recent scans API for dashboard widgets
- Scan details API
- React dashboard integration
- React scan details page
- React repository submission form
- Swagger request and response models

## Security Gate

Deployment is approved only when:

- GitLeaks findings count is zero
- Trivy critical vulnerability count is zero

Deployment is blocked when:

- Any secret is detected
- Any critical vulnerability is detected

## API Endpoints

### POST /api/v1/scans

Request:

```json
{
  "repository_url": "https://github.com/org/project"
}
```

Response:

```json
{
  "scan_id": "SCAN-20260622-0001",
  "status": "PASSED",
  "deployment_approved": true,
  "critical_count": 0,
  "high_count": 3,
  "medium_count": 8,
  "secrets_count": 0
}
```

### GET /api/v1/scans

Returns recent scan summaries for the dashboard.

### GET /api/v1/scans/{scan_id}

Returns scan metadata, GitLeaks findings, Trivy findings, and deployment status.

## Database Changes

Sprint 2 extends `scans` with:

- `repository_url`
- `deployment_approved`
- `started_at`
- `completed_at`
- `critical_count`
- `high_count`
- `medium_count`
- `low_count`
- `secrets_count`

Sprint 2 adds `scan_findings` for storing GitLeaks and Trivy findings.

Migration file:

```text
database/migrations/002_sprint_2_scan_orchestration.sql
```

The backend also runs idempotent startup schema checks so existing Sprint 1 database volumes can be upgraded safely.

## Testing Checklist

- `GET /health` returns healthy.
- `GET /docs` shows scan endpoints.
- `POST /api/v1/scans` clones a public repository.
- GitLeaks runs and stores findings.
- Trivy filesystem scan runs and stores findings.
- Deployment is blocked when secrets or critical vulnerabilities exist.
- Dashboard shows recent scans.
- Projects page submits repository URLs.
- Scan details page shows stored findings.

## Out of Scope

- Jenkins integration
- GitHub Actions workflow files
- SonarQube execution
- Docker image build
- Trivy image scan
- Report file generation
- Slack or email notifications
- AI recommendation layer
- Security score formula
