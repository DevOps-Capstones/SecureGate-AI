# Sprint 5 Monitoring And Grafana Visualization

Sprint 5 adds production-style monitoring and visualization for SecureGate AI. The backend exposes Prometheus metrics through `/metrics`, Prometheus scrapes those metrics, and Grafana visualizes the platform security posture. The React dashboard also includes executive KPIs, security summaries, scan score trends, vulnerability trends, pipeline status, latest uploads, reports, and notification health.

Grafana is available at `http://localhost:3000`. The SecureGate AI Grafana folder now contains one clean dashboard:

- `SecureGate AI - Executive Security Dashboard`

The previous extra Grafana dashboard pages were removed so the folder stays focused and easy to use. The remaining dashboard includes executive security, scan, vulnerability, CI/CD, notification, report, and platform health panels backed by Prometheus.

Current Grafana setup includes:

- Prometheus datasource: `Prometheus` -> `http://prometheus:9090`
- Provisioned dashboard JSON under `monitoring/grafana/dashboards/`
- Provisioned dashboard folder under `monitoring/grafana/provisioning/dashboards/`
- Starter alert rules under `monitoring/grafana/provisioning/alerting/`
- Datasource cleanup for stale `prometheus-1` entries

Grafana folder tabs:

- `Dashboards`: contains the main SecureGate AI executive dashboard.
- `Panels`: reserved for future reusable library panels.
- `Alert rules`: contains starter rules for critical vulnerabilities, secrets, low security score, rejected deployments, failed scans, backend availability, and frontend availability.

Grafana's own email alert delivery requires SMTP configuration in Grafana. This is separate from SecureGate AI's application-level Slack and email notifications.

See `docs/sprint-5-monitoring.md` for detailed Sprint 5 monitoring notes.

## Future Improvements

Planned improvements for later sprints include:

- AI-assisted executive summaries and remediation guidance
- More advanced master reports for managers and DevOps engineers
- Grafana dashboard: Project Security Trends
- Grafana dashboard: Tool-Level Findings
- Grafana dashboard: CI/CD Health
- Grafana dashboard: Notification Delivery Health
- Grafana dashboard: Docker Image Risk
- Grafana contact points for Slack and email alert delivery
- More granular drill-down dashboards per project, branch, image, and tool
- Production deployment hardening and backup/restore documentation

---

## SecureGate AI Updated Dasboard


<img width="1280" height="800" alt="Screenshot 2026-07-04 at 1 08 15 AM" src="https://github.com/user-attachments/assets/77937f34-0605-482e-b4f4-8740dc408ee3" />


<img width="1864" height="316" alt="image" src="https://github.com/user-attachments/assets/ee1d8072-9793-43cf-9369-46eb60f0493c" />

<img width="2522" height="1508" alt="image" src="https://github.com/user-attachments/assets/20c40b3d-f4e8-4315-be4c-49e9c9ac9a3e" />

<img width="2106" height="1090" alt="image" src="https://github.com/user-attachments/assets/a17058f8-a9a7-4fcd-ba99-bd83a351eb6a" />

<img width="1066" height="529" alt="Screenshot 2026-07-04 at 1 11 30 AM" src="https://github.com/user-attachments/assets/20567f2c-0e45-4726-a223-4f8155aac3fc" />

---

## Graffana Dashboard

<img width="2530" height="1518" alt="image" src="https://github.com/user-attachments/assets/7dbeb542-8d54-46b9-824e-84beef00d1c4" />

---

## Current Sprint 5 monitoring and Grafana visualization summary

- Prometheus /metrics flow
- One clean Grafana dashboard setup
- Grafana folder tabs explanation: Dashboards, Panels, Alert rules
- Current datasource and provisioning details
- Note about Grafana SMTP being separate from SecureGate AI notifications
- Future Grafana dashboard improvements:Project Security Trends
- Tool-Level Findings
- CI/CD Health
- Notification Delivery Health
- Docker Image Risk

---

NOTE: SPrint-06 will focus on the addition of **AI agent** for Report & Summary generation and Remediation.

---







