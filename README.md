## Sprint 3

Sprint 3 calculates a 0-100 security score, records `APPROVED` or `REJECTED` deployment decisions, generates prioritized rule-based recommendations, and stores a canonical master report. Reports are available as PDF, DOCX, and JSON, with 12-month history filters in the dashboard.

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/003_sprint_3_security_decision_engine.sql
docker compose restart backend
```

Export endpoints are documented at `http://localhost:8000/docs` under `reports`.

---

## Future Implementations

Scanner execution, CI workflow files, Jenkins, notifications, LLM recommendations, and monitoring dashboards.

---
