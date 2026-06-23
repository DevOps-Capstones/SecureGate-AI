## Securegate AI Sprint 3

Sprint 3 calculates a 0-100 security score, records `APPROVED` or `REJECTED` deployment decisions, generates prioritized rule-based recommendations, and stores a canonical master report. Reports are available as PDF, DOCX, and JSON, with 12-month history filters in the dashboard.

```bash
docker compose exec -T postgres psql -U securegate -d securegate < database/migrations/003_sprint_3_security_decision_engine.sql
docker compose restart backend
```

Export endpoints are documented at `http://localhost:8000/docs` under `reports`.

<img width="1280" height="404" alt="Screenshot 2026-06-23 at 11 28 21 AM" src="https://github.com/user-attachments/assets/00cda0c6-6efd-4f71-ad8d-5cfc06362dcc" />


<img width="1280" height="800" alt="Screenshot 2026-06-23 at 11 29 54 AM" src="https://github.com/user-attachments/assets/db6b67fb-175b-4a2b-aa7b-cd9d0c769acc" />


<img width="1252" height="570" alt="Screenshot 2026-06-23 at 11 30 57 AM" src="https://github.com/user-attachments/assets/02c3de2f-c8d6-4700-a86a-cd198f5a8db9" />


---

# Updated Dashboard

<img width="1280" height="800" alt="Screenshot 2026-06-23 at 11 26 36 AM" src="https://github.com/user-attachments/assets/e3282fb5-8c4a-48ca-b946-d84f19938863" />


<img width="1280" height="800" alt="Screenshot 2026-06-23 at 11 35 12 AM" src="https://github.com/user-attachments/assets/dd284fe8-b932-4755-8ea2-5d6b467f358c" />


<img width="1280" height="800" alt="Screenshot 2026-06-23 at 11 40 57 AM" src="https://github.com/user-attachments/assets/9a44ba0b-4292-4b27-a209-7d26b589f9de" />

----

**PDF Report Sample:**

<img width="1132" height="1538" alt="image" src="https://github.com/user-attachments/assets/937764ca-753a-4033-8300-08210ff43465" />


----

## Future Implementations

Scanner execution, CI workflow files, Jenkins, notifications, LLM recommendations, and monitoring dashboards.

---
