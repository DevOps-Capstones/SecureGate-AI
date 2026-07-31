import { useEffect, useMemo, useState } from "react";
import { AlertCircle, AlertTriangle, Bell, CheckCircle2, Clock3, Gauge, Mail, MessageSquare, RadioTower, Search, ShieldAlert, Siren, SlidersHorizontal } from "lucide-react";
import { Link } from "react-router-dom";
import { getAlertPolicy, getAlertStatistics, listAlerts, listProjects, updateAlertPolicy } from "../api/scans";
import type { AlertItem, AlertPolicy, AlertStatistics, ProjectSummary } from "../types/scans";

const severityOptions = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

const alertRules = [
  { label: "Critical Vulnerabilities", severity: "CRITICAL", text: "Critical vulnerabilities exceed the configured threshold." },
  { label: "High Vulnerability Threshold", severity: "HIGH", text: "High vulnerabilities exceed the configured threshold." },
  { label: "Secrets Detected", severity: "CRITICAL", text: "GitLeaks detected exposed secrets or credentials." },
  { label: "SonarQube Quality Gate", severity: "HIGH", text: "SonarQube or SonarCloud quality gate failed." },
  { label: "Deployment Blocked", severity: "CRITICAL", text: "SecureGate AI rejected a deployment decision." },
  { label: "Master Report Failure", severity: "MEDIUM", text: "Master report generation or finalization failed." },
  { label: "Notification Failure", severity: "MEDIUM", text: "Slack or email delivery failed." },
];

function titleCase(value: string) {
  return value
    .split("_")
    .join(" ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function severityTone(severity: string) {
  const normalized = severity.toUpperCase();
  if (normalized === "CRITICAL") return "critical";
  if (normalized === "HIGH" || normalized === "MEDIUM") return "warning";
  return "good";
}

function statusTone(status: string) {
  const normalized = status.toUpperCase();
  if (normalized === "OPEN") return "critical";
  if (normalized === "RESOLVED") return "good";
  return "warning";
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

function channelLabel(value: string) {
  return value.toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

export function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [statistics, setStatistics] = useState<AlertStatistics | null>(null);
  const [filters, setFilters] = useState({ search: "", severity: "", status: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectKey, setSelectedProjectKey] = useState("");
  const [policy, setPolicy] = useState<AlertPolicy | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [policyMessage, setPolicyMessage] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      listAlerts({ severity: filters.severity, status: filters.status }),
      getAlertStatistics(),
      listProjects(),
    ])
      .then(([alertRows, stats, projectRows]) => {
        setAlerts(alertRows);
        setStatistics(stats);
        setProjects(projectRows);
        setSelectedProjectKey((current) => current || projectRows[0]?.project_key || "");
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters.severity, filters.status]);

  useEffect(() => {
    if (!selectedProjectKey) {
      setPolicy(null);
      return;
    }
    setPolicyLoading(true);
    setPolicyMessage(null);
    getAlertPolicy(selectedProjectKey)
      .then(setPolicy)
      .catch((err: Error) => setPolicyMessage(err.message))
      .finally(() => setPolicyLoading(false));
  }, [selectedProjectKey]);

  async function handlePolicySave() {
    if (!selectedProjectKey || !policy) return;
    setPolicyLoading(true);
    setPolicyMessage(null);
    try {
      const saved = await updateAlertPolicy(selectedProjectKey, {
        enabled: policy.enabled,
        slack_enabled: policy.slack_enabled,
        email_enabled: policy.email_enabled,
        slack_min_severity: policy.slack_min_severity,
        email_min_severity: policy.email_min_severity,
      });
      setPolicy(saved);
      setPolicyMessage(saved.enabled ? "Custom alert policy saved for future scans." : "Custom policy disabled. Default routing policy is active.");
    } catch (err) {
      setPolicyMessage(err instanceof Error ? err.message : "Unable to save alert policy.");
    } finally {
      setPolicyLoading(false);
    }
  }

  const visible = useMemo(() => alerts.filter((alert) => {
    const haystack = `${alert.project_name} ${alert.repository ?? ""} ${alert.branch ?? ""} ${alert.alert_type} ${alert.description}`.toLowerCase();
    return haystack.includes(filters.search.toLowerCase());
  }), [alerts, filters.search]);

  const visibleOpen = visible.filter((alert) => alert.status === "OPEN").length;
  const visibleCritical = visible.filter((alert) => alert.severity === "CRITICAL").length;
  const visibleHigh = visible.filter((alert) => alert.severity === "HIGH").length;
  const visibleEscalated = visible.filter((alert) => alert.escalation_level > 0).length;
  const visibleResolved = visible.filter((alert) => alert.status === "RESOLVED").length;
  const latestAlert = visible[0] ?? null;
  const summaryCards = [
    { label: "Open Alerts", value: visibleOpen, helper: "Needs review", icon: Siren, tone: visibleOpen > 0 ? "critical" : "good" },
    { label: "Critical", value: visibleCritical, helper: "Email + Slack", icon: ShieldAlert, tone: visibleCritical > 0 ? "critical" : "good" },
    { label: "High", value: visibleHigh, helper: "Email + Slack", icon: AlertTriangle, tone: visibleHigh > 0 ? "warning" : "good" },
    { label: "Escalated", value: statistics?.escalated_alerts ?? visibleEscalated, helper: "Past SLA window", icon: Clock3, tone: (statistics?.escalated_alerts ?? visibleEscalated) > 0 ? "warning" : "good" },
    { label: "Resolved", value: visibleResolved, helper: "Closed alerts", icon: CheckCircle2, tone: "good" },
  ];

  return <section className="page alerts-page">
    <header className="page-header monitoring-hero alerts-hero">
      <div>
        <p className="eyebrow">Sprint 5 Alertmanager Integration</p>
        <h1>Alerts</h1>
        <p>Security-event alerts from Prometheus and Alertmanager with dashboard, Slack, and email routing.</p>
      </div>
      <span className={`monitoring-live-pill ${visibleOpen > 0 ? "critical" : "healthy"}`}><RadioTower size={16} /> {visibleOpen > 0 ? `${visibleOpen} Open` : "All Clear"}</span>
    </header>

    <div className="monitoring-telemetry-grid alerts-metric-grid">
      {summaryCards.map((card) => {
        const Icon = card.icon;
        return <article className={`monitoring-metric-card ${card.tone}`} key={card.label}>
          <span className="monitoring-icon"><Icon size={21} /></span>
          <div><strong>{card.value}</strong><span>{card.label}</span><small>{card.helper}</small></div>
        </article>;
      })}
    </div>

    <section className="section-band scan-modern-card alerts-routing-card">
      <div className="scan-card-header compact">
        <span className="scan-card-icon"><Bell size={22} /></span>
        <div>
          <h2>Alert Routing Policy</h2>
          <p>Dashboard stores every alert. Slack receives all severities. Email receives Critical and High only.</p>
        </div>
        <span className="scan-card-count">7 Rules</span>
      </div>
      <div className="alerts-route-grid">
        <article><span className="alert-route-icon"><Gauge size={18} /></span><strong>Dashboard</strong><small>All Severities</small></article>
        <article><span className="alert-route-icon"><MessageSquare size={18} /></span><strong>Slack</strong><small>Critical, High, Medium, Low, Info</small></article>
        <article><span className="alert-route-icon"><Mail size={18} /></span><strong>Email</strong><small>Critical And High Only</small></article>
      </div>
      <div className="alerts-rule-list">
        {alertRules.map((rule) => <div className="alerts-rule-row" key={rule.label}>
          <span className={`alerts-severity-dot ${severityTone(rule.severity)}`} />
          <div><strong>{rule.label}</strong><small>{rule.text}</small></div>
          <b className={`alert-severity-pill ${severityTone(rule.severity)}`}>{rule.severity}</b>
        </div>)}
      </div>
    </section>



    <section className="section-band scan-modern-card alerts-custom-card">
      <div className="scan-card-header compact">
        <span className="scan-card-icon"><SlidersHorizontal size={22} /></span>
        <div>
          <h2>Custom Alert Management</h2>
          <p>Project-level overrides for future scans. When disabled, the default Alert Routing Policy remains active.</p>
        </div>
        <span className={`scan-card-count ${policy?.enabled ? "" : "muted-count"}`}>{policy?.enabled ? "Custom Active" : "Default Active"}</span>
      </div>
      <div className="custom-alert-grid">
        <label>Project<select value={selectedProjectKey} onChange={(event) => setSelectedProjectKey(event.target.value)}>
          {projects.length === 0 ? <option value="">No Projects Registered</option> : projects.map((project) => <option value={project.project_key} key={project.project_key}>{project.name} · {project.project_key}</option>)}
        </select></label>
        <label>Policy Mode<select value={policy?.enabled ? "custom" : "default"} onChange={(event) => policy && setPolicy({ ...policy, enabled: event.target.value === "custom" })} disabled={!policy}>
          <option value="default">Use Default Routing Policy</option>
          <option value="custom">Use Custom Project Policy</option>
        </select></label>
        <label>Slack Alerts<select value={policy?.slack_enabled ? "enabled" : "disabled"} onChange={(event) => policy && setPolicy({ ...policy, slack_enabled: event.target.value === "enabled" })} disabled={!policy}>
          <option value="enabled">Enabled</option>
          <option value="disabled">Disabled</option>
        </select></label>
        <label>Slack Minimum Severity<select value={policy?.slack_min_severity ?? "LOW"} onChange={(event) => policy && setPolicy({ ...policy, slack_min_severity: event.target.value })} disabled={!policy}>
          {severityOptions.map((severity) => <option key={severity}>{severity}</option>)}
        </select></label>
        <label>Email Alerts<select value={policy?.email_enabled ? "enabled" : "disabled"} onChange={(event) => policy && setPolicy({ ...policy, email_enabled: event.target.value === "enabled" })} disabled={!policy}>
          <option value="enabled">Enabled</option>
          <option value="disabled">Disabled</option>
        </select></label>
        <label>Email Minimum Severity<select value={policy?.email_min_severity ?? "HIGH"} onChange={(event) => policy && setPolicy({ ...policy, email_min_severity: event.target.value })} disabled={!policy}>
          {severityOptions.map((severity) => <option key={severity}>{severity}</option>)}
        </select></label>
      </div>
      <div className="custom-alert-actions">
        <p>{policy?.enabled ? `Custom policy will override defaults for ${policy.project_name}.` : "Default: dashboard stores all alerts, Slack receives all severities, Email receives Critical and High."}</p>
        <button type="button" className="green-pill-button" onClick={handlePolicySave} disabled={!policy || policyLoading}>{policyLoading ? "Saving..." : "Save Alert Policy"}</button>
      </div>
      {policyMessage && <p className="policy-message">{policyMessage}</p>}
    </section>

    <form className="filter-bar reports-filter-card scan-modern-card alerts-filter-card" onSubmit={(event) => event.preventDefault()}>
      <div className="scan-card-header reports-filter-header">
        <span className="scan-card-icon"><SlidersHorizontal size={22} /></span>
        <div>
          <h2>Alert Filters</h2>
          <p>Filter Alertmanager records by search text, severity, and lifecycle status.</p>
        </div>
      </div>
      <label>Search<input placeholder="Project, repo, branch, or alert" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} /></label>
      <label>Severity<select value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}><option value="">All Severities</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option><option>INFO</option></select></label>
      <label>Status<select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}><option value="">All Statuses</option><option>OPEN</option><option>RESOLVED</option></select></label>
      <div className="reports-filter-actions">
        <button type="button" onClick={() => setFilters({ search: "", severity: "", status: "" })}><Search size={17} /> Reset</button>
      </div>
    </form>

    {error && <p className="error-text">{error}</p>}

    <section className="section-band scan-modern-card alerts-history-card">
      <div className="scan-card-header">
        <span className="scan-card-icon"><AlertCircle size={22} /></span>
        <div>
          <h2>Alert History</h2>
          <p>{latestAlert ? `Latest alert: ${titleCase(latestAlert.alert_type)} for ${latestAlert.project_name}` : "No matching alerts found."}</p>
        </div>
        <span className="scan-card-count">{visible.length} Alerts</span>
      </div>
      {loading ? <p className="muted">Loading alerts...</p> : visible.length === 0 ? <p className="muted">No alerts match these filters.</p> : <div className="alerts-modern-list">
        {visible.map((alert) => <article className={`alerts-modern-row ${statusTone(alert.status)}`} key={alert.alert_id}>
          <span className="alert-avatar"><AlertTriangle size={19} /></span>
          <div className="alert-primary-copy">
            <strong>{titleCase(alert.alert_type)}</strong>
            <span>{alert.description}</span>
          </div>
          <div className="alert-project-copy">
            <strong>{alert.project_name}</strong>
            <span>{alert.repository ?? "Repository not linked"}</span>
          </div>
          <b className={`alert-severity-pill ${severityTone(alert.severity)}`}>{alert.severity}</b>
          <b className={`alert-status-pill ${statusTone(alert.status)}`}>{alert.status}</b>
          <div className="alert-channel-list">{alert.notification_channels.map((channel) => <span key={channel}>{channelLabel(channel)}</span>)}</div>
          <div className="alert-meta-copy">
            <span>{formatDate(alert.created_at)}</span>
            {alert.scan_id ? <Link to={`/scans/${alert.scan_id}`}>View Scan</Link> : <small>No Scan Link</small>}
          </div>
          <p className="alert-recommendation"><strong>Recommendation:</strong> {alert.recommendation}</p>
        </article>)}
      </div>}
    </section>
  </section>;
}
