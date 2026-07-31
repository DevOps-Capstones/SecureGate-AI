import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Bot,
  CheckCircle2,
  ChevronRight,
  Circle,
  CircleCheck,
  CircleX,
  Download,
  FileCode2,
  FileJson,
  FileText,
  GitBranch,
  Github,
  LockKeyhole,
  Mail,
  Package,
  PlayCircle,
  Settings,
  ShieldAlert,
  Sparkles,
  Timer,
  Wrench,
} from "lucide-react";
import {
  aiRemediationPlanUrl,
  aiSummaryReportUrl,
  generateMasterReports,
  getMasterReportStatus,
  getAiInsights,
  getAiRemediationPlan,
  getProject,
  getScan,
  reportDownloadUrl,
  toolReportDownloadUrl,
  toolReportPdfUrl,
  triggerProjectScan,
} from "../api/scans";
import type { AIInsights, AIRemediationPlan, Finding, ProjectHealth, ScanDetails, ScanSummary, ToolReport } from "../types/scans";

function formatDate(value: string | null | undefined) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function githubOwner(repositoryUrl: string) {
  const match = repositoryUrl.match(/github\.com[:/]([^/]+)\//i);
  return match?.[1] ?? "Unknown";
}

function shortSha(value: string | null | undefined) {
  return value ? value.slice(0, 8) : "Not available";
}

function percent(value: number, total: number) {
  return total === 0 ? 0 : Math.round((value / total) * 100);
}

function scoreRing(score: number | null) {
  const safe = Math.min(Math.max(score ?? 0, 0), 100);
  return `conic-gradient(#259b49 0 ${safe}%, #e7eee9 ${safe}% 100%)`;
}

function statusTone(status: string | null | undefined) {
  const value = (status ?? "").toUpperCase();
  if (["APPROVED", "COMPLETED", "DONE", "PASSED", "OK", "SENT", "UPLOADED", "SUCCESS"].includes(value)) return "good";
  if (["REJECTED", "FAILED", "ERROR", "CRITICAL"].includes(value)) return "critical";
  if (["PENDING", "PROCESSING", "UNKNOWN", "SKIPPED"].includes(value)) return "warning";
  return "info";
}

function severityClass(value: string | null | undefined) {
  return (value ?? "unknown").toLowerCase();
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
  return labels[value] ?? value.split(/[-_ ]/).filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function durationBetween(start: string | null | undefined, end: string | null | undefined) {
  if (!start || !end) return "--";
  const seconds = Math.max(0, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function repositoryName(repositoryUrl: string) {
  return repositoryUrl.split("github.com/")[1] ?? repositoryUrl;
}

function repositoryHref(repositoryUrl: string) {
  return /^https?:\/\//i.test(repositoryUrl) ? repositoryUrl : `https://${repositoryUrl}`;
}

function securityCountClass(value: number | string | null | undefined) {
  return Number(value ?? 0) > 0 ? "security-count nonzero" : "security-count";
}

function StatCard({ icon: Icon, label, value, description, tone = "info", trend = "Latest", href, riskCount = false }: { icon: typeof ShieldAlert; label: string; value: string | number; description: string; tone?: string; trend?: string; href: string; riskCount?: boolean }) {
  return <Link to={href} className={`workspace-kpi-card ${tone}`}>
    <span className="workspace-kpi-icon"><Icon size={20} /></span>
    <div><strong className={riskCount ? securityCountClass(value) : ""}>{value}</strong><small>{label}</small><em>{description}</em></div>
    <b>{trend}</b>
  </Link>;
}

function MiniChart({ points, tone = "good" }: { points: number[]; tone?: string }) {
  const max = Math.max(1, ...points);
  return <div className={`workspace-mini-chart ${tone}`}>{points.map((point, index) => <i key={`${point}-${index}`} style={{ height: `${Math.max(10, (point / max) * 100)}%` }} />)}</div>;
}

function EmptyState({ text }: { text: string }) {
  return <p className="muted workspace-empty-state">{text}</p>;
}

function ReportCard({ title, generatedAt, href, disabled }: { title: string; generatedAt: string; href?: string; disabled?: boolean }) {
  return <article className="workspace-report-card">
    <span className="workspace-report-icon"><FileText size={20} /></span>
    <div><strong>{title}</strong><small>Generated: {generatedAt}</small><small>Size: Generated on download</small></div>
    {href && !disabled ? <a className="inline-action" href={href}><Download size={14} /> Download</a> : <button className="secondary-button" disabled>Unavailable</button>}
  </article>;
}

function ProjectScoreRing({ score, label }: { score: number | null; label: string }) {
  return <div className="project-score-ring" style={{ background: scoreRing(score) }}>
    <div><strong>{score ?? 0}%</strong><span>{label}</span></div>
  </div>;
}

function Donut({ approved, rejected, pending }: { approved: number; rejected: number; pending: number }) {
  const total = approved + rejected + pending;
  const approvedPct = percent(approved, total);
  const rejectedPct = percent(rejected, total);
  const style = { background: total === 0 ? "#dce8e4" : `conic-gradient(#5d8b38 0 ${approvedPct}%, #b43b3b ${approvedPct}% ${approvedPct + rejectedPct}%, #d8b13f ${approvedPct + rejectedPct}% 100%)` };
  return <div className="donut" style={style}><div className="donut-label"><span>{total}</span><small>scans</small></div></div>;
}

function SeverityDonut({ counts }: { counts: Record<string, number> }) {
  const critical = counts.CRITICAL ?? 0;
  const high = counts.HIGH ?? 0;
  const medium = counts.MEDIUM ?? 0;
  const low = counts.LOW ?? 0;
  const total = critical + high + medium + low;
  const c = percent(critical, total);
  const h = percent(high, total);
  const m = percent(medium, total);
  const style = { background: total === 0 ? "#dce8e4" : `conic-gradient(#8a1717 0 ${c}%, #d8751f ${c}% ${c + h}%, #d8b13f ${c + h}% ${c + h + m}%, #7fbf93 ${c + h + m}% 100%)` };
  return <div className="donut severity-donut" style={style}><div className="donut-label"><span className={securityCountClass(total)}>{total}</span><small>findings</small></div></div>;
}

export function ProjectDetailsPage() {
  const { projectKey } = useParams();
  const [project, setProject] = useState<ProjectHealth | null>(null);
  const [scanDetails, setScanDetails] = useState<ScanDetails | null>(null);
  const [activeTab, setActiveTab] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [triggerMessage, setTriggerMessage] = useState<string | null>(null);
  const [triggerError, setTriggerError] = useState<string | null>(null);
  const [aiInsights, setAiInsights] = useState<AIInsights | null>(null);
  const [remediationPlan, setRemediationPlan] = useState<AIRemediationPlan | null>(null);

  useEffect(() => {
    if (!projectKey) return;
    let active = true;
    setLoading(true);
    setError(null);
    setProject(null);
    setScanDetails(null);
    setAiInsights(null);
    setRemediationPlan(null);

    getProject(projectKey)
      .then(async (data) => {
        if (!active) return;
        setProject(data);
        if (data.latest_scan?.scan_id) {
          try {
            const details = await getScan(data.latest_scan.scan_id);
            if (active) setScanDetails(details);
          } catch {
            if (active) setScanDetails(null);
          }
        }
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [projectKey]);

  useEffect(() => {
    const latestScanId = project?.latest_scan?.scan_id;
    if (!latestScanId) {
      setAiInsights(null);
      setRemediationPlan(null);
      return;
    }

    let active = true;
    setAiInsights(null);
    setRemediationPlan(null);

    getAiInsights(latestScanId)
      .then((data) => { if (active) setAiInsights(data); })
      .catch(() => { if (active) setAiInsights(null); });

    getAiRemediationPlan(latestScanId)
      .then((data) => { if (active) setRemediationPlan(data); })
      .catch(() => { if (active) setRemediationPlan(null); });

    return () => { active = false; };
  }, [project?.latest_scan?.scan_id]);

  const latest = project?.latest_scan ?? null;
  const healthLabel = useMemo(() => {
    if (!project) return "Unknown";
    if (project.latest_decision === "APPROVED") return "Healthy";
    if (project.latest_decision === "REJECTED") return "Needs attention";
    return "Awaiting scans";
  }, [project]);

  if (loading) return <section className="page"><div className="section-band scan-modern-card workspace-skeleton"><strong>Loading Project Security Overview...</strong><span /></div></section>;
  if (error || !project) return <p className="error-text">{error ?? "Project not found."}</p>;

  const owner = githubOwner(project.repository_url);
  const findings = scanDetails?.findings ?? [];
  const uploadedReports = scanDetails?.uploaded_reports ?? [];
  const toolStatus = scanDetails?.tool_status ?? {};
  const notificationItems = scanDetails?.notifications ?? [];
  const recentScores = project.recent_scans.slice(0, 8).reverse().map((scan) => scan.security_score ?? 0);
  const criticalTrend = project.recent_scans.slice(0, 8).reverse().map(() => project.severity_counts.CRITICAL ?? 0);
  const successTrend = project.recent_scans.slice(0, 8).reverse().map((scan) => scan.deployment_decision === "APPROVED" ? 100 : 0);
  const durationTrend = project.recent_scans.slice(0, 8).reverse().map((scan) => scan.completed_at ? Math.max(1, Math.round((new Date(scan.completed_at).getTime() - new Date(scan.received_at).getTime()) / 1000)) : 1);
  const secrets = findings.filter((finding) => finding.tool === "gitleaks").length;
  const codeSmells = findings.filter((finding) => finding.tool === "sonarqube").length;
  const riskLevel = (project.severity_counts.CRITICAL ?? 0) > 0 || secrets > 0 ? "Critical" : (project.severity_counts.HIGH ?? 0) > 0 ? "High" : project.latest_decision === "APPROVED" ? "Low" : "Medium";
  const latestImageAvailable = Boolean(latest?.image_full_path || latest?.image_name);
  const dockerImageStatus = latestImageAvailable && project.latest_decision === "APPROVED" ? "Available" : "Not available";
  const latestUploadTime = uploadedReports.length > 0 ? uploadedReports[0].uploaded_at : latest?.report_generation_at;

  const toolUploaded = (tool: string) => uploadedReports.some((report) => report.tool_name === tool);
  const latestFinished = ["COMPLETED", "FAILED"].includes((latest?.status ?? "").toUpperCase());
  const latestPipelineFailed = [latest?.status, latest?.pipeline_status].some((value) => ["FAILED", "ERROR", "CANCELLED"].includes((value ?? "").toUpperCase()));
  const latestRejected = project.latest_decision === "REJECTED";
  const findingToolKey = (finding: Finding) => {
    const normalized = (finding.tool || finding.source_tool || "").toLowerCase().replace(/\s+/g, "-");
    if (normalized.includes("trivy") && normalized.includes("image")) return "trivy-image";
    if (normalized.includes("trivy")) return "trivy-fs";
    if (normalized.includes("sonar")) return "sonarqube";
    if (normalized.includes("gitleaks")) return "gitleaks";
    if (normalized.includes("semgrep")) return "semgrep";
    if (normalized.includes("unit")) return "unit-tests";
    return normalized;
  };
  const hasBlockingFinding = (tool: string, severities?: string[]) => findings.some((finding) => {
    if (findingToolKey(finding) !== tool) return false;
    return !severities || severities.includes((finding.severity ?? "").toUpperCase());
  });
  const findingRecommendation = (finding: Finding) => {
    const tool = findingToolKey(finding);
    if (tool === "gitleaks") return "Remove secret, rotate credential, and move it to CI/CD secrets.";
    if (tool === "semgrep") return "Fix the code pattern flagged by Semgrep, then rerun the scan.";
    if (tool.startsWith("trivy")) return "Upgrade the package or base image to a fixed version.";
    if (tool === "sonarqube") return "Resolve the quality gate issue, code smell, bug, or hotspot.";
    if (tool === "unit-tests") return "Fix failed tests or upload the latest test report.";
    return "Review the tool report and apply the recommended remediation.";
  };

  const toolStageStatus = (tool: string, failWhen = false) => {
    if (toolUploaded(tool)) return failWhen ? "FAILED" : "DONE";
    return latestFinished || latestPipelineFailed ? "FAILED" : "PENDING";
  };
  const notificationStageStatus = (type: string) => {
    const item = notificationItems.find((notification) => notification.notification_type === type);
    if (!item) return latestFinished || latestPipelineFailed ? "FAILED" : "PENDING";
    return item.status === "SENT" ? "DONE" : "FAILED";
  };
  const dockerBuildStageStatus = latestRejected
    ? "FAILED"
    : dockerImageStatus === "Available"
      ? "DONE"
      : (latestFinished || latestPipelineFailed ? "FAILED" : "PENDING");
  const trivyImageStageStatus = latestRejected
    ? "FAILED"
    : project.latest_decision === "APPROVED"
      ? toolStageStatus("trivy-image", hasBlockingFinding("trivy-image", ["CRITICAL", "HIGH"]))
      : (latestFinished || latestPipelineFailed ? "FAILED" : "PENDING");
  const pipelineStages = [
    { label: "Git Checkout", tool: "GitHub", status: latest ? "DONE" : "PENDING", timestamp: latest?.received_at, duration: "--" },
    { label: "Compilation", tool: "CI Runner", status: latestPipelineFailed ? "FAILED" : latest ? "DONE" : "PENDING", timestamp: latest?.processing_at ?? latest?.received_at, duration: durationBetween(latest?.received_at, latest?.processing_at) },
    { label: "GitLeaks", tool: "GitLeaks", status: toolStageStatus("gitleaks", hasBlockingFinding("gitleaks")), timestamp: uploadedReports.find((report) => report.tool_name === "gitleaks")?.uploaded_at, duration: "--" },
    { label: "Filesystem Scan", tool: "Trivy FS", status: toolStageStatus("trivy-fs", hasBlockingFinding("trivy-fs", ["CRITICAL", "HIGH"])), timestamp: uploadedReports.find((report) => report.tool_name === "trivy-fs")?.uploaded_at, duration: "--" },
    { label: "Unit Tests", tool: "Unit Tests", status: toolStageStatus("unit-tests"), timestamp: uploadedReports.find((report) => report.tool_name === "unit-tests")?.uploaded_at, duration: "--" },
    { label: "SonarQube Analysis", tool: "SonarQube", status: toolStageStatus("sonarqube"), timestamp: uploadedReports.find((report) => report.tool_name === "sonarqube")?.uploaded_at, duration: "--" },
    { label: "Quality Gate", tool: "SonarCloud", status: project.sonar_quality_gate === "OK" ? "DONE" : project.sonar_quality_gate === "UNKNOWN" && !latestFinished ? "PENDING" : "FAILED", timestamp: latest?.scoring_at, duration: "--" },
    { label: "Docker Build", tool: "Docker", status: dockerBuildStageStatus, timestamp: latest?.processing_at, duration: "--" },
    { label: "Trivy Image Scan", tool: "Trivy Image", status: trivyImageStageStatus, timestamp: uploadedReports.find((report) => report.tool_name === "trivy-image")?.uploaded_at, duration: "--" },
    { label: "Master Report", tool: "SecureGate AI", status: latest?.report_generation_at ? "DONE" : latestFinished ? "FAILED" : "PENDING", timestamp: latest?.report_generation_at, duration: durationBetween(latest?.scoring_at, latest?.report_generation_at) },
    { label: "Slack Notification", tool: "Slack", status: notificationStageStatus("SLACK"), timestamp: notificationItems.find((item) => item.notification_type === "SLACK")?.sent_at, duration: "--" },
    { label: "Email Notification", tool: "Email", status: notificationStageStatus("EMAIL"), timestamp: notificationItems.find((item) => item.notification_type === "EMAIL")?.sent_at, duration: "--" },
    { label: "Deployment Decision", tool: "Policy Engine", status: project.latest_decision === "APPROVED" ? "DONE" : project.latest_decision === "REJECTED" ? "FAILED" : "PENDING", timestamp: latest?.completed_at, duration: durationBetween(latest?.received_at, latest?.completed_at) },
  ];

  const activityEvents = [
    { label: "Git Push", timestamp: latest?.received_at, status: latest ? "DONE" : "PENDING", duration: "--" },
    { label: "Pipeline Started", timestamp: latest?.processing_at ?? latest?.received_at, status: latest?.pipeline_status ?? "PENDING", duration: "--" },
    ...pipelineStages.slice(2, 12).map((stage) => ({ label: stage.label, timestamp: stage.timestamp, status: stage.status, duration: stage.duration })),
    { label: project.latest_decision === "APPROVED" ? "Deployment Approved" : "Deployment Blocked", timestamp: latest?.completed_at, status: project.latest_decision, duration: durationBetween(latest?.received_at, latest?.completed_at) },
  ];


  async function handleTriggerScan() {
    if (!project) return;
    setTriggering(true);
    setTriggerMessage(null);
    setTriggerError(null);
    try {
      const result = await triggerProjectScan(project.project_key, latest?.branch ?? "main");
      setTriggerMessage(`${result.message} Runner: ${result.runner}. Branch: ${result.branch}.`);
    } catch (err) {
      setTriggerError(err instanceof Error ? err.message : "Unable to trigger GitHub Actions workflow.");
    } finally {
      setTriggering(false);
    }
  }

  async function handlePdfDownload(scanId: string) {
    try {
      const reportStatus = await getMasterReportStatus(scanId);
      if (!reportStatus.has_master_report) {
        const shouldGenerate = window.confirm("No master report was generated for this scan. Would you like SecureGate AI to generate it now?");
        if (!shouldGenerate) return;
        await generateMasterReports(scanId);
      }
      window.location.href = reportDownloadUrl(scanId, "pdf");
    } catch (err) {
      const shouldGenerate = window.confirm("No master report was found or it could not be opened. Would you like SecureGate AI to generate it now?");
      if (!shouldGenerate) return;
      try {
        await generateMasterReports(scanId);
        window.location.href = reportDownloadUrl(scanId, "pdf");
      } catch (nextErr) {
        setError(nextErr instanceof Error ? nextErr.message : "Unable to generate master report.");
      }
    }
  }

  const findingToolOrder = ["gitleaks", "semgrep", "trivy-fs", "trivy-image", "sonarqube", "unit-tests"];
  const findingToolCounts = findings.reduce<Record<string, number>>((counts, finding) => {
    const key = findingToolKey(finding);
    counts[key] = (counts[key] ?? 0) + 1;
    return counts;
  }, {});
  const findingTabs = [
    { key: "all", label: "All", count: findings.length },
    ...findingToolOrder.filter((key) => findingToolCounts[key] > 0).map((key) => ({ key, label: formatToolName(key), count: findingToolCounts[key] })),
  ];
  const currentFindings = activeTab === "all" ? findings : findings.filter((finding) => findingToolKey(finding) === activeTab);
  const findingsHref = latest ? `/scans/${latest.scan_id}` : "/reports";
  const passedStages = pipelineStages.filter((stage) => statusTone(stage.status) === "good").length;
  const toolReport = (tool: string): ToolReport | undefined => uploadedReports.find((report) => report.tool_name === tool);

  return <section className="page project-workspace-page">
    <nav className="workspace-breadcrumb"><Link to="/projects">Projects</Link><ChevronRight size={14} /><span>{project.name}</span></nav>

    <header className="page-header workspace-header">
      <div>
        <p className="eyebrow">Project Security Overview</p>
        <div className="workspace-title-row"><h1>{project.name}</h1><span className={`decision-chip ${project.latest_decision.toLowerCase()}`}>{project.latest_decision}</span></div>
      </div>
      <div className="workspace-header-actions">
        <button className="secondary-button workspace-action-trigger" type="button" onClick={handleTriggerScan} disabled={triggering}><PlayCircle size={15} /> {triggering ? "Triggering..." : "Trigger Scan"}</button>
        <Link className="inline-action workspace-action-analytics" to={`/projects/${project.project_key}/analytics`}><BarChart3 size={15} /> View Analytics</Link>
        <Link className="inline-action workspace-action-alerts" to="/alerts"><Bell size={15} /> View Alerts</Link>
        {latest ? <button className="secondary-button workspace-action-download" type="button" onClick={() => handlePdfDownload(latest.scan_id)}><Download size={15} /> Download Report</button> : <button className="secondary-button workspace-action-download" type="button" disabled><Download size={15} /> Download Report</button>}
        {latest ? <Link className="inline-action workspace-action-remediation" to={`/remediation-plan?scan_id=${latest.scan_id}`}><Wrench size={15} /> Remediation Plan</Link> : <button className="secondary-button workspace-action-remediation" type="button" disabled><Wrench size={15} /> Remediation Plan</button>}
        {latest ? <a className="secondary-button workspace-action-ai" href={aiSummaryReportUrl(latest.scan_id)}><Bot size={15} /> AI Summary</a> : <button className="secondary-button workspace-action-ai" type="button" disabled><Bot size={15} /> AI Summary</button>}
      </div>
    </header>

    {(triggerMessage || triggerError) && <div className={`trigger-feedback ${triggerError ? "error" : "success"}`}>{triggerError ?? triggerMessage}</div>}

    <div className="project-hero section-band scan-modern-card project-overview-card">
      <div className="project-overview-header">
        <span className="scan-card-icon"><Github size={22} /></span>
        <div><h2>Project Overview</h2></div>
      </div>
      <div className="project-overview-grid">
        <div className="project-overview-details project-overview-details-wide">
          <div><span>Project Name</span><strong>{project.name}</strong></div>
          <div><span>Project ID</span><strong>{project.project_key}</strong></div>
          <div><span>Repository URL</span><strong className="truncate"><a className="repo-link" href={repositoryHref(project.repository_url)} target="_blank" rel="noreferrer">{project.repository_url}</a></strong></div>
          <div><span>Default Branch</span><strong>{latest?.branch ?? "main"}</strong></div>
          <div><span>Current Branch</span><strong>{latest?.branch ?? "No scan yet"}</strong></div>
          <div><span>Latest Commit</span><strong>{shortSha(latest?.commit_sha)}</strong></div>
          <div><span>Commit Author</span><strong>{owner}</strong></div>
          <div><span>Pipeline</span><strong>{latest?.pipeline_run_id ? `GitHub Actions #${latest.pipeline_run_id}` : "GitHub Actions"}</strong></div>
          <div><span>Latest Scan</span><strong>{latest?.scan_id ?? "No scan yet"}</strong></div>
          <div><span>Project Owner</span><strong>{owner}</strong></div>
          <div><span>Created Date</span><strong>{formatDate(project.created_at)}</strong></div>
          <div><span>Last Updated</span><strong>{formatDate(latest?.completed_at ?? latest?.received_at)}</strong></div>
          <div><span>Docker Image</span><strong className="truncate">{latest?.image_name ?? latest?.image_full_path ?? "Not available"}</strong></div>
          <div><span>Docker Tag</span><strong>{latest?.image_tag ?? "Not available"}</strong></div>
        </div>
        <ProjectScoreRing score={project.latest_security_score} label={healthLabel} />
      </div>
    </div>

    <div className="dashboard-grid workspace-donut-row">
      <div className="section-band chart-card"><div className="section-title"><h2>Decision Health</h2><BarChart3 size={20} /></div><Donut approved={project.decision_counts.APPROVED ?? 0} rejected={project.decision_counts.REJECTED ?? 0} pending={project.decision_counts.PENDING ?? 0} /><div className="legend-row color-legend"><span className="legend-approved">Approved</span><span className="legend-rejected">Rejected</span><span className="legend-pending">Pending</span></div></div>
      <div className="section-band chart-card"><div className="section-title"><h2>Finding Severity</h2><ShieldAlert size={20} /></div><SeverityDonut counts={project.severity_counts} /><div className="legend-row color-legend"><span className="legend-critical">Critical</span><span className="legend-high">High</span><span className="legend-medium">Medium</span><span className="legend-low">Low</span></div></div>
    </div>

    <div className="section-band scan-modern-card project-security-summary-card">
      <div className="scan-card-header"><span className="scan-card-icon"><ShieldAlert size={22} /></span><div><h2>Security Summary</h2><p>Latest project-level risk indicators and deployment readiness.</p></div><span className="scan-card-count">{riskLevel} Risk</span></div>
      <div className="workspace-kpi-grid">
        <StatCard icon={BarChart3} label="Security Score" value={`${project.latest_security_score ?? 0}%`} description="Latest computed SecureGate score." tone={(project.latest_security_score ?? 0) < 80 ? "critical" : "good"} trend="Latest" href={findingsHref} />
        <StatCard icon={CheckCircle2} label="Deployment Status" value={project.latest_decision} description="Current policy decision." tone={statusTone(project.latest_decision)} trend="Policy" href={findingsHref} />
        <StatCard icon={ShieldAlert} label="Critical Vulnerabilities" value={project.severity_counts.CRITICAL ?? 0} description="Blocking production risk." tone={(project.severity_counts.CRITICAL ?? 0) > 0 ? "critical" : "good"} trend="CVE" href={findingsHref} riskCount />
        <StatCard icon={AlertTriangle} label="High Vulnerabilities" value={project.severity_counts.HIGH ?? 0} description="Must be remediated quickly." tone={(project.severity_counts.HIGH ?? 0) > 0 ? "warning" : "good"} trend="CVE" href={findingsHref} riskCount />
        <StatCard icon={AlertTriangle} label="Medium Vulnerabilities" value={project.severity_counts.MEDIUM ?? 0} description="Plan patching in next cycle." tone={(project.severity_counts.MEDIUM ?? 0) > 0 ? "warning" : "good"} trend="CVE" href={findingsHref} riskCount />
        <StatCard icon={Circle} label="Low Vulnerabilities" value={project.severity_counts.LOW ?? 0} description="Monitor and patch normally." tone="info" trend="CVE" href={findingsHref} riskCount />
        <StatCard icon={LockKeyhole} label="Secrets Found" value={secrets} description="Secrets block deployment." tone={secrets > 0 ? "critical" : "good"} trend="GitLeaks" href={findingsHref} riskCount />
        <StatCard icon={FileCode2} label="Code Smells" value={codeSmells} description="Maintainability issues from analysis." tone={codeSmells > 0 ? "warning" : "good"} trend="Sonar" href={findingsHref} riskCount />
        <StatCard icon={CheckCircle2} label="Quality Gate" value={project.sonar_quality_gate} description="SonarCloud quality gate result." tone={statusTone(project.sonar_quality_gate)} trend="Gate" href={findingsHref} />
        <StatCard icon={Package} label="Docker Image Status" value={dockerImageStatus} description="Latest image build/scan availability." tone={dockerImageStatus === "Available" ? "good" : "critical"} trend="Image" href={findingsHref} />
        <StatCard icon={Sparkles} label="AI Readiness" value={aiInsights?.overall_risk ?? "Pending"} description={aiInsights?.ai_readiness ?? "AI assessment waiting for latest scan context."} tone={aiInsights?.overall_risk === "Low" ? "good" : aiInsights?.overall_risk === "Critical" ? "critical" : "warning"} trend="Gemma" href={latest ? `/scans/${latest.scan_id}` : findingsHref} />
        <StatCard icon={Activity} label="Overall Risk Level" value={riskLevel} description="Calculated from blocking findings." tone={riskLevel === "Critical" ? "critical" : riskLevel === "High" || riskLevel === "Medium" ? "warning" : "good"} trend="Risk" href={findingsHref} />
      </div>
    </div>

    <div className="section-band scan-modern-card">
      <div className="scan-card-header"><span className="scan-card-icon"><Activity size={22} /></span><div><h2>Pipeline Timeline</h2><p>Horizontal execution timeline for the latest scan.</p></div><span className="scan-card-count">{passedStages}/{pipelineStages.length} Stages Passed</span></div>
      <div className="workspace-pipeline-timeline">
        {pipelineStages.map((stage) => {
          const Icon = statusTone(stage.status) === "good" ? CircleCheck : statusTone(stage.status) === "critical" ? CircleX : Circle;
          return <div className={`workspace-pipeline-stage ${statusTone(stage.status)}`} key={stage.label} title={`${stage.tool} | ${stage.status} | ${stage.duration}`}>
            <span><Icon size={17} /></span><strong>{stage.label}</strong><small>{stage.tool}</small><em>{formatDate(stage.timestamp)}</em><b>{stage.duration}</b>
          </div>;
        })}
      </div>
    </div>

    <div className="section-band scan-modern-card" id="security-findings">
      <div className="scan-card-header"><span className="scan-card-icon"><FileCode2 size={22} /></span><div><h2>Security Findings</h2><p>Tool-specific findings normalized by SecureGate AI.</p></div><span className="scan-card-count"><span className={securityCountClass(findings.length)}>{findings.length}</span> Findings</span></div>
      <div className="workspace-tabs">{findingTabs.map((tab) => <button className={activeTab === tab.key ? "active" : ""} onClick={() => setActiveTab(tab.key)} key={tab.key}>{tab.label} <span className={securityCountClass(tab.count)}>{tab.count}</span></button>)}</div>
      {activeTab === "sonarqube" && <div className="sonar-summary-grid"><span>Quality Gate <strong>{project.sonar_quality_gate}</strong></span><span>Coverage <strong>--</strong></span><span>Code Smells <strong className={securityCountClass(codeSmells)}>{codeSmells}</strong></span><span>Bugs <strong className={securityCountClass(findings.filter((finding) => findingToolKey(finding) === "sonarqube" && finding.title.toLowerCase().includes("bug")).length)}>{findings.filter((finding) => findingToolKey(finding) === "sonarqube" && finding.title.toLowerCase().includes("bug")).length}</strong></span><span>Duplications <strong>--</strong></span><span>Security Hotspots <strong className={securityCountClass(findings.filter((finding) => findingToolKey(finding) === "sonarqube" && finding.title.toLowerCase().includes("hotspot")).length)}>{findings.filter((finding) => findingToolKey(finding) === "sonarqube" && finding.title.toLowerCase().includes("hotspot")).length}</strong></span><span>Technical Debt <strong>--</strong></span></div>}
      {currentFindings.length === 0 ? <EmptyState text="No findings available for this tool in the latest scan." /> : <div className="workspace-findings-table">
        {currentFindings.slice(0, 12).map((finding, index) => <div className="workspace-finding-row" key={`${finding.tool}-${finding.title}-${index}`}>
          <span className={`severity ${severityClass(finding.severity)}`}>{finding.severity}</span>
          <span className="tool-caught-pill">{formatToolName(findingToolKey(finding))}</span>
          <strong>{finding.title}</strong>
          <code>{finding.file ?? "N/A"}</code>
          <small>{findingRecommendation(finding)}</small>
        </div>)}
      </div>}
    </div>

    <div className="section-band scan-modern-card">
      <div className="scan-card-header"><span className="scan-card-icon"><FileText size={22} /></span><div><h2>Reports</h2><p>Download master and tool-level evidence for the latest scan.</p></div></div>
      <div className="workspace-report-grid">
        {latest && <><ReportCard title="Master Security Report PDF" generatedAt={formatDate(latest.report_generation_at)} href={reportDownloadUrl(latest.scan_id, "pdf")} /><ReportCard title="Master Security Report DOCX" generatedAt={formatDate(latest.report_generation_at)} href={reportDownloadUrl(latest.scan_id, "docx")} /><ReportCard title="Master Security Report JSON" generatedAt={formatDate(latest.report_generation_at)} href={reportDownloadUrl(latest.scan_id, "json")} /></>}
        {["gitleaks", "trivy-fs", "trivy-image", "sonarqube"].map((tool) => <ReportCard key={tool} title={`${formatToolName(tool)} Report`} generatedAt={formatDate(toolReport(tool)?.uploaded_at)} href={latest && toolReport(tool) ? toolReportPdfUrl(latest.scan_id, tool) : undefined} disabled={!latest || !toolReport(tool)} />)}
      </div>
    </div>

    <div className="section-band scan-modern-card">
      <div className="scan-card-header"><span className="scan-card-icon"><BarChart3 size={22} /></span><div><h2>Historical Security Trends</h2><p>Modular chart placeholders ready for future Grafana panel replacement.</p></div></div>
      <div className="workspace-chart-grid"><div><strong>Security Score Trend</strong><MiniChart points={recentScores} /></div><div><strong>Critical Vulnerabilities Trend</strong><MiniChart points={criticalTrend} tone="critical" /></div><div><strong>Deployment Success Rate</strong><MiniChart points={successTrend} /></div><div><strong>Scan Duration Trend</strong><MiniChart points={durationTrend} tone="info" /></div><div><strong>Secrets Trend</strong><MiniChart points={[secrets, secrets, secrets]} tone={secrets > 0 ? "critical" : "good"} /></div><div><strong>Code Smells Trend</strong><MiniChart points={[codeSmells, codeSmells, codeSmells]} tone="warning" /></div></div>
    </div>

    <div className="section-band scan-modern-card">
      <div className="scan-card-header"><span className="scan-card-icon"><Bell size={22} /></span><div><h2>Notifications</h2><p>Latest Slack and email delivery events for this repository.</p></div><span className="scan-card-count">{notificationItems.length} Events</span></div>
      {notificationItems.length === 0 ? <EmptyState text="No notifications were recorded for the latest scan." /> : <div className="workspace-notification-list">{notificationItems.slice(0, 6).map((item) => <div key={`${item.notification_type}-${item.created_at}`}><span>{item.notification_type === "EMAIL" ? <Mail size={18} /> : <Bell size={18} />}</span><strong>{item.notification_type}</strong><small>{item.status} | {formatDate(item.sent_at ?? item.created_at)}</small><code>{item.recipient}</code><em>Retry Count: 0</em></div>)}</div>}
    </div>

    <div className="section-band scan-modern-card">
      <div className="scan-card-header"><span className="scan-card-icon"><Settings size={22} /></span><div><h2>Project Configuration</h2><p>Read-only repository security configuration.</p></div></div>
      <div className="settings-table-grid settings-modern-table"><div className="settings-table-head">Setting</div><div className="settings-table-head">Value</div>{[
        ["Repository", project.repository_url], ["Default Branch", latest?.branch ?? "main"], ["Webhook Status", latest ? "Connected through CI/CD" : "Waiting for first scan"], ["Security Threshold", "80 minimum score, no secrets, no critical vulnerabilities"], ["Quality Gate", project.sonar_quality_gate], ["Slack Channel", notificationItems.find((item) => item.notification_type === "SLACK")?.recipient ?? "Not configured"], ["Email Recipients", notificationItems.find((item) => item.notification_type === "EMAIL")?.recipient ?? "Not configured"], ["Docker Hub Repository", latest?.image_full_path ?? "Not available"], ["Retention Policy", "Last 12 months"], ["Rescan Policy", "On push or scheduled pipeline"]
      ].map(([name, value]) => <div className="settings-table-row" key={name}><span>{name}</span><strong>{value}</strong></div>)}</div>
    </div>

    <div className="section-band scan-modern-card">
      <div className="scan-card-header"><span className="scan-card-icon"><Timer size={22} /></span><div><h2>Activity Timeline</h2><p>Vertical scan activity history for the latest repository scan.</p></div></div>
      <div className="workspace-activity-timeline">{activityEvents.map((event) => <div className={`workspace-activity-event ${statusTone(event.status)}`} key={event.label}><span /><div><strong>{event.label}</strong><small>{formatDate(event.timestamp)}</small></div><em>{event.duration}</em><b>{event.status}</b></div>)}</div>
    </div>

    <div className="section-band scan-modern-card remediation-plan-card">
      <div className="scan-card-header"><span className="scan-card-icon"><Bot size={22} /></span><div><h2>AI Remediation Plan</h2><p>Developer-focused fix plan generated from the latest Master Security Report and normalized findings.</p></div><span className={`scan-card-count ${remediationPlan?.production_ready ? "" : "failed"}`}>{remediationPlan?.production_ready ? "READY" : remediationPlan ? "ACTION REQUIRED" : "WAITING"}</span></div>
      <div className="remediation-kpi-grid">
        <div><span>Overall Priority</span><strong>{remediationPlan?.overall_priority ?? "Pending"}</strong></div>
        <div><span>Estimated Fix Time</span><strong>{remediationPlan?.estimated_fix_time ?? "--"}</strong></div>
        <div><span>Total Critical Issues</span><strong className={securityCountClass(remediationPlan?.finding_counts?.CRITICAL ?? 0)}>{String(remediationPlan?.finding_counts?.CRITICAL ?? 0)}</strong></div>
        <div><span>Total High Issues</span><strong className={securityCountClass(remediationPlan?.finding_counts?.HIGH ?? 0)}>{String(remediationPlan?.finding_counts?.HIGH ?? 0)}</strong></div>
        <div><span>Total Recommended Actions</span><strong className={securityCountClass(remediationPlan?.total_recommended_actions ?? 0)}>{remediationPlan?.total_recommended_actions ?? 0}</strong></div>
      </div>
      <div className="remediation-action-row project-remediation-actions">
        {latest && <Link className="green-pill-button" to={`/remediation-plan?scan_id=${latest.scan_id}`}><FileText size={14} /> View Plan</Link>}
        {latest && <a className="green-pill-button" href={aiRemediationPlanUrl(latest.scan_id)}><Download size={14} /> Download PDF</a>}
        <button className="green-pill-button ask-ai-button" type="button" onClick={() => window.dispatchEvent(new CustomEvent("securegate:open-ai-assistant"))}><Bot size={14} /> Ask AI</button>
      </div>
    </div>

    <div className="section-band scan-modern-card workspace-ai-placeholders ai-live-summary-card">
      <div className="scan-card-header"><span className="scan-card-icon"><Sparkles size={22} /></span><div><h2>AI Security Insights</h2><p>Concise AI-assisted risk summary and remediation guidance for the latest scan.</p></div><span className={`scan-card-count ${aiInsights?.ollama_status === "UNAVAILABLE" ? "failed" : ""}`}>{aiInsights?.ollama_status ?? "Waiting"}</span></div>
      <div className="ai-summary-content ai-insight-grid">
        <article className="ai-insight-panel ai-risk-panel">
          <span>Risk Level</span>
          <strong>{aiInsights?.overall_risk ?? "Pending"}</strong>
          <p>{aiInsights?.executive_summary ?? "Run a scan to generate an AI project summary."}</p>
          <small>{aiInsights?.estimated_fix_time ?? "Estimated fix time will appear here."}</small>
        </article>
        <article className="ai-insight-panel ai-actions-panel">
          <span>Priority Actions</span>
          <ul>{(aiInsights?.top_recommendations ?? ["Review project findings and tool reports after the next scan."]).slice(0, 3).map((item, index) => <li key={item}><b>{String(index + 1).padStart(2, "0")}</b><em>{item}</em></li>)}</ul>
        </article>
        <article className="ai-insight-panel ai-download-panel">
          <span>AI Reports</span>
          <p>{latest ? `Latest scan ${latest.scan_id}` : "Reports appear after a scan completes."}</p>
          <div className="ai-report-actions">{latest && <><a className="green-pill-button" href={aiSummaryReportUrl(latest.scan_id)}>AI Summary PDF</a><a className="green-pill-button" href={aiRemediationPlanUrl(latest.scan_id)}>Remediation PDF</a></>}</div>
        </article>
      </div>
    </div>


    <div className="section-band scan-modern-card">
      <div className="scan-card-header"><span className="scan-card-icon"><Activity size={22} /></span><div><h2>Recent Scans</h2><p>Repository scan history received from CI/CD pipelines.</p></div><span className="scan-card-count">{project.recent_scans.length} Shown</span></div>
      {project.recent_scans.length === 0 ? <EmptyState text="No CI/CD scans received for this project yet." /> : <div className="table"><div className="table-row table-head decision-row"><span>Scan ID</span><span>Status</span><span>Score</span><span>Decision</span><span>Received</span><span>Report</span></div>{project.recent_scans.map((scan: ScanSummary) => <div className="table-row decision-row" key={scan.scan_id}><Link to={`/scans/${scan.scan_id}`}>{scan.scan_id}</Link><span>{scan.status}</span><span>{scan.security_score ?? "--"}%</span><span className={`status-text ${scan.deployment_decision.toLowerCase()}`}>{scan.deployment_decision}</span><span>{formatDate(scan.received_at)}</span><button className="mini-button" type="button" onClick={() => handlePdfDownload(scan.scan_id)}>PDF</button></div>)}</div>}
    </div>

    <article className="section-band guide-panel"><div className="section-title"><h2>Add SecureGate AI to this repo</h2><GitBranch size={20} /></div><p className="muted">Use project name <strong>{project.name}</strong> in the GitHub Actions sample. SecureGate AI will attach each push scan to this project when the repository URL matches.</p><div className="command-strip"><code>.github/workflows/securegate-ai.yml</code></div></article>
  </section>;
}
