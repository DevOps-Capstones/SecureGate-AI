import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, BarChart3, CheckCircle2, ChevronRight, Gauge, GitBranch, ShieldAlert, TrendingUp, XCircle } from "lucide-react";
import { getProject } from "../api/scans";
import type { ProjectHealth, ScanSummary } from "../types/scans";

function formatDate(value: string | null | undefined) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function score(scan: ScanSummary) {
  return scan.security_score ?? 0;
}

function duration(scan: ScanSummary) {
  if (!scan.received_at || !scan.completed_at) return "--";
  const seconds = Math.max(0, Math.round((new Date(scan.completed_at).getTime() - new Date(scan.received_at).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function statusTone(value: string | null | undefined) {
  const normalized = (value ?? "").toUpperCase();
  if (["APPROVED", "COMPLETED", "OK", "SUCCESS"].includes(normalized)) return "good";
  if (["REJECTED", "FAILED", "ERROR", "CRITICAL"].includes(normalized)) return "critical";
  return "warning";
}

function average(values: number[]) {
  return values.length ? Math.round(values.reduce((sum, item) => sum + item, 0) / values.length) : 0;
}

export function ProjectAnalyticsPage() {
  const { projectKey } = useParams();
  const [project, setProject] = useState<ProjectHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectKey) return;
    setLoading(true);
    setError(null);
    getProject(projectKey)
      .then(setProject)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [projectKey]);

  const recentScans = useMemo(() => project?.recent_scans ?? [], [project]);
  const chronologicalScans = [...recentScans].reverse();
  const approved = project?.decision_counts.APPROVED ?? 0;
  const rejected = project?.decision_counts.REJECTED ?? 0;
  const totalDecisions = approved + rejected + (project?.decision_counts.PENDING ?? 0);
  const approvalRate = totalDecisions ? Math.round((approved / totalDecisions) * 100) : 0;
  const averageScore = average(recentScans.map(score).filter((value) => value > 0));
  const critical = project?.severity_counts.CRITICAL ?? 0;
  const high = project?.severity_counts.HIGH ?? 0;
  const maxScore = Math.max(100, ...chronologicalScans.map(score));
  const kpis = project ? [
    { label: "Project Scans", value: project.total_scans, helper: "Total CI/CD submissions", icon: GitBranch, tone: "info" },
    { label: "Approval Rate", value: `${approvalRate}%`, helper: `${approved} Approved / ${rejected} Rejected`, icon: CheckCircle2, tone: approvalRate >= 80 ? "good" : "critical" },
    { label: "Average Score", value: `${averageScore}%`, helper: "Recent scan average", icon: Gauge, tone: averageScore >= 80 ? "good" : "critical" },
    { label: "Critical Findings", value: critical, helper: "Blocks deployment", icon: ShieldAlert, tone: critical > 0 ? "critical" : "good" },
    { label: "High Findings", value: high, helper: "Requires fast remediation", icon: AlertTriangle, tone: high > 0 ? "warning" : "good" },
  ] : [];

  if (loading) return <section className="page"><p className="muted">Loading project analytics...</p></section>;
  if (error || !project) return <section className="page"><p className="error-text">{error ?? "Project analytics not found."}</p></section>;

  return <section className="page analytics-page project-analytics-page">
    <nav className="workspace-breadcrumb"><Link to="/projects">Projects</Link><ChevronRight size={14} /><Link to={`/projects/${project.project_key}`}>{project.name}</Link><ChevronRight size={14} /><span>Analytics</span></nav>

    <header className="page-header monitoring-hero analytics-hero">
      <div>
        <p className="eyebrow">Project-Specific Analytics</p>
        <h1>{project.name} Analytics</h1>
        <p>Security score, deployment decisions, vulnerability severity, and tool health for this selected repository only.</p>
      </div>
      <span className={`monitoring-live-pill ${project.latest_decision === "APPROVED" ? "healthy" : "critical"}`}><TrendingUp size={16} /> {project.latest_decision}</span>
    </header>

    <div className="monitoring-telemetry-grid analytics-kpi-grid">
      {kpis.map((card) => {
        const Icon = card.icon;
        return <article className={`monitoring-metric-card ${card.tone}`} key={card.label}>
          <span className="monitoring-icon"><Icon size={21} /></span>
          <div><strong>{card.value}</strong><span>{card.label}</span><small>{card.helper}</small></div>
        </article>;
      })}
    </div>

    <section className="section-band scan-modern-card analytics-trend-card">
      <div className="scan-card-header">
        <span className="scan-card-icon"><BarChart3 size={22} /></span>
        <div>
          <h2>Project Score Trend</h2>
          <p>Latest scan scores for this project only, ordered from oldest to newest.</p>
        </div>
        <span className="scan-card-count">{chronologicalScans.length} Scans</span>
      </div>
      {chronologicalScans.length === 0 ? <p className="muted">No scan history yet.</p> : <div className="project-score-trend">
        {chronologicalScans.map((scan) => <Link to={`/scans/${scan.scan_id}`} className={`project-score-bar ${statusTone(scan.deployment_decision)}`} key={scan.scan_id} title={`${scan.scan_id}: ${score(scan)}%`}>
          <span style={{ height: `${Math.max(8, (score(scan) / maxScore) * 100)}%` }} />
          <small>{score(scan)}%</small>
          <b>{scan.scan_id.split("-")[scan.scan_id.split("-").length - 1]}</b>
        </Link>)}
      </div>}
    </section>

    <div className="monitoring-split-grid project-analytics-split">
      <section className="section-band scan-modern-card analytics-table-card">
        <div className="scan-card-header compact"><span className="scan-card-icon"><Gauge size={22} /></span><div><h2>Decision History</h2><p>Every recent scan and its project-level deployment outcome.</p></div></div>
        <div className="analytics-modern-list">
          <div className="analytics-modern-row analytics-head"><span>Scan</span><span>Score</span><span>Decision</span><span>Branch</span><span>Duration</span><span>Received</span></div>
          {recentScans.map((scan) => <div className="analytics-modern-row" key={scan.scan_id}>
            <Link to={`/scans/${scan.scan_id}`}>{scan.scan_id}</Link>
            <span>{score(scan)}%</span>
            <span className={scan.deployment_decision === "APPROVED" ? "analytics-good" : "analytics-critical"}>{scan.deployment_decision === "APPROVED" ? <CheckCircle2 size={14} /> : <XCircle size={14} />} {scan.deployment_decision}</span>
            <span>{scan.branch}</span>
            <span>{duration(scan)}</span>
            <span>{formatDate(scan.received_at)}</span>
          </div>)}
        </div>
      </section>

      <section className="section-band scan-modern-card analytics-table-card">
        <div className="scan-card-header compact"><span className="scan-card-icon"><ShieldAlert size={22} /></span><div><h2>Tool-Level Risk</h2><p>Current normalized vulnerability pressure by scanner.</p></div></div>
        <div className="project-tool-risk-list">
          {project.tool_health.map((tool) => <article className={`project-tool-risk-row ${tool.critical > 0 ? "critical" : tool.high > 0 ? "warning" : "good"}`} key={tool.tool}>
            <strong>{tool.label}</strong>
            <span>{tool.status}</span>
            <small>C {tool.critical} / H {tool.high} / M {tool.medium} / L {tool.low}</small>
          </article>)}
        </div>
      </section>
    </div>
  </section>;
}
