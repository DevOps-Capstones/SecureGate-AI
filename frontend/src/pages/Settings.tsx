import { Bell, PlugZap, Settings2, ShieldCheck } from "lucide-react";

const integrationSettings = [
  {
    name: "Public SecureGate URL",
    value: "Use your public backend URL, for example https://your-ngrok-domain.ngrok-free.dev. Save it in CI as SECUREGATE_URL."
  },
  {
    name: "SecureGate API Key",
    value: "Save the generated key as SECUREGATE_API_KEY in GitHub Actions secrets or as the Jenkins credential securegate-api-key. Send it as Authorization: Bearer <key>."
  },
  {
    name: "Start Pipeline Scan",
    value: "POST $SECUREGATE_URL/api/v1/pipeline/start with project_name, repository_url, branch, commit_sha, and pipeline_run_id."
  },
  {
    name: "Upload Tool Reports",
    value: "POST JSON reports to /api/v1/scans/{scan_id}/gitleaks, /semgrep, /trivy-fs, /trivy-image, /sonarqube, and /unit-tests."
  },
  {
    name: "Complete Pipeline Scan",
    value: "POST $SECUREGATE_URL/api/v1/pipeline/complete with scan_id and status SUCCESS or FAILED."
  },
  {
    name: "Read Deployment Decision",
    value: "GET $SECUREGATE_URL/api/v1/scans/{scan_id}. The selected runner continues only when deployment_decision is APPROVED; no GitHub-to-Jenkins approval handoff is required."
  }
];

const toolSettings = [
  {
    name: "GitHub Actions",
    value: "Use GitHub Actions as one complete runner option. Add SECUREGATE_URL, SECUREGATE_API_KEY, SONAR_HOST_URL, SONAR_TOKEN, SONAR_PROJECT_KEY, SONAR_ORGANIZATION, and optional DOCKERHUB_USERNAME/DOCKERHUB_TOKEN as repository secrets. The workflow scans, runs SonarCloud before temporary Dockerfile generation, builds, uploads reports, updates the dashboard, prints the safe-to-deploy message on approval, pushes the approved image when Docker Hub secrets exist, and uploads a post-push image rescan."
  },
  {
    name: "Jenkins",
    value: "Use Jenkins as the alternative complete runner option. Create credentials named securegate-url and securegate-api-key, plus SonarCloud credentials. Jenkins runs the same scans, runs SonarCloud before temporary Dockerfile generation, builds/scans the Docker image, uploads reports, updates the dashboard, prints the safe-to-deploy message on approval, and can push/rescan the approved image when Docker Hub credentials are configured."
  },
  {
    name: "SonarCloud",
    value: "Use SONAR_HOST_URL=https://sonarcloud.io plus SONAR_TOKEN, SONAR_PROJECT_KEY, and SONAR_ORGANIZATION. Upload the quality gate JSON to SecureGate AI."
  },
  {
    name: "Trivy",
    value: "Generate filesystem and image JSON reports. If the repository has no Dockerfile, the selected runner creates SecureGate.Dockerfile only for image scanning, then uploads trivy-fs and trivy-image to SecureGate AI."
  },
  {
    name: "GitLeaks",
    value: "Generate gitleaks-report.json and upload it to the GitLeaks endpoint. Any detected secret blocks deployment."
  },
  {
    name: "Unit Tests",
    value: "Upload unit-tests-report.json to /api/v1/scans/{scan_id}/unit-tests. Failed tests block deployment; missing tests can be uploaded as SKIPPED so the dashboard stays complete."
  },
  {
    name: "Prometheus And Grafana",
    value: "Prometheus scrapes $SECUREGATE_URL/metrics. Grafana can use the Prometheus datasource for trends and platform monitoring."
  }
];

const notificationSettings = [
  {
    name: "Slack Alerts",
    value: "Set SLACK_WEBHOOK_URL in .env for delivery and SLACK_CHANNEL_NAME for safe dashboard display. SecureGate sends severity-aware alerts after reports are ingested and scored."
  },
  {
    name: "Email Alerts",
    value: "Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM in .env for email delivery."
  },
  {
    name: "Daily Summary",
    value: "Use GitHub Actions schedule to call POST /api/v1/notifications/summary/daily automatically. The message shows projects scanned in the last 24 hours, pass/fail totals, and vulnerabilities by project."
  },
  {
    name: "Weekly Summary",
    value: "Use GitHub Actions schedule to call POST /api/v1/notifications/summary/weekly automatically. The message shows projects scanned in the last 7 days, pass/fail totals, and vulnerabilities by project."
  },
  {
    name: "Monthly Summary",
    value: "Use GitHub Actions schedule to call POST /api/v1/notifications/summary/monthly automatically. The message shows projects scanned in the last 30 days, pass/fail totals, and vulnerabilities by project."
  }
];

function SettingsGroup({ title, items, icon: Icon }: { title: string; items: { name: string; value: string }[]; icon: typeof Settings2 }) {
  return (
    <div className="settings-list sprint4-settings section-band scan-modern-card settings-modern-card">
      <div className="scan-card-header">
        <span className="scan-card-icon"><Icon size={22} /></span>
        <div>
          <h2>{title}</h2>
          <p>Review the required configuration values for this SecureGate AI integration area.</p>
        </div>
        <span className="scan-card-count">{items.length} Items</span>
      </div>
      <div className="settings-table-grid settings-modern-table">
        <div className="settings-table-head">Setting</div>
        <div className="settings-table-head">Configuration</div>
        {items.map((setting) => (
          <div className="settings-table-row" key={setting.name}>
            <span>{setting.name}</span>
            <strong>{setting.value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SettingsPage() {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Platform Settings</p>
          <h1>Tool Integration Settings</h1>
        </div>
      </header>

      <SettingsGroup title="SecureGate AI Pipeline Contract" items={integrationSettings} icon={ShieldCheck} />
      <SettingsGroup title="CI/CD And Security Tools" items={toolSettings} icon={PlugZap} />
      <SettingsGroup title="Notifications And Summaries" items={notificationSettings} icon={Bell} />
    </section>
  );
}
