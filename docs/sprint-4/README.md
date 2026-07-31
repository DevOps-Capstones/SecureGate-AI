# Sprint 4: DevSecOps Workflow Automation

Sprint 4 converts SecureGate AI into an automated workflow platform while preserving the locked architecture: GitHub Actions runs scanners and SecureGate AI receives, stores, normalizes, scores, reports, notifies, and displays results.

## Required Environment

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

## GitHub Integration

All GitHub Actions automation endpoints require:

```text
Authorization: Bearer <SECUREGATE_API_KEY>
```

Start a pipeline scan:

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/start \
  -H "Authorization: Bearer $SECUREGATE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"payment-service","repository_url":"https://github.com/company/payment-service","branch":"main","commit_sha":"abc123","pipeline_run_id":"123456"}'
```

Complete a pipeline scan:

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/complete \
  -H "Authorization: Bearer $SECUREGATE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scan_id":"SCAN-20260701-0001","status":"SUCCESS"}'
```

## Report Uploads

Existing upload endpoints now save raw JSON to disk and database:

- `POST /api/v1/scans/{scan_id}/gitleaks`
- `POST /api/v1/scans/{scan_id}/semgrep`
- `POST /api/v1/scans/{scan_id}/trivy-fs`
- `POST /api/v1/scans/{scan_id}/trivy-image`
- `POST /api/v1/scans/{scan_id}/sonarqube`
- `POST /api/v1/scans/{scan_id}/unit-tests`

Files are persisted under:

```text
storage/scans/<scan_id>/gitleaks-report.json
storage/scans/<scan_id>/trivy-fs-report.json
storage/scans/<scan_id>/trivy-image-report.json
storage/scans/<scan_id>/sonarqube-report.json
storage/scans/<scan_id>/deployment_approval.pdf
storage/scans/<scan_id>/deployment_approval.docx
storage/scans/<scan_id>/deployment_approval.json
```

## Notifications

Slack webhook and SMTP notifications are sent after all required reports are uploaded and the master report is generated. If credentials are missing, notification rows are stored with `SKIPPED` status so the dashboard still shows delivery history.

## Dashboard

The dashboard refreshes automatically and displays active scans, recent scans, latest decisions, latest security score, report downloads, and recent notification events.

## Migration

Apply the Sprint 4 migration to an existing database:

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/004_sprint_4_workflow_automation.sql
docker compose restart backend
```

Fresh Docker volumes create all tables automatically during backend startup.

## CI/CD Runner Examples

SecureGate AI supports two independent runner options:

- GitHub Actions: `examples/github-actions/securegate.yml`
- Jenkins: `examples/jenkins/Jenkinsfile.securegate`

Choose one runner per repository. Each runner starts a SecureGate scan, runs GitLeaks, Trivy filesystem, Docker build, Trivy image, and SonarCloud/SonarQube checks, uploads all reports to SecureGate AI, reads the deployment decision, updates the dashboard through the API, and completes the pipeline lifecycle. Docker Hub push is optional and only occurs after SecureGate AI returns `APPROVED` and Docker credentials are configured. After a successful push, the runner rescans the pushed Docker image and uploads the refreshed Trivy image report so the dashboard reflects the pushed artifact.

GitHub Actions no longer triggers Jenkins and no manual deployment approval environment is required for the sample workflow.


## Scheduled Summary Alerts

SecureGate AI does not run a background scheduler. Use GitHub Actions cron to call the summary endpoints automatically.

- Daily endpoint: `POST /api/v1/notifications/summary/daily`
- Weekly endpoint: `POST /api/v1/notifications/summary/weekly`
- Example workflow: `examples/github-actions/securegate-summary.yml`

The summary tells the DevOps team how many projects were scanned, how many scans passed or failed, and how many critical, high, medium, and low vulnerabilities were found for each project. It also shows pending and resolved finding totals in simple language.
