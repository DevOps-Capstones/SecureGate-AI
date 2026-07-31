# Sprint 5 Monitoring And Alertmanager Guide

SecureGate AI Sprint 5 adds Alertmanager-backed monitoring without changing the locked architecture. CI runners still execute GitLeaks, Semgrep, Trivy, SonarQube, unit tests, Docker build, and image scan. SecureGate AI receives reports, stores findings, calculates decisions, exposes Prometheus metrics, and sends alerts.

## Services

- SecureGate API: http://localhost:8000
- SecureGate metrics: http://localhost:8000/metrics
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Grafana: http://localhost:3000

## Alert Flow

```text
SecureGate AI /metrics
  -> Prometheus alert rules
  -> Alertmanager routing
  -> SecureGate webhook
  -> Dashboard alert records
  -> Slack for all severities
  -> Email for CRITICAL and HIGH only
```

Alertmanager posts to `POST /api/v1/alerts/webhook-placeholder`. The backend stores the alert, applies the notification routing policy, and records delivery status.

## Configurable Thresholds

Set these values in `.env`, then restart the backend and Prometheus/Alertmanager services.

| Variable | Default | Purpose |
| --- | ---: | --- |
| `CRITICAL_VULNERABILITY_THRESHOLD` | `0` | Alert when critical vulnerabilities are above this value. |
| `HIGH_VULNERABILITY_THRESHOLD` | `5` | Alert when high vulnerabilities exceed this value. |
| `SECURITY_SCORE_THRESHOLD` | `80` | Minimum passing security score. |
| `BLOCK_HIGH_VULNERABILITIES` | `true` | Blocks deployment when high vulnerabilities exceed threshold. |
| `QUALITY_GATE_REQUIRED` | `true` | Blocks deployment and alerts when SonarQube quality gate fails. |
| `SECRET_DETECTION_REQUIRED` | `true` | Blocks deployment and alerts when secrets are detected. |
| `ALERT_ESCALATION_MINUTES` | `30` | Age after which open alerts can be escalated. |

## Alert Rules

Rules live in `monitoring/prometheus/rules/securegate-alerts.yml`. Sprint 5 keeps the rules focused on SecureGate AI security events only.

| Alert | Severity | Trigger |
| --- | --- | --- |
| `CriticalVulnerabilityDetected` | CRITICAL | Critical vulnerabilities exceed `CRITICAL_VULNERABILITY_THRESHOLD`. |
| `HighVulnerabilityThresholdReached` | HIGH | High vulnerabilities exceed `HIGH_VULNERABILITY_THRESHOLD`. |
| `SecretsDetected` | CRITICAL | GitLeaks findings exist and secret detection is required. |
| `SonarQubeQualityGateFailed` | HIGH | SonarQube/SonarCloud quality gate is failed or errored. |
| `DeploymentBlocked` | CRITICAL | SecureGate AI has rejected one or more deployments. |
| `MasterReportGenerationFailed` | MEDIUM | Scan/report generation failed before report completion. |
| `NotificationDeliveryFailed` | MEDIUM | Slack or email delivery failure was recorded. |

Each alert includes a summary, description, recommendation, and runbook URL placeholder.

## Notification Routing

| Destination | Receives | Reason |
| --- | --- | --- |
| Dashboard | All severities | Full operational history. |
| Slack | All severities | Real-time DevOps visibility. |
| Email | CRITICAL and HIGH only | Avoid noisy inboxes while preserving urgent escalation. |

Slack and email messages include project name, repository, scan ID, severity, deployment status, security score, short summary, timestamp, and report links where available.

## Required Notification Settings

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_CHANNEL_NAME=#securegate-alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@example.com
PUBLIC_BACKEND_URL=http://localhost:8000
```

## Daily, Weekly, And Monthly Summaries

The summary workflow is intentionally external. GitHub Actions cron triggers the summary endpoint; SecureGate AI does not run a background scheduler.

Example manifest: `examples/github-actions/securegate-summary.yml`

The summary payload includes:

- Number of projects scanned in the period.
- Total scans.
- Passed and failed deployments.
- Critical, high, medium, low, informational, and secret counts.
- Project-by-project vulnerability counts.
- Quality gate and pipeline success information.
- Simple language summary for DevOps teams.

## Manual Validation

```bash
docker compose config --quiet
python3 -m compileall -q backend/app
docker compose up -d --build backend prometheus alertmanager
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/metrics | grep securegate_high_vulnerability_threshold
```

Check Prometheus rules:

```bash
curl -fsS http://localhost:9090/api/v1/rules
```

Send a safe Alertmanager webhook test to SecureGate AI:

```bash
curl -fsS -X POST http://localhost:8000/api/v1/alerts/webhook-placeholder \
  -H "Content-Type: application/json" \
  -d '{
    "status":"firing",
    "alerts":[{
      "status":"firing",
      "labels":{"alertname":"NotificationDeliveryFailed","severity":"MEDIUM","category":"notification"},
      "annotations":{"summary":"Test notification alert","description":"Manual Alertmanager webhook validation.","recommendation":"No action needed for this test."},
      "startsAt":"2026-07-05T00:00:00Z"
    }]
  }'
```

## Troubleshooting

- If Alertmanager is not visible, open http://localhost:9093 and verify the container is running.
- If alerts do not appear, check Prometheus rule status at http://localhost:9090/rules.
- If Slack is missing alerts, verify `SLACK_WEBHOOK_URL` and backend logs.
- If email is missing critical/high alerts, verify SMTP settings and app password configuration.
- If thresholds look wrong, update `.env` and restart `backend`, `prometheus`, and `alertmanager`.

## Current Scope

Implemented in Sprint 5:

- Alertmanager service and routing.
- Prometheus alert rules for SecureGate AI security events.
- Configurable thresholds through backend settings and `.env`.
- Dashboard alert storage.
- Slack and email routing policy.
- Daily, weekly, and monthly summary notification workflow.

Out of scope until Sprint 6:

- AI-generated recommendations.
- LLM-based root cause analysis.
- Advanced manager report rewriting.
