import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  CheckCircle2,
  Clock3,
  Database,
  ExternalLink,
  FileText,
  Gauge,
  GitBranch,
  Mail,
  MessageSquare,
  Network,
  RadioTower,
  Server,
  ShieldCheck,
  Workflow,
  XCircle,
  type LucideIcon
} from "lucide-react";
import { Link } from "react-router-dom";
import { getHealth, getMonitoringOverview } from "../api/scans";
import type { MonitoringOverview } from "../types/scans";

type HealthStatus = Record<string, string | number>;

const healthChecks: Array<{ label: string; path: string; owner: string; detail: string; icon: LucideIcon }> = [
  { label: "Backend API", path: "/health", owner: "FastAPI", detail: "Receives reports and serves dashboards", icon: Server },
  { label: "PostgreSQL", path: "/health/database", owner: "Database", detail: "Stores scans, reports, findings, and audits", icon: Database },
  { label: "Prometheus", path: "/health/prometheus", owner: "Metrics", detail: "Scrapes SecureGate AI operational metrics", icon: Activity },
  { label: "Grafana", path: "/health/grafana", owner: "Visualization", detail: "Displays provisioned monitoring dashboards", icon: BarChart3 },
  { label: "Sonar", path: "/health/sonarqube", owner: "Quality Gate", detail: "Tracks code quality integration readiness", icon: ShieldCheck }
];

const dependencyFlow: Array<{ label: string; detail: string; healthKey?: string; icon: LucideIcon }> = [
  { label: "CI Runner", detail: "GitHub Actions or Jenkins sends reports", icon: GitBranch },
  { label: "SecureGate API", detail: "Validates and ingests pipeline payloads", healthKey: "Backend API", icon: Server },
  { label: "PostgreSQL", detail: "Persists normalized security state", healthKey: "PostgreSQL", icon: Database },
  { label: "Prometheus", detail: "Collects platform metrics", healthKey: "Prometheus", icon: Activity },
  { label: "Grafana", detail: "Visualizes operations health", healthKey: "Grafana", icon: BarChart3 },
  { label: "Notifications", detail: "Sends Slack and email outcomes", icon: Bell }
];

const quickLinks = [
  { label: "Metrics Endpoint", href: "http://localhost:8000/metrics", icon: RadioTower },
  { label: "Prometheus", href: "http://localhost:9090", icon: Activity },
  { label: "Grafana Dashboard", href: "http://localhost:3000/d/securegate-ai-executive-security", icon: BarChart3 },
  { label: "Alert Rules", href: "http://localhost:3000/alerting/list", icon: Bell }
];

function statusClass(status: string | number | undefined): "healthy" | "warning" | "critical" {
  const normalized = String(status ?? "checking").toLowerCase();
  if (["healthy", "ok", "success", "completed", "available", "ready"].includes(normalized)) return "healthy";
  if (["critical", "error", "failed", "down", "unhealthy", "offline"].includes(normalized)) return "critical";
  return "warning";
}

function statusLabel(status: string | number | undefined): string {
  const value = String(status ?? "checking");
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function numberFrom(record: Record<string, string | number> | undefined, key: string): number {
  const value = record?.[key];
  if (typeof value === "number") return value;
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function titleCase(value: string): string {
  return value.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function Monitoring() {
  const [overview, setOverview] = useState<MonitoringOverview | null>(null);
  const [health, setHealth] = useState<Record<string, HealthStatus>>({});

  useEffect(() => {
    getMonitoringOverview().then(setOverview).catch(console.error);
    healthChecks.forEach(({ label, path }) => {
      getHealth(path)
        .then((value) => setHealth((prev) => ({ ...prev, [label]: value })))
        .catch(() => setHealth((prev) => ({ ...prev, [label]: { status: "critical" } })));
    });
  }, []);

  const telemetry = useMemo(() => [
    { label: "Running Scans", value: overview?.running_scans ?? 0, helper: "Currently active pipeline checks", icon: Workflow, tone: "info" },
    { label: "Completed Scans", value: overview?.completed_scans ?? 0, helper: "Finished scans tracked by SecureGate AI", icon: CheckCircle2, tone: "good" },
    { label: "Failed Scans", value: overview?.failed_scans ?? 0, helper: "Pipelines that reported failure", icon: XCircle, tone: "critical" },
    { label: "Reports Generated", value: overview?.reports_generated ?? 0, helper: "Master and tool reports available", icon: FileText, tone: "info" },
    { label: "Open Alerts", value: overview?.alerts.open_alerts ?? 0, helper: "Active alert records needing review", icon: Bell, tone: (overview?.alerts.open_alerts ?? 0) > 0 ? "warning" : "good" },
    { label: "Average Scan Time", value: `${overview?.average_scan_time ?? 0}s`, helper: "Mean processing duration", icon: Clock3, tone: "info" }
  ], [overview]);

  const notificationSuccess = numberFrom(overview?.notifications, "notification_success_rate");
  const notificationStatus = notificationSuccess >= 95 ? "healthy" : notificationSuccess >= 80 ? "warning" : "critical";
  const slackSent = numberFrom(overview?.notifications, "slack_delivery_count");
  const slackFailed = numberFrom(overview?.notifications, "slack_failures");
  const emailSent = numberFrom(overview?.notifications, "email_delivery_count");
  const emailFailed = numberFrom(overview?.notifications, "email_failures");

  return (
    <section className="page monitoring-page">
      <header className="page-header monitoring-hero">
        <div>
          <p className="eyebrow">Operations Center</p>
          <h1>SecureGate AI Monitoring Center</h1>
          <p>Live platform health, scan operations, alert state, and notification delivery.</p>
        </div>
        <span className={`monitoring-live-pill ${Object.values(health).some((item) => statusClass(item.status) === "critical") ? "critical" : "healthy"}`}>
          <RadioTower size={16} /> Live Checks
        </span>
      </header>

      <section className="monitoring-service-grid" aria-label="Platform health overview">
        {healthChecks.map(({ label, owner, detail, icon: Icon }) => {
          const current = health[label];
          const tone = statusClass(current?.status);
          return (
            <article className={`monitoring-service-card ${tone}`} key={label}>
              <div className="monitoring-card-head">
                <span className="monitoring-icon"><Icon size={20} /></span>
                <span className={`monitoring-status-dot ${tone}`} />
              </div>
              <strong>{label}</strong>
              <small>{owner}</small>
              <p>{detail}</p>
              <span className={`monitoring-status-label ${tone}`}>{statusLabel(current?.status)}</span>
            </article>
          );
        })}
      </section>

      <section className="monitoring-telemetry-grid" aria-label="Live operations telemetry">
        {telemetry.map(({ label, value, helper, icon: Icon, tone }) => (
          <article className={`monitoring-metric-card ${tone}`} key={label}>
            <span className="monitoring-icon"><Icon size={19} /></span>
            <div>
              <strong>{value}</strong>
              <span>{label}</span>
              <small>{helper}</small>
            </div>
          </article>
        ))}
      </section>

      <section className="section-band monitoring-flow-panel">
        <div className="scan-card-header">
          <span className="scan-card-icon"><Network size={23} /></span>
          <div>
            <h2>Service Dependency Flow</h2>
            <p>Operational path from CI runner to visibility and notifications.</p>
          </div>
          <Link className="scan-card-action" to="/manifests">View Manifests <ExternalLink size={15} /></Link>
        </div>
        <div className="monitoring-flow">
          {dependencyFlow.map(({ label, detail, healthKey, icon: Icon }, index) => {
            const tone = healthKey ? statusClass(health[healthKey]?.status) : label === "Notifications" ? notificationStatus : "healthy";
            return (
              <article className={`monitoring-flow-node ${tone}`} key={label}>
                <span className="monitoring-flow-step">{String(index + 1).padStart(2, "0")}</span>
                <Icon size={22} />
                <strong>{label}</strong>
                <small>{detail}</small>
              </article>
            );
          })}
        </div>
      </section>

      <div className="monitoring-split-grid">
        <section className="section-band monitoring-alert-panel">
          <div className="scan-card-header compact">
            <span className="scan-card-icon"><AlertTriangle size={22} /></span>
            <div>
              <h2>Alert Rules Summary</h2>
              <p>Current alert records created from scan and platform signals.</p>
            </div>
            <Link className="scan-card-action" to="/alerts">View Alerts <ExternalLink size={15} /></Link>
          </div>
          <div className="monitoring-alert-stats">
            <span><b>{overview?.alerts.total_alerts ?? 0}</b>Total</span>
            <span><b>{overview?.alerts.open_alerts ?? 0}</b>Open</span>
            <span><b>{overview?.alerts.escalated_alerts ?? 0}</b>Escalated</span>
            <span><b>{overview?.alerts.resolved_alerts ?? 0}</b>Resolved</span>
          </div>
          <div className="monitoring-rule-list">
            {Object.entries(overview?.alerts.by_type ?? {}).length ? Object.entries(overview?.alerts.by_type ?? {}).map(([type, count]) => (
              <div className="monitoring-rule-row" key={type}>
                <span><AlertTriangle size={15} /> {titleCase(type)}</span>
                <strong>{count}</strong>
              </div>
            )) : <p className="muted">No alert rules are currently firing.</p>}
          </div>
        </section>

        <section className="section-band monitoring-notification-panel">
          <div className="scan-card-header compact">
            <span className="scan-card-icon"><Bell size={22} /></span>
            <div>
              <h2>Notification Delivery</h2>
              <p>Delivery health for operational Slack and email messages.</p>
            </div>
            <span className={`monitoring-status-label ${notificationStatus}`}>{notificationSuccess}% Success</span>
          </div>
          <div className="monitoring-channel-grid">
            <article>
              <MessageSquare size={22} />
              <strong>Slack</strong>
              <span>{slackSent} Sent</span>
              <small>{slackFailed} Failed</small>
            </article>
            <article>
              <Mail size={22} />
              <strong>Email</strong>
              <span>{emailSent} Sent</span>
              <small>{emailFailed} Failed</small>
            </article>
          </div>
          <div className="monitoring-delivery-bar" title={`${notificationSuccess}% notification success rate`}>
            <span style={{ width: `${Math.min(100, Math.max(0, notificationSuccess))}%` }} />
          </div>
        </section>
      </div>

      <div className="monitoring-split-grid">
        <section className="section-band monitoring-events-panel">
          <div className="scan-card-header compact">
            <span className="scan-card-icon"><Activity size={22} /></span>
            <div>
              <h2>Operational Signals</h2>
              <p>Compact view of monitoring signals that may require action.</p>
            </div>
          </div>
          <div className="monitoring-signal-list">
            <div><strong>Risk Concentration</strong><span>{overview?.top_risk_projects.length ? `${overview.top_risk_projects.length} project(s) currently driving risk` : "No high-risk project signal"}</span></div>
            <div><strong>Critical Findings</strong><span>{overview?.critical_findings ?? 0} open critical finding signal(s)</span></div>
            <div><strong>High Findings</strong><span>{overview?.high_findings ?? 0} high finding signal(s)</span></div>
            <div><strong>Notification Volume</strong><span>{numberFrom(overview?.notifications, "notification_volume")} delivery event(s)</span></div>
          </div>
        </section>

        <section className="section-band monitoring-links-panel">
          <div className="scan-card-header compact">
            <span className="scan-card-icon"><ExternalLink size={22} /></span>
            <div>
              <h2>Monitoring Shortcuts</h2>
              <p>Jump directly into the operational systems behind this page.</p>
            </div>
          </div>
          <div className="monitoring-link-grid">
            {quickLinks.map(({ label, href, icon: Icon }) => (
              <a href={href} key={label} rel="noreferrer" target="_blank">
                <Icon size={18} />
                <span>{label}</span>
                <ExternalLink size={14} />
              </a>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
