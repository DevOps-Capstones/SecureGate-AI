# Sprint 3: Security Decision Engine

Sprint 3 aggregates normalized Sprint 2 findings into a security score, deployment decision, prioritized recommendations, and one canonical master security report.

## Decision Rules

The score starts at 100. Trivy vulnerabilities deduct 15 points per critical finding, 8 per high finding, and 3 per medium finding. The score cannot fall below zero.

Deployment is `REJECTED` when secrets exist, critical vulnerabilities exist, the SonarQube quality gate fails, or the score is below 80. It is `APPROVED` only after all four required tool reports have arrived and every rule passes.

## Exports

- `GET /api/v1/reports/{scan_id}/pdf`
- `GET /api/v1/reports/{scan_id}/docx`
- `GET /api/v1/reports/{scan_id}/json`
- `GET /api/v1/reports` for the last 12 months of report history

History filters support `project`, `branch`, `date_from`, `date_to`, `decision`, and `severity`.

## Database Migration

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/003_sprint_3_security_decision_engine.sql
docker compose restart backend
```

## Testing

```bash
docker compose up -d --build
docker compose exec backend python -m unittest discover -s tests -v
docker compose config --quiet
cd frontend && npm run build
```

Upload GitLeaks, Trivy filesystem, Trivy image, and SonarQube JSON for one scan. Confirm the scan becomes `COMPLETED`, its score and decision are stored, a master report appears in history, and all three exports download successfully.

## Out of Scope

Slack, email, Ollama, LLM recommendations, Jenkins, Prometheus dashboards, and Grafana dashboards remain out of scope.
