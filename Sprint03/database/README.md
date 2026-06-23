# Database

PostgreSQL stores projects, scan history, raw tool reports, normalized findings, and audit events.

- `001_initial_schema.sql`: complete schema for fresh installations
- `002_sprint_2_report_ingestion.sql`: idempotent Sprint 1 upgrade
- `003_sprint_3_security_decision_engine.sql`: score, decision, quality-gate, and report payload fields

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/002_sprint_2_report_ingestion.sql
docker compose restart backend
```

Apply Sprint 3 to an existing database:

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/003_sprint_3_security_decision_engine.sql
docker compose restart backend
```

Fresh volumes run migrations automatically. Defaults: `localhost:5432`, database/user `securegate`, password `securegate_password`.
