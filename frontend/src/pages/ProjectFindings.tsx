import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, ChevronRight, FileText, Search, ShieldAlert } from "lucide-react";
import { getProject, getProjectFindings, toolReportPdfUrl } from "../api/scans";
import type { ProjectFinding, ProjectHealth } from "../types/scans";

function formatDate(value: string | null | undefined) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function formatToolName(value: string) {
  const labels: Record<string, string> = {
    gitleaks: "GitLeaks",
    semgrep: "Semgrep",
    "trivy-fs": "Trivy FS",
    "trivy-image": "Trivy Image",
    sonarqube: "SonarQube",
    "unit-tests": "Unit Tests",
  };
  return labels[value] ?? value;
}

function statusTone(value: string) {
  if (value === "OPEN") return "critical";
  if (value === "RESOLVED") return "good";
  return "warning";
}

function severityTone(value: string) {
  const severity = value.toUpperCase();
  if (severity === "CRITICAL") return "critical";
  if (severity === "HIGH") return "high";
  if (severity === "MEDIUM") return "medium";
  if (severity === "LOW") return "low";
  return "unknown";
}

export function ProjectFindingsPage() {
  const { projectKey } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const status = (searchParams.get("status") ?? "open").toUpperCase();
  const [project, setProject] = useState<ProjectHealth | null>(null);
  const [findings, setFindings] = useState<ProjectFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectKey) return;
    setLoading(true);
    Promise.all([getProject(projectKey), getProjectFindings(projectKey, status)])
      .then(([projectData, findingData]) => {
        setProject(projectData);
        setFindings(findingData);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [projectKey, status]);

  const counts = useMemo(() => findings.reduce<Record<string, number>>((acc, finding) => {
    acc[finding.severity.toUpperCase()] = (acc[finding.severity.toUpperCase()] ?? 0) + 1;
    return acc;
  }, {}), [findings]);

  if (loading) return <section className="page"><div className="section-band scan-modern-card workspace-skeleton"><strong>Loading Project Findings...</strong><span /></div></section>;
  if (error || !project) return <p className="error-text">{error ?? "Project not found."}</p>;

  const tabs = ["OPEN", "RESOLVED", "PENDING_RECHECK", "ALL"];

  return <section className="page project-findings-page">
    <nav className="workspace-breadcrumb"><Link to="/projects">Projects</Link><ChevronRight size={14} /><Link to={`/projects/${project.project_key}`}>{project.name}</Link><ChevronRight size={14} /><span>Findings</span></nav>

    <header className="page-header workspace-header">
      <div>
        <p className="eyebrow">Project Finding History</p>
        <div className="workspace-title-row"><h1>{project.name} Findings</h1><span className={`decision-chip ${project.latest_decision.toLowerCase()}`}>{project.latest_decision}</span></div>
        <p className="workspace-repo-line">Grouped findings across scans for this repository. Open means the issue still appears in the latest scan; resolved means it disappeared in a later completed scan.</p>
      </div>
    </header>

    <div className="section-band scan-modern-card">
      <div className="scan-card-header"><span className="scan-card-icon"><ShieldAlert size={22} /></span><div><h2>Severity Summary</h2><p>{status.replace("_", " ")} findings across historical scans.</p></div><span className="scan-card-count">{findings.length} Findings</span></div>
      <div className="workspace-kpi-grid project-findings-summary">
        <div className="workspace-kpi-card critical"><span className="workspace-kpi-icon"><AlertTriangle size={20} /></span><div><strong>{counts.CRITICAL ?? 0}</strong><small>Critical</small><em>Immediate blockers.</em></div><b>Severity</b></div>
        <div className="workspace-kpi-card warning"><span className="workspace-kpi-icon"><AlertTriangle size={20} /></span><div><strong>{counts.HIGH ?? 0}</strong><small>High</small><em>Must be remediated quickly.</em></div><b>Severity</b></div>
        <div className="workspace-kpi-card warning"><span className="workspace-kpi-icon"><Search size={20} /></span><div><strong>{counts.MEDIUM ?? 0}</strong><small>Medium</small><em>Plan patching.</em></div><b>Severity</b></div>
        <div className="workspace-kpi-card good"><span className="workspace-kpi-icon"><CheckCircle2 size={20} /></span><div><strong>{counts.LOW ?? 0}</strong><small>Low</small><em>Monitor normally.</em></div><b>Severity</b></div>
      </div>
    </div>

    <div className="section-band scan-modern-card normalized-findings-card">
      <div className="scan-card-header"><span className="scan-card-icon"><FileText size={22} /></span><div><h2>Project Findings</h2><p>Grouped by tool, severity, title, and file across all scans.</p></div></div>
      <div className="workspace-tabs">
        {tabs.map((tab) => <button key={tab} className={status === tab ? "active" : ""} type="button" onClick={() => setSearchParams({ status: tab.toLowerCase() })}>{tab.replace("_", " ")}</button>)}
      </div>
      {findings.length === 0 ? <p className="muted workspace-empty-state">No {status.replace("_", " ").toLowerCase()} findings for this project.</p> : <div className="project-findings-table">
        <div className="project-finding-row project-finding-head"><span>Status</span><span>Severity</span><span>Tool</span><span>Finding</span><span>First Seen</span><span>Latest Seen</span><span>Evidence</span></div>
        {findings.map((finding) => <div className="project-finding-row" key={`${finding.tool}-${finding.severity}-${finding.title}-${finding.file}`}>
          <span className={`status-pill ${statusTone(finding.resolution_status)}`}>{finding.resolution_status.replace("_", " ")}</span>
          <span className={`severity-dot-label ${severityTone(finding.severity)}`}>{finding.severity}</span>
          <strong>{formatToolName(finding.tool)}</strong>
          <div><b>{finding.title}</b><small>{finding.file ?? "N/A"}</small></div>
          <Link to={`/scans/${finding.first_seen_scan_id}`}>{finding.first_seen_scan_id}<small>{formatDate(finding.first_seen_at)}</small></Link>
          <Link to={`/scans/${finding.latest_seen_scan_id}`}>{finding.latest_seen_scan_id}<small>{formatDate(finding.latest_seen_at)}</small></Link>
          <a className="inline-action" href={toolReportPdfUrl(finding.latest_seen_scan_id, finding.tool)}><FileText size={14} /> Tool PDF</a>
        </div>)}
      </div>}
    </div>
  </section>;
}
