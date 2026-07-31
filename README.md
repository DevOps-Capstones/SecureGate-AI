# SecureGate AI

SecureGate AI is an enterprise DevSecOps security decision platform for CI/CD pipelines. It receives security scan reports from GitHub Actions or Jenkins, normalizes findings, calculates deployment decisions, generates manager-friendly reports, sends notifications, visualizes security posture, and provides local AI-assisted remediation guidance.

The project is complete through Sprint 6.

## Official Documentation

The formal project documentation is available at [SecureGate AI Official Documentation](docs/securegate-ai-official-documentation.md). It includes business context, architecture, deployment, configuration, validation, monitoring, alerts, AI remediation, and references.

## Unique Selling Proposition

SecureGate AI gives DevOps teams one place to answer a simple production question:

**Is this repository safe enough to build, ship, and deploy?**

Instead of checking GitLeaks, Semgrep, Trivy, SonarQube, unit-test logs, Docker image scans, Slack messages, PDF reports, and Grafana panels separately, SecureGate AI combines them into one security cockpit.

What makes it useful:

- It works with existing CI/CD runners instead of replacing them.
- It supports GitHub Actions and Jenkins pipeline manifests.
- It enforces a strict security gate on every branch.
- It tracks one project per repository, with generated project IDs.
- It stores scan history, tool reports, findings, reports, audit logs, alerts, and notifications.
- It generates PDF, DOCX, JSON, AI summary, and AI remediation reports.
- It shows executive dashboards, project views, scan timelines, alerts, analytics, monitoring, and Grafana visualizations.
- It uses local Ollama/Gemma for AI assistance, with deterministic fallback when the model is unavailable.

## How SecureGate AI Works

```text
Developer pushes code to any branch
        |
GitHub Actions or Jenkins starts
        |
GitLeaks secret scan
        |
Semgrep static analysis
        |
Trivy filesystem scan
        |
SonarQube / SonarCloud quality gate
        |
Unit tests when available
        |
Docker build when policy allows
        |
Trivy image scan
        |
Optional Docker Hub push when approved and credentials exist
        |
SecureGate AI receives all reports through APIs
        |
SecureGate AI normalizes findings, scores the scan, decides APPROVED or REJECTED
        |
Dashboard, reports, notifications, Grafana metrics, AI summary, remediation plan
```

<img width="1408" height="768" alt="image" src="https://github.com/user-attachments/assets/73c61f8b-1422-4707-9822-c1ae6cadf242" />

<br>
<br>

SecureGate AI does **not** clone repositories or run scanners itself. The CI/CD runner performs scanning and uploads results to SecureGate AI.

## Technology Stack

- Frontend: React, Vite, TypeScript
- Backend: FastAPI, Python
- Database: PostgreSQL
- Containers: Docker Compose
- Security tools: GitLeaks, Semgrep, Trivy FS, Trivy Image, SonarQube/SonarCloud, unit-test ingestion
- Reports: PDF, DOCX, JSON, raw tool JSON, readable tool PDF
- Notifications: Slack webhook, SMTP email
- Monitoring: Prometheus, Alertmanager, Grafana
- AI: Ollama with Gemma 3 4B, rule-based fallback

## Service URLs

After startup:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Swagger API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- SonarQube: http://localhost:9000
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Grafana: http://localhost:3000
- Ollama: http://localhost:11434

## Quick Start

```bash
cd /Users/saimausman/Desktop/securegate-ai
docker compose up -d --build
```

Check services:

```bash
docker compose ps
curl -fsS http://localhost:8000/health
```

Pull the local AI model once:

```bash
docker compose exec ollama ollama pull gemma3:4b
```

Rebuild after code changes:

```bash
docker compose up -d --build frontend backend
```

Restart only the backend:

```bash
docker compose restart backend
```

View logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f ollama
```

Optional fresh database reset for demo data cleanup:

```bash
docker compose down -v
docker compose up -d --build
docker compose exec ollama ollama pull gemma3:4b
```

The reset command removes PostgreSQL, Prometheus, Grafana, SonarQube, and Ollama volumes. Use it only when you intentionally want a fresh environment.

## Environment Variables

Create the environment file at:

```text
/Users/saimausman/Desktop/securegate-ai/.env
```

Example:

```bash
SECUREGATE_API_KEY=replace-with-a-long-random-token
PUBLIC_BACKEND_URL=http://localhost:8000

# GitHub workflow trigger from SecureGate AI project page
GITHUB_TRIGGER_TOKEN=github_pat_or_fine_grained_token
GITHUB_WORKFLOW_FILE=securegate.yml

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@example.com

# Security gate policy
SECURITY_SCORE_THRESHOLD=80
CRITICAL_VULNERABILITY_THRESHOLD=0
HIGH_VULNERABILITY_THRESHOLD=5
BLOCK_HIGH_VULNERABILITIES=true
QUALITY_GATE_REQUIRED=true
SECRET_DETECTION_REQUIRED=true

# Monitoring and AI
PROMETHEUS_ENABLED=true
ENABLE_MONITORING=true
ENABLE_ANALYTICS=true
AI_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_TIMEOUT_SECONDS=300
```

For ngrok/local public testing, set:

```bash
PUBLIC_BACKEND_URL=https://your-ngrok-url.ngrok-free.dev
```

Then update GitHub repository secrets with the same public backend URL and API key.

## CI/CD Integration

SecureGate AI provides ready manifests in the frontend under **Manifests** and in the repo under:

- `examples/github-actions/securegate.yml`
- `examples/github-actions/securegate-summary.yml`
- `examples/jenkins/Jenkinsfile.securegate`

The normal scan workflow runs on branch pushes and manual dispatch. It supports all branches by policy.

The scheduled summary workflow runs automatically from GitHub Actions cron and can also be started manually through `workflow_dispatch`.

Required GitHub repository secrets:

```text
SECUREGATE_URL
SECUREGATE_API_KEY
SONAR_TOKEN
SONAR_HOST_URL
SONAR_PROJECT_KEY
SONAR_ORGANIZATION
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

Docker Hub credentials are optional. If they are missing, SecureGate AI still scans, reports, and decides. If they exist and the gate allows it, the pipeline can build/push images and rescan the final image.

## Core API Endpoints

Scan lifecycle:

- `POST /api/v1/pipeline/start`
- `POST /api/v1/pipeline/complete`
- `POST /api/v1/scans`
- `GET /api/v1/scans`
- `GET /api/v1/scans/{scan_id}`
- `GET /api/v1/scans/{scan_id}/audit`

Tool report uploads:

- `POST /api/v1/scans/{scan_id}/gitleaks`
- `POST /api/v1/scans/{scan_id}/semgrep`
- `POST /api/v1/scans/{scan_id}/trivy-fs`
- `POST /api/v1/scans/{scan_id}/trivy-image`
- `POST /api/v1/scans/{scan_id}/sonarqube`
- `POST /api/v1/scans/{scan_id}/unit-tests`

Project registry:

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_key}`
- `GET /api/v1/projects/{project_key}/findings`
- `POST /api/v1/projects/{project_key}/trigger-scan`
- `DELETE /api/v1/projects/{project_key}`

Reports:

- `GET /api/v1/reports/{scan_id}/pdf`
- `GET /api/v1/reports/{scan_id}/docx`
- `GET /api/v1/reports/{scan_id}/json`
- `GET /api/v1/scans/{scan_id}/reports/{tool_name}`
- `GET /api/v1/scans/{scan_id}/reports/{tool_name}/pdf`

AI:

- `GET /api/v1/ai/scans/{scan_id}/insights`
- `POST /api/v1/ai/scans/{scan_id}/chat`
- `GET /api/v1/ai/scans/{scan_id}/remediation-plan`
- `GET /api/v1/ai/scans/{scan_id}/summary-report/pdf`
- `GET /api/v1/ai/scans/{scan_id}/remediation-plan/pdf`

Monitoring:

- `GET /metrics`
- `GET /api/v1/monitoring/overview`
- `GET /api/v1/monitoring/analytics`
- `GET /api/v1/alerts`

## Security Gate Rules

Deployment is rejected when any blocking rule is true:

- Secrets are found by GitLeaks.
- Critical vulnerabilities are found.
- High vulnerabilities exceed the configured threshold.
- SonarQube/SonarCloud quality gate fails when required.
- Security score is below the configured threshold.
- Required pipeline stages fail.

Default scoring:

- Maximum score: 100
- Critical vulnerability: major deduction
- High vulnerability: strong deduction
- Medium vulnerability: moderate deduction
- Low vulnerability: light deduction
- Secrets: production blocker
- Failed quality gate: production blocker
- Passing score: 80 by default

The dashboard highlights any non-zero issue, vulnerability, severity, or finding count in red so users immediately notice risk.

## P1-P7 Remediation Priority Logic

SecureGate AI assigns remediation priority so developers know what to fix first.

| Priority | Meaning | Typical Examples |
| --- | --- | --- |
| P1 | Emergency production blocker | Exposed production secret, active credential leak |
| P2 | Critical security blocker | Critical CVE, severe exploitable dependency |
| P3 | Quality gate or policy blocker | Failed SonarQube quality gate, serious code quality failure |
| P4 | Critical vulnerability remediation | Critical container or filesystem CVE |
| P5 | High vulnerability remediation | High CVEs or high-risk static analysis findings |
| P6 | Important code/security hygiene | Code smells, maintainability risks, repeated scanner warnings |
| P7 | Lower urgency but still required | Medium findings, technical debt, next-cycle remediation |

`P7` does not mean ignore the issue. It means the issue is lower urgency than P1-P6 and should be handled in the next remediation cycle or before release depending on policy.

## Dashboard Pages

- Dashboard: executive KPIs, security summary, pipeline status, trends, latest uploads, reports, AI summary.
- Projects: register one project per repository, trigger scans, view project health.
- Project Details: overview, security summary, decision health, severity charts, pipeline timeline, findings, reports, AI remediation.
- Scan Details: lifecycle timeline, uploaded reports, severity pie, normalized findings, notifications, audit history.
- Reports: master report downloads and deletion.
- Remediation Plan: choose any scanned project and view AI remediation actions.
- Monitoring: platform/service health and dependency flow.
- Alerts: severity-aware alert tracking and escalation state.
- Analytics: security analytics and historical trends.
- User Guide: setup and usage guide.
- Settings: integration variables and tool configuration guidance.
- Manifests: GitHub Actions, Jenkins, GitLab/generic CI/CD examples.

## Reports Generated

SecureGate AI stores and serves:

- Master Security Report PDF
- Master Security Report DOCX
- Master Security Report JSON
- Readable PDF for each tool report
- Raw JSON for each uploaded tool report
- AI Security Summary PDF
- AI Remediation Plan PDF

Reports include project, repository, branch, upload time, score, decision, severity summary, tool status, top findings, simplified summary, and recommendations.

## Notifications

SecureGate AI sends Slack and email notifications for:

- Scan passed
- Scan failed
- Severity-aware alerts
- Daily/weekly/monthly summaries through GitHub Actions cron

Summary notifications include:

- Number of projects scanned
- Passed scans
- Failed scans
- Critical, high, medium, low, pending, and resolved counts
- Project-level severity breakdown
- Plain-language action summary

## Monitoring And Grafana

Prometheus scrapes SecureGate AI metrics from `/metrics`.

Grafana is available at:

```text
http://localhost:3000
```

The provisioned Grafana folder contains:

- `SecureGate AI - Executive Security Dashboard`

Current panels cover scan counts, findings, decisions, reports, notification health, alerts, CI/CD status, and service readiness.

Future Grafana dashboard improvements:

- Project Security Trends
- Tool-Level Findings
- CI/CD Health
- Notification Delivery Health
- Docker Image Risk
- Project-level drilldowns
- Branch-level drilldowns
- Image risk drilldowns

## AI Assistant And Remediation

Sprint 6 adds local AI support using Ollama and Gemma.

AI features:

- Ask AI Assistant floating widget
- AI Summary section on dashboard/project pages
- AI Security Summary PDF
- AI Remediation Plan PDF
- Project-level remediation page
- P1-P7 fix priorities
- Estimated fix time
- Production readiness checklist
- Rule-based fallback if Ollama is unavailable

Pull model:

```bash
docker compose exec ollama ollama pull gemma3:4b
```

Check model:

```bash
docker compose exec ollama ollama list
```

If Ollama is unavailable, SecureGate AI still works and uses deterministic stored-scan guidance.

## Database

SecureGate AI uses PostgreSQL.

Database service:

```text
postgresql://securegate:securegate_password@postgres:5432/securegate
```

Migrations are mounted through Docker Compose and run automatically on a fresh PostgreSQL volume from:

```text
database/migrations/
```

For an existing database, apply migrations manually in order:

```bash
for file in database/migrations/*.sql; do
  docker compose exec -T postgres psql -U securegate -d securegate < "$file"
done
docker compose restart backend
```

Important tables include:

- projects
- scans
- tool_reports
- findings
- reports
- audit_logs
- notifications
- alerts

## Validation Commands

Backend syntax check:

```bash
python3 -m compileall -q backend/app
```

Frontend build:

```bash
cd frontend
npm run build
```

Docker Compose validation:

```bash
docker compose config --quiet
```

Health check:

```bash
curl -fsS http://localhost:8000/health
```

Prometheus metrics:

```bash
curl -fsS http://localhost:8000/metrics
```

## Sprint Completion Summary

- Sprint 1: foundation, Docker Compose, React, FastAPI, PostgreSQL, SonarQube, Prometheus, Grafana, GitLeaks and Trivy validation.
- Sprint 2: report ingestion platform, scan metadata, tool uploads, normalization, scan history, dashboard integration.
- Sprint 3: scoring engine, deployment approval engine, recommendations, master report, PDF/DOCX/JSON exports.
- Sprint 4: project registry, GitHub/Jenkins automation, Slack/email notifications, pipeline lifecycle, dashboard UX, reports and scan details.
- Sprint 5: monitoring, alerts, Prometheus metrics, Grafana dashboard, trends, summary notification jobs, branch policy, Docker image tracking.
- Sprint 6: local AI assistant, AI summary, AI remediation plan, remediation PDF, chat assistant, P1-P7 priority logic, polished project completion docs.

## Production Notes

Before production use:

- Replace `SECUREGATE_API_KEY=change-me`.
- Use HTTPS for `PUBLIC_BACKEND_URL`.
- Store all tokens in CI/CD secrets.
- Restrict GitHub token permissions to required repositories.
- Configure SMTP and Slack carefully.
- Use persistent backups for PostgreSQL and report storage.
- Review Docker Hub push policy before enabling automatic image publishing.
- Pin third-party GitHub Actions to commit SHAs when your security policy requires strict supply-chain controls.

## License And Ownership

SecureGate AI is a capstone DevSecOps project demonstrating secure CI/CD report ingestion, decisioning, visualization, notification, and AI-assisted remediation.

## Author

**Saima Usman** \
Jr. DevOps + Cloud Engineer \
HeroVired (PPMCAD-15)

**Capstone Project** \
Container Image Vulnerability Scanner with Reporting

**Project Name:** \
SecureGate AI
