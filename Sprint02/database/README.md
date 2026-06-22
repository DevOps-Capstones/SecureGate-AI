# Database

PostgreSQL stores projects, scan history, raw tool reports, normalized findings, and audit events.

- `001_initial_schema.sql`: complete schema for fresh installations
- `002_sprint_2_report_ingestion.sql`: idempotent Sprint 1 upgrade

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/002_sprint_2_report_ingestion.sql
docker compose restart backend
```

Fresh volumes run migrations automatically. Defaults: `localhost:5432`, database/user `securegate`, password `securegate_password`.
