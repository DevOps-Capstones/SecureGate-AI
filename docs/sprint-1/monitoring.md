# Monitoring Setup

## Prometheus

Access Prometheus at:

```text
http://localhost:9090
```

Use `Status > Targets` to inspect configured scrape targets.

Sprint 1 includes:

- Prometheus self-scrape
- Placeholder backend scrape target at `backend:8000/metrics`

The backend does not expose metrics yet, so backend scraping may show as unavailable until metrics are added in a future sprint.

## Grafana

Access Grafana at:

```text
http://localhost:3000
```

Default credentials:

- Username: `admin`
- Password: `admin`

Grafana is provisioned with a Prometheus datasource named `Prometheus`.

## Future Usage Plans

Later sprints can add:

- Vulnerability counts by severity
- Open vulnerabilities over time
- Resolved vulnerabilities over time
- Pending fixes by project
- Scanner execution duration
- CI/CD pass and fail trends

No Grafana dashboards are required in Sprint 1.
