import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, AlertTriangle, BarChart3, CheckCircle2, ChevronLeft, ChevronRight, Circle, CircleCheck, CircleX, CloudUpload, FileText, Gauge, Github, LockKeyhole, Package, Search, ShieldAlert, TrendingUp } from "lucide-react";
import { aiRemediationPlanUrl, aiSummaryReportUrl, getAiInsights, getDashboardSummary, reportDownloadUrl, toolReportDownloadUrl, toolReportPdfUrl } from "../api/scans";
import type { AIInsights, DashboardSummary } from "../types/scans";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function maxTrendTotal(items: DashboardSummary["vulnerability_trend"]) {
  return Math.max(1, ...items.map((item) => item.CRITICAL + item.HIGH + item.MEDIUM + item.LOW));
}

function conicGradient(items: Array<{ value: number; color: string }>) {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  if (total <= 0) return "conic-gradient(#dfe7e1 0deg 360deg)";
  let cursor = 0;
  const stops = items.filter((item) => item.value > 0).map((item) => {
    const start = cursor;
    const end = cursor + (item.value / total) * 360;
    cursor = end;
    return `${item.color} ${start.toFixed(1)}deg ${end.toFixed(1)}deg`;
  });
  return `conic-gradient(${stops.join(", ")})`;
}

function securityCountClass(value: number | string | null | undefined) {
  return Number(value ?? 0) > 0 ? "security-count nonzero" : "security-count";
}

function formatToolName(value: string) {
  const labels: Record<string, string> = {
    gitleaks: "GitLeaks",
    semgrep: "Semgrep",
    "trivy-fs": "Trivy FS",
    sonarqube: "SonarQube",
    "unit-tests": "Unit Tests",
    "trivy-image": "Trivy Image",
  };
  return labels[value] ?? value.split(/[-_ ]/).filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function dashboardToolIcon(value: string) {
  if (value === "gitleaks") return Github;
  if (value === "semgrep") return Search;
  if (value === "trivy-fs" || value === "trivy-image") return Package;
  if (value === "sonarqube") return Activity;
  if (value === "unit-tests") return ShieldAlert;
  return FileText;
}

function decisionIcon(value: string) {
  if (value === "APPROVED") return CheckCircle2;
  if (value === "REJECTED") return AlertTriangle;
  return Activity;
}

function pagedItems<T>(items: T[], page: number, pageSize: number) {
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(Math.max(page, 0), totalPages - 1);
  return {
    items: items.slice(safePage * pageSize, safePage * pageSize + pageSize),
    page: safePage,
    totalPages,
  };
}

function PaginationControls({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="widget-pagination" aria-label="Widget pagination">
      <button type="button" onClick={() => onPageChange(page - 1)} disabled={page === 0} aria-label="Previous page">
        <ChevronLeft size={15} />
      </button>
      <span>Page {page + 1} Of {totalPages}</span>
      <button type="button" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages - 1} aria-label="Next page">
        <ChevronRight size={15} />
      </button>
    </div>
  );
}

export function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [activeCriterion, setActiveCriterion] = useState("securegate");
  const [scorePage, setScorePage] = useState(0);
  const [vulnerabilityPage, setVulnerabilityPage] = useState(0);
  const [reportPage, setReportPage] = useState(0);
  const [uploadPage, setUploadPage] = useState(0);
  const [scanPage, setScanPage] = useState(0);
  const [aiInsights, setAiInsights] = useState<AIInsights | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const loadSummary = useCallback(() => {
    setError(null);
    return getDashboardSummary()
      .then((data) => { setSummary(data); setLastUpdated(new Date()); })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadSummary();
    const timer = window.setInterval(loadSummary, 15000);
    return () => window.clearInterval(timer);
  }, [loadSummary]);

  const latestScore = summary?.latest_security_score ?? null;
  const trendHeight = (score: number) => `${Math.min(Math.max(score, 0), 100)}%`;
  const stats = [
    { label: "Security Score", value: latestScore == null ? "--" : `${latestScore}%`, icon: Gauge, score: latestScore },
    { label: "Approval Status", value: summary?.latest_approval_status ?? "PENDING", icon: CheckCircle2 },
    { label: "Active Scans", value: String(summary?.active_scans ?? 0), icon: Activity },
    { label: "Critical Findings", value: String(summary?.critical_findings ?? 0), icon: ShieldAlert, riskCount: true },
    { label: "High Findings", value: String(summary?.high_findings ?? 0), icon: AlertTriangle, riskCount: true }
  ];
  const toolInfo: Record<string, string> = {
    gitleaks: "Detects leaked secrets and credentials.",
    semgrep: "Finds insecure source-code patterns.",
    "trivy-fs": "Scans dependencies and filesystem vulnerabilities.",
    sonarqube: "Checks quality gate, bugs, and maintainability.",
    "unit-tests": "Blocks failed tests; skips safely when none exist.",
    "trivy-image": "Scans the built container image.",
  };

  const scoreTrendPage = pagedItems(summary?.score_trend ?? [], scorePage, 10);
  const vulnerabilityTrendPage = pagedItems(summary?.vulnerability_trend ?? [], vulnerabilityPage, 5);
  const reportsPage = pagedItems(summary?.recent_reports ?? [], reportPage, 5);
  const uploadsPage = pagedItems(summary?.latest_uploads ?? [], uploadPage, 5);
  const scansPage = pagedItems(summary?.recent_scans ?? [], scanPage, 10);

  const notificationCounts = (summary?.recent_notifications ?? []).reduce<Record<string, number>>((acc, item) => {
    acc[item.status] = (acc[item.status] ?? 0) + 1;
    return acc;
  }, {});
  const scoreTrend = summary?.score_trend ?? [];
  const latestTrendScore = scoreTrend.length > 0 ? scoreTrend[scoreTrend.length - 1].score : null;
  const previousTrendScore = scoreTrend.length > 1 ? scoreTrend[scoreTrend.length - 2].score : latestTrendScore;
  const scoreDelta = latestTrendScore != null && previousTrendScore != null ? latestTrendScore - previousTrendScore : 0;
  const scoreTone = latestScore == null ? "Waiting" : latestScore >= 90 ? "Excellent" : latestScore >= 80 ? "Good" : latestScore >= 60 ? "Needs Attention" : "Critical";
  const activeProjectFindingsHref = summary?.active_project_key ? `/projects/${summary.active_project_key}/findings?status=open` : "/reports";
  const mediumFindings = summary?.medium_findings ?? 0;
  const lowFindings = summary?.low_findings ?? 0;
  const totalSeverityFindings = (summary?.critical_findings ?? 0) + (summary?.high_findings ?? 0) + mediumFindings + lowFindings;
  const recentScans = summary?.recent_scans ?? [];
  const approvedScans = recentScans.filter((scan) => scan.deployment_decision === "APPROVED").length;
  const rejectedScans = recentScans.filter((scan) => scan.deployment_decision === "REJECTED").length;
  const approvalRate = recentScans.length > 0 ? Math.round((approvedScans / recentScans.length) * 100) : 0;
  const latestScan = recentScans[0] ?? null;
  const latestScanCompleted = latestScan?.status === "COMPLETED" || Boolean(latestScan?.completed_at);
  const latestScanFailed = latestScan?.status === "FAILED" || Boolean(latestScan?.failed_at);
  const latestScanUploads = new Set((summary?.latest_uploads ?? []).filter((report) => report.scan_id === latestScan?.scan_id).map((report) => report.tool_name));
  const secretsCount = (summary?.most_recent_findings ?? []).filter((finding) => finding.tool === "gitleaks").length;
  const codeSmellsCount = (summary?.most_recent_findings ?? []).filter((finding) => finding.tool === "sonarqube").length;
  const latestImageAvailable = Boolean(latestScan?.image_full_path || latestScan?.image_name);
  const dockerImageStatus = latestImageAvailable && latestScan?.deployment_decision === "APPROVED" ? "READY" : latestScanCompleted || latestScanFailed || latestScan?.deployment_decision === "REJECTED" ? "MISSING" : "PENDING";
  const securitySummary = [
    { label: "Critical Vulnerabilities", value: String(summary?.critical_findings ?? 0), icon: ShieldAlert, tone: (summary?.critical_findings ?? 0) > 0 ? "critical" : "good", href: activeProjectFindingsHref },
    { label: "High Vulnerabilities", value: String(summary?.high_findings ?? 0), icon: AlertTriangle, tone: (summary?.high_findings ?? 0) > 0 ? "warning" : "good", href: activeProjectFindingsHref },
    { label: "Secrets", value: String(secretsCount), icon: LockKeyhole, tone: secretsCount > 0 ? "critical" : "good", href: activeProjectFindingsHref },
    { label: "Code Smells", value: String(codeSmellsCount), icon: Search, tone: codeSmellsCount > 0 ? "warning" : "good", href: activeProjectFindingsHref },
    { label: "Quality Gate", value: latestScan?.sonar_quality_gate ?? "UNKNOWN", icon: CheckCircle2, tone: latestScan?.sonar_quality_gate === "OK" ? "good" : "critical", href: activeProjectFindingsHref },
    { label: "Docker Image Status", value: dockerImageStatus, icon: Package, tone: dockerImageStatus === "READY" ? "good" : dockerImageStatus === "MISSING" ? "critical" : "warning", href: activeProjectFindingsHref },
  ];
  const gateResults = [
    { label: "GitLeaks", passed: latestScanUploads.has("gitleaks") && (summary?.critical_findings ?? 0) === 0 },
    { label: "Trivy Filesystem", passed: latestScanUploads.has("trivy-fs") && (summary?.critical_findings ?? 0) === 0 },
    { label: "SonarQube Quality Gate", passed: latestScan?.sonar_quality_gate === "OK" },
    { label: "Docker Image Scan", passed: latestScanUploads.has("trivy-image") && (summary?.critical_findings ?? 0) === 0 },
    { label: "Policy Engine", passed: summary?.latest_approval_status === "APPROVED" },
  ];
  const slackNotifications = (summary?.recent_notifications ?? []).filter((item) => item.notification_type === "SLACK");
  const emailNotifications = (summary?.recent_notifications ?? []).filter((item) => item.notification_type === "EMAIL");
  const deliveryPercent = (items: typeof slackNotifications) => items.length > 0 ? Math.round((items.filter((item) => item.status === "SENT").length / items.length) * 100) : 100;
  const notificationDurations = (summary?.recent_notifications ?? [])
    .filter((item) => item.sent_at)
    .map((item) => Math.max(0, (new Date(item.sent_at as string).getTime() - new Date(item.created_at).getTime()) / 1000));
  const averageDelivery = notificationDurations.length > 0 ? notificationDurations.reduce((sum, item) => sum + item, 0) / notificationDurations.length : 0;
  const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const notificationWeek = weekdayLabels.map((label, weekday) => ({
    label,
    count: (summary?.recent_notifications ?? []).filter((item) => new Date(item.created_at).getDay() === weekday).length,
  }));
  const maxNotificationDay = Math.max(1, ...notificationWeek.map((item) => item.count));
  const repositoryName = latestScan?.repository_url.split("github.com/")[1] ?? latestScan?.repository_url ?? "No repository yet";
  type PipelineState = "passed" | "failed" | "pending";
  const latestDecision = latestScan?.deployment_decision ?? summary?.latest_approval_status ?? "PENDING";
  const latestRejected = latestDecision === "REJECTED" || latestScanFailed;
  const latestApproved = latestDecision === "APPROVED";
  const recentFindings = summary?.most_recent_findings ?? [];
  const hasBlockingFinding = (tool: string, severities = ["CRITICAL", "HIGH"]) => recentFindings.some((finding) => finding.tool === tool && severities.includes(finding.severity.toUpperCase()));
  const hasSecretsBlock = recentFindings.some((finding) => finding.tool === "gitleaks");
  const hasTrivyFsBlock = hasBlockingFinding("trivy-fs") || (latestRejected && (summary?.critical_findings ?? 0) + (summary?.high_findings ?? 0) > 0);
  const hasTrivyImageBlock = hasBlockingFinding("trivy-image");
  const hasSonarBlock = Boolean(latestScan && latestScan.sonar_quality_gate !== "OK" && (latestScanUploads.has("sonarqube") || latestScanCompleted || latestScanFailed));
  const stageStateFromUpload = (tool: string, blocked = false): PipelineState => {
    if (!latestScan) return "pending";
    if (latestScanUploads.has(tool)) return blocked ? "failed" : "passed";
    return latestScanCompleted || latestScanFailed || latestRejected ? "failed" : "pending";
  };
  const dockerStageState: PipelineState = !latestScan
    ? "pending"
    : latestRejected
      ? "failed"
      : latestApproved && latestImageAvailable
        ? "passed"
        : latestScanCompleted || latestScanFailed
          ? "failed"
          : "pending";
  const imageStageState: PipelineState = !latestScan
    ? "pending"
    : latestRejected
      ? "failed"
      : latestApproved && latestScanUploads.has("trivy-image") && !hasTrivyImageBlock
        ? "passed"
        : latestScanCompleted || latestScanFailed
          ? "failed"
          : "pending";
  const pipelineStages: Array<{ label: string; state: PipelineState }> = [
    { label: "GitLeaks", state: stageStateFromUpload("gitleaks", hasSecretsBlock) },
    { label: "Trivy", state: stageStateFromUpload("trivy-fs", hasTrivyFsBlock) },
    { label: "Sonar", state: !latestScan ? "pending" : latestScan.sonar_quality_gate === "OK" ? "passed" : hasSonarBlock ? "failed" : "pending" },
    { label: "Docker", state: dockerStageState },
    { label: "Image", state: imageStageState },
    { label: "Report", state: !latestScan ? "pending" : latestScan.report_generation_at || (summary?.recent_reports ?? []).some((report) => report.scan_id === latestScan.scan_id) ? "passed" : latestScanCompleted || latestScanFailed || latestRejected ? "failed" : "pending" },
    { label: "Notification", state: !latestScan ? "pending" : latestScan.notification_sent_at ? "passed" : latestScanCompleted || latestScanFailed || latestRejected ? "failed" : "pending" },
    { label: "Done", state: !latestScan ? "pending" : latestApproved && latestScanCompleted ? "passed" : latestRejected ? "failed" : "pending" },
  ];
  const passedPipelineStages = pipelineStages.filter((stage) => stage.state === "passed").length;
  const failedPipelineStages = pipelineStages.some((stage) => stage.state === "failed");

  useEffect(() => {
    let active = true;
    if (!latestScan?.scan_id) {
      setAiInsights(null);
      return () => { active = false; };
    }
    setAiLoading(true);
    getAiInsights(latestScan.scan_id)
      .then((data) => { if (active) setAiInsights(data); })
      .catch(() => { if (active) setAiInsights(null); })
      .finally(() => { if (active) setAiLoading(false); });
    return () => { active = false; };
  }, [latestScan?.scan_id]);

  const gateCriteria = [
    {
      id: "securegate",
      label: "Pass Or Fail Criteria",
      description: "SecureGate approves only when no blocking findings exist and score is at least 80.",
      href: "/docs"
    },
    {
      id: "gitleaks",
      label: "GitLeaks Secrets",
      description: "GitLeaks fails on detected secrets.",
      href: "https://github.com/gitleaks/gitleaks"
    },
    {
      id: "trivy",
      label: "Trivy Vulnerabilities",
      description: "Trivy fails on critical vulnerabilities and reduces score for high or medium findings.",
      href: "https://trivy.dev/latest/docs/"
    },
    {
      id: "sonarqube",
      label: "SonarQube Quality Gate",
      description: "SonarQube fails when the quality gate is not OK.",
      href: "https://docs.sonarsource.com/sonarqube-cloud/"
    }
  ];

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>SecureGate AI Executive Dashboard</h1>
          <p className="dashboard-subtitle">Continuous Security Validation for CI/CD Pipelines.</p>
          <nav className="dashboard-start-nav" aria-label="Quick start navigation">
            <Link to="/projects">Register A Project</Link>
            <Link to="/manifests">Add SecureGate-AI To Pipeline</Link>
            <Link to="/how-to-use">Start Scanning</Link>
          </nav>
          {summary?.active_project_name && <div className="active-project-chip" title={summary.active_repository_url ?? undefined}><span className="active-project-label">Showing Analysis For</span><strong>{summary.active_project_name}</strong>{summary.active_project_key && <span>{summary.active_project_key}</span>}</div>}
        </div>
        <span className="status-pill">Auto-refresh {lastUpdated ? formatDate(lastUpdated.toISOString()) : "starting"}</span>
      </header>

      <div className="stat-grid sprint4-stats dashboard-stat-grid">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return <article className={`stat-card ${stat.label === "Security Score" ? "score-stat-card" : ""}`} key={stat.label}>
            {stat.label === "Security Score" ? <div className="score-meter"><div className="score-icon-panel"><Icon size={28} /></div><strong className="stat-value">{stat.value}</strong></div> : <><Icon size={22} /><strong className={`stat-value ${stat.riskCount ? securityCountClass(stat.value) : ""}`}>{stat.value}</strong></>}
            <span>{stat.label}</span>
          </article>;
        })}
      </div>

      {loading && <p className="muted">Loading dashboard...</p>}
      {error && <p className="error-text">{error}</p>}

      {summary && <>

        <div className="section-band scan-modern-card dashboard-pipeline-status-card">
          <div className="scan-card-header">
            <span className="scan-card-icon"><Activity size={22} /></span>
            <div>
              <h2>Pipeline Status Timeline</h2>
              <p>Latest pipeline stages across scans, reports, notifications, and deployment readiness.</p>
            </div>
            <span className={`scan-card-count ${failedPipelineStages ? "failed" : ""}`}>{passedPipelineStages}/{pipelineStages.length} Stages Passed</span>
          </div>
          <div className="dashboard-pipeline-timeline" aria-label="Pipeline status timeline">
            {pipelineStages.map((stage, index) => {
              const Icon = stage.state === "passed" ? CircleCheck : stage.state === "failed" ? CircleX : Circle;
              return <div className={`pipeline-status-stage ${stage.state}`} key={stage.label}>
                <span className="pipeline-status-node"><Icon size={18} /></span>
                <strong>{stage.label}</strong>
                <small>{stage.state.toUpperCase()} · {String(index + 1).padStart(2, "0")}</small>
              </div>;
            })}
          </div>
        </div>

        <div className="dashboard-grid">
          <div className="section-band">
            <div className="section-title"><div><h2>Scan Score Trends</h2><span>Green Shows Security Score; Red Shows Remaining Vulnerability Risk</span></div><TrendingUp size={20} /></div>
            {summary.score_trend.length === 0 ? <p className="muted">No evaluated scans yet.</p> : (
              <>
                <div className="trend-chart" aria-label="Security score trend">
                  {scoreTrendPage.items.map((point) => <Link to={`/scans/${point.scan_id}`} className="trend-column" key={point.scan_id} title={`${point.scan_id}: ${point.score}%`}>
                    <span>{point.score}%</span><div className="trend-track"><i style={{ height: trendHeight(point.score) }} /></div><small>{point.scan_id.slice(-4)}</small>
                  </Link>)}
                </div>
                <PaginationControls page={scoreTrendPage.page} totalPages={scoreTrendPage.totalPages} onPageChange={setScorePage} />
              </>
            )}
          </div>

          <div className="section-band">
            <div className="section-title"><div><h2>Vulnerability Trend</h2><span>Critical, High, Medium, Low, Pending, And Resolved Findings</span></div><ShieldAlert size={20} /></div>
            <div className="legend-row color-legend vulnerability-legend" aria-label="Vulnerability trend color meaning">
              <span className="legend-critical">Critical</span>
              <span className="legend-high">High</span>
              <span className="legend-medium">Medium</span>
              <span className="legend-low">Low</span>
              <span className="legend-pending">Pending</span>
              <span className="legend-approved">Resolved</span>
            </div>
            {summary.vulnerability_trend.length === 0 ? <p className="muted">No vulnerability trend data yet.</p> : (
              <>
                <div className="vulnerability-trend">
                  {vulnerabilityTrendPage.items.map((point) => {
                    const total = point.CRITICAL + point.HIGH + point.MEDIUM + point.LOW;
                    const maxTotal = maxTrendTotal(vulnerabilityTrendPage.items);
                    return <Link to={`/scans/${point.scan_id}`} className="vulnerability-trend-row" key={point.scan_id}>
                      <span>{point.scan_id.slice(-4)}</span>
                      <div className="stacked-bar" title={total === 0 ? "No vulnerabilities found" : `${total} findings`}>
                        {total === 0 ? <i className="resolved" style={{ width: "100%" }} /> : <>
                          <i className="critical" style={{ width: `${(point.CRITICAL / maxTotal) * 100}%` }} />
                          <i className="high" style={{ width: `${(point.HIGH / maxTotal) * 100}%` }} />
                          <i className="medium" style={{ width: `${(point.MEDIUM / maxTotal) * 100}%` }} />
                          <i className="low" style={{ width: `${(point.LOW / maxTotal) * 100}%` }} />
                        </>}
                      </div>
                      <small className="pr-summary">
                        P {point.PENDING} / R {point.RESOLVED}
                        <span>{point.PENDING} vulnerabilities are still pending<br />{point.RESOLVED} vulnerabilities have been resolved</span>
                      </small>
                    </Link>;
                  })}
                </div>
                <PaginationControls page={vulnerabilityTrendPage.page} totalPages={vulnerabilityTrendPage.totalPages} onPageChange={setVulnerabilityPage} />
              </>
            )}
          </div>

          <div className="section-band soc-analytics-panel">
            <div className="section-title">
              <div><h2>Executive KPIs</h2><span>Enterprise SOC Overview For Security, Deployments, And Notifications</span></div>
              <BarChart3 size={20} />
            </div>

            <div className="soc-card-grid" aria-label="SecureGate AI SOC analytics preview">
              <article className="soc-card security-posture-card">
                <div className="soc-card-header"><span className="soc-card-icon">🛡️</span><div><h3>Security Posture</h3><p>Overall risk and findings health</p></div><span className="soc-menu">⋮</span></div>
                <div className="soc-split-row">
                  <div className="soc-score-box">
                    <span>Security Score</span>
                    <div className="soc-gauge" style={{ background: `conic-gradient(#259b49 0deg ${(latestScore ?? 0) * 1.8}deg, #e7eee9 ${(latestScore ?? 0) * 1.8}deg 180deg)` }}>
                      <strong>{latestScore ?? "--"}</strong><small>/100</small>
                    </div>
                    <b className={latestScore != null && latestScore >= 80 ? "soc-good" : "soc-critical"}>● {scoreTone}</b>
                  </div>
                  <div className="soc-mini-panel">
                    <span>Trend (7D)</span>
                    <strong className={scoreDelta >= 0 ? "soc-good" : "soc-critical"}>{scoreDelta >= 0 ? "↗" : "↘"} {Math.abs(scoreDelta)}%</strong>
                    <small>{scoreDelta >= 0 ? "Improving" : "Needs review"}</small>
                    <div className="soc-sparkline">{scoreTrend.slice(-7).map((point) => <i key={point.scan_id} style={{ height: `${Math.max(12, point.score)}%` }} />)}</div>
                  </div>
                </div>
                <div className="soc-breakdown findings-matrix" aria-label="Open findings by severity">
                  <div className="findings-matrix-copy">
                    <strong>Open Findings By Severity</strong>
                    <small><span className={securityCountClass(totalSeverityFindings)}>{totalSeverityFindings}</span> open issue{totalSeverityFindings === 1 ? "" : "s"} in the latest scan. Click the ring to view finding details.</small>
                    <span><i className="critical-dot" />Critical Blockers <b className={securityCountClass(summary.critical_findings)}>{summary.critical_findings}</b></span>
                    <span><i className="high-dot" />High Risk Findings <b className={securityCountClass(summary.high_findings)}>{summary.high_findings}</b></span>
                    <span><i className="medium-dot" />Medium Findings <b className={securityCountClass(mediumFindings)}>{mediumFindings}</b></span>
                    <span><i className="low-dot" />Low Findings <b className={securityCountClass(lowFindings)}>{lowFindings}</b></span>
                  </div>
                  <Link to={activeProjectFindingsHref} className="soc-donut findings-link" title="Open project findings across scans" style={{ background: conicGradient([
                    { value: summary.critical_findings, color: "#9b1c1c" },
                    { value: summary.high_findings, color: "#e1791a" },
                    { value: mediumFindings, color: "#d9b34c" },
                    { value: lowFindings, color: "#5d8b38" },
                  ]) }}><div><strong className={securityCountClass(totalSeverityFindings)}>{totalSeverityFindings}</strong><span>Open Findings</span></div></Link>
                </div>
                <div className="soc-mini-stats"><span><b>{scoreTrend.length}</b>Scans (7D)</span><span><b>{summary.total_projects}</b>Projects</span><span><b>{summary.total_projects}</b>Repositories</span></div>
              </article>

              <article className="soc-card deployment-status-card">
                <div className="soc-card-header"><span className="soc-card-icon">🚀</span><div><h3>Deployment Status</h3><p>Scan outcomes and policy decisions</p></div><span className="soc-menu">⋮</span></div>
                <div className="soc-split-row">
                  <div className="soc-decision-box">
                    <span>Latest Decision</span>
                    <strong className={summary.latest_approval_status === "APPROVED" ? "soc-good" : summary.latest_approval_status === "REJECTED" ? "soc-critical" : "soc-warning"}>{summary.latest_approval_status === "APPROVED" ? "✅" : summary.latest_approval_status === "REJECTED" ? "🚫" : "⏳"} {summary.latest_approval_status}</strong>
                    <small>{summary.latest_approval_status === "APPROVED" ? "Security gates passed" : "Security gates need attention"}</small>
                    <em>{latestScan ? formatDate(latestScan.received_at) : "No scan yet"}</em>
                  </div>
                  <div className="soc-mini-panel">
                    <span>Trend (7D)</span>
                    <strong className={approvalRate >= 80 ? "soc-good" : approvalRate >= 50 ? "soc-warning" : "soc-critical"}>{approvalRate}%</strong>
                    <small>Approval rate</small>
                    <div className="soc-sparkline">{recentScans.slice(0, 7).reverse().map((scan) => <i key={scan.scan_id} style={{ height: scan.deployment_decision === "APPROVED" ? "88%" : "32%" }} />)}</div>
                  </div>
                </div>
                <div className="soc-gates">
                  <strong>Gate Results (Latest Scan)</strong>
                  {gateResults.map((gate) => <span key={gate.label}><b>{gate.passed ? "✅" : "⚠️"} {gate.label}</b><em className={gate.passed ? "soc-good" : "soc-warning"}>{gate.passed ? "Passed" : "Review"}</em></span>)}
                </div>
                <div className="soc-mini-stats"><span><b>{approvedScans}</b>Passed</span><span><b>{rejectedScans}</b>Failed</span><span><b>{rejectedScans}</b>Blocked Deployments</span></div>
              </article>

              <article className="soc-card notification-health-card">
                <div className="soc-card-header"><span className="soc-card-icon">🔔</span><div><h3>Notification Health</h3><p>Slack and email delivery status</p></div><span className="soc-menu">⋮</span></div>
                <div className="soc-channel-grid">
                  <div className="soc-channel"><strong>💬 Slack</strong><b>{deliveryPercent(slackNotifications)}%</b><span>Delivered</span><small>{slackNotifications.filter((item) => item.status === "SENT").length} Sent | {slackNotifications.filter((item) => item.status === "FAILED").length} Failed</small></div>
                  <div className="soc-channel"><strong>✉️ Email</strong><b>{deliveryPercent(emailNotifications)}%</b><span>Delivered</span><small>{emailNotifications.filter((item) => item.status === "SENT").length} Sent | {emailNotifications.filter((item) => item.status === "FAILED").length} Failed</small></div>
                  <div className="soc-channel"><strong>🚨 Failed</strong><b>{notificationCounts.FAILED ?? 0}</b><span>{(notificationCounts.FAILED ?? 0) === 0 ? "All good" : "Needs review"}</span></div>
                  <div className="soc-channel"><strong>⏱️ Avg Delivery</strong><b>{averageDelivery > 0 ? `${averageDelivery.toFixed(1)}s` : "--"}</b><span>Recent events</span></div>
                </div>
                <div className="soc-events-chart"><div><strong>Total Events (7D)</strong><b>{summary.recent_notifications.length}</b></div><div className="soc-bars">{notificationWeek.map((item) => <span key={item.label}><i style={{ height: `${Math.max(10, (item.count / maxNotificationDay) * 100)}%` }} /><small>{item.label}</small></span>)}</div></div>
              </article>
            </div>

            <div className="soc-latest-strip">
              <span>🤖 <b>Last Scan</b><strong>{latestScan ? formatDate(latestScan.received_at) : "No scan yet"}</strong></span>
              <span>🐙 <b>Repository</b><strong>{repositoryName}</strong></span>
              <span>🌿 <b>Branch</b><strong>{latestScan?.branch ?? "--"}</strong></span>
              <span>🔖 <b>Commit</b><strong>{latestScan?.commit_sha.slice(0, 7) ?? "--"}</strong></span>
              {latestScan ? <a href={reportDownloadUrl(latestScan.scan_id, "pdf")} className="soc-report-link" download>View Full Report →</a> : <span className="soc-report-link disabled">View Full Report →</span>}
            </div>
          </div>


        </div>

          <div className="section-band scan-modern-card security-summary-card">
            <div className="scan-card-header">
              <span className="scan-card-icon"><ShieldAlert size={22} /></span>
              <div><h2>Security Summary</h2><p>Latest repository health signals from secrets, vulnerabilities, code quality, and image readiness.</p></div>
              <Link className="scan-card-action" to={activeProjectFindingsHref}>Project Findings <ChevronRight size={15} /></Link>
            </div>
            <div className="security-summary-grid">
              {securitySummary.map((item) => {
                const Icon = item.icon;
                return <Link to={item.href} className={`security-summary-item ${item.tone}`} key={item.label}>
                  <span><Icon size={20} /></span>
                  <div><strong className={["Critical Vulnerabilities", "High Vulnerabilities", "Secrets", "Code Smells"].includes(item.label) ? securityCountClass(item.value) : ""}>{item.value}</strong><small>{item.label}</small></div>
                </Link>;
              })}
            </div>
          </div>

        <div className="section-band scan-modern-card ai-summary-reserved-card ai-live-summary-card">
          <div className="scan-card-header">
            <span className="scan-card-icon"><Activity size={22} /></span>
            <div>
              <h2>AI Summary</h2>
              <p>Local Gemma guidance from the latest scan context, with rule-based fallback when Ollama is unavailable.</p>
            </div>
            <span className={`scan-card-count ${aiInsights?.ollama_status === "UNAVAILABLE" ? "failed" : ""}`}>{aiLoading ? "Loading" : aiInsights?.ollama_status ?? "Waiting"}</span>
          </div>
          {latestScan ? <div className="ai-summary-content">
            <div>
              <strong>{aiInsights?.overall_risk ?? "Pending"} Risk</strong>
              <p>{aiInsights?.executive_summary ?? "AI insight will appear after the latest scan context is loaded."}</p>
              <small>{aiInsights?.ai_readiness ?? "Waiting for AI readiness assessment."}</small>
            </div>
            <ul>
              {(aiInsights?.top_recommendations ?? ["Review SecureGate findings and tool reports for remediation details."]).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
            </ul>
            <div className="ai-report-actions">
              <a className="green-pill-button" href={aiSummaryReportUrl(latestScan.scan_id)}>AI Summary PDF</a>
              <a className="green-pill-button" href={aiRemediationPlanUrl(latestScan.scan_id)}>Remediation PDF</a>
            </div>
          </div> : <p className="ai-summary-placeholder">Run a scan to generate AI deployment insight and remediation guidance.</p>}
        </div>

        <div className="dashboard-grid dashboard-modern-grid">
          <div className="section-band scan-modern-card dashboard-reports-card">
            <div className="scan-card-header">
              <span className="scan-card-icon"><FileText size={23} /></span>
              <div><h2>Recent Reports</h2><p>{summary.recent_reports.length} Master Reports</p></div>
              <Link className="scan-card-action" to="/reports">View All Reports <ChevronRight size={15} /></Link>
            </div>
            <div className="modern-list-panel dashboard-report-list">
              {summary.recent_reports.length === 0 ? <p className="muted">No master reports generated yet.</p> : reportsPage.items.map((report) => (
                <div className="dashboard-report-row" key={`${report.scan_id}-${report.created_at}`}>
                  <span className="tool-avatar"><FileText size={21} /></span>
                  <div><strong>{report.project_name}</strong><span>{report.scan_id} • {formatDate(report.created_at)}</span></div>
                  <div className="upload-report-buttons modern-file-buttons">
                    <a href={reportDownloadUrl(report.scan_id, "pdf")} title="Download PDF"><FileText size={13} /> PDF</a>
                    <a href={reportDownloadUrl(report.scan_id, "docx")} title="Download DOCX"><FileText size={13} /> DOCX</a>
                    <a href={reportDownloadUrl(report.scan_id, "json")} title="Open JSON"><FileText size={13} /> JSON</a>
                  </div>
                </div>
              ))}
            </div>
            <PaginationControls page={reportsPage.page} totalPages={reportsPage.totalPages} onPageChange={setReportPage} />
          </div>

          <div className="section-band scan-modern-card dashboard-uploads-card">
            <div className="scan-card-header">
              <span className="scan-card-icon"><CloudUpload size={23} /></span>
              <div><h2>Latest Uploads</h2><p>{summary.latest_uploads.length} Tool Reports</p></div>
              <Link className="scan-card-action" to="/reports">View All Uploads <ChevronRight size={15} /></Link>
            </div>
            <div className="modern-list-panel dashboard-upload-list">
              {summary.latest_uploads.length === 0 ? <p className="muted">No reports uploaded yet.</p> : uploadsPage.items.map((report) => {
                const Icon = dashboardToolIcon(report.tool_name);
                return (
                  <div className="dashboard-upload-row" key={`${report.tool_name}-${report.uploaded_at}`}>
                    <span className="tool-avatar"><Icon size={21} /></span>
                    <div className="dashboard-upload-copy">
                      <strong className="tool-name-trigger">{formatToolName(report.tool_name)}</strong>
                      <span className="tool-hover-note" role="tooltip">{toolInfo[report.tool_name] ?? "Uploaded security tool report."}</span>
                      <small>{formatDate(report.uploaded_at)}</small>
                      <code>{report.file_path ?? "Report path unavailable"}</code>
                    </div>
                    <span className="modern-status-pill uploaded"><i />UPLOADED</span>
                    {report.scan_id && <div className="upload-report-buttons modern-file-buttons">
                      <a href={toolReportDownloadUrl(report.scan_id, report.tool_name)} title={`Open ${formatToolName(report.tool_name)} raw JSON report`}><FileText size={13} /> JSON</a>
                      <a href={toolReportPdfUrl(report.scan_id, report.tool_name)} title={`Open ${formatToolName(report.tool_name)} readable PDF report`}><FileText size={13} /> PDF</a>
                    </div>}
                  </div>
                );
              })}
            </div>
            <PaginationControls page={uploadsPage.page} totalPages={uploadsPage.totalPages} onPageChange={setUploadPage} />
          </div>
        </div>

        <div className="section-band scan-modern-card dashboard-scans-card">
          <div className="scan-card-header scan-section-title">
            <span className="scan-card-icon"><ShieldAlert size={23} /></span>
            <div><h2>Current And Recent Vulnerability Scans</h2><p>Lifecycle, Scores, And Deployment Decisions</p></div>
            <span className="scan-card-count">{summary.recent_scans.length} Scans</span>
          </div>
          <div className="gate-criteria" aria-label="Vulnerability scan pass or fail criteria">
            {gateCriteria.map((criterion) => <a
              className={`criteria-tab ${activeCriterion === criterion.id ? "active" : ""}`}
              href={criterion.href}
              key={criterion.id}
              onClick={() => setActiveCriterion(criterion.id)}
              rel={criterion.href.startsWith("http") ? "noreferrer" : undefined}
              target={criterion.href.startsWith("http") ? "_blank" : "_blank"}
              title="Read Official Documentation"
            >
              <strong>{criterion.label}</strong>
              <span>{criterion.description}</span>
            </a>)}
          </div>
          {summary.recent_scans.length === 0 ? <p className="muted">No vulnerability scans received yet.</p> : <div className="modern-scan-table">
            <div className="modern-scan-row modern-scan-head"><span>Scan</span><span>Project</span><span>Status</span><span>Score</span><span>Decision</span><span>Received</span></div>
            {scansPage.items.map((scan) => {
              const Icon = decisionIcon(scan.deployment_decision);
              return <Link className="modern-scan-row linked-row" to={`/scans/${scan.scan_id}`} key={scan.scan_id}>
                <span className="scan-id-cell"><i><Icon size={16} /></i><b>{scan.scan_id}</b></span>
                <span className="truncate">{scan.project_name}</span>
                <span><b className={`modern-status-pill ${scan.status.toLowerCase()}`}>{scan.status}</b></span>
                <span>{scan.security_score ?? "--"}</span>
                <span><b className={`decision-chip ${scan.deployment_decision.toLowerCase()}`}>{scan.deployment_decision}</b></span>
                <span>{formatDate(scan.received_at)}</span>
              </Link>;
            })}
            <PaginationControls page={scansPage.page} totalPages={scansPage.totalPages} onPageChange={setScanPage} />
          </div>}
        </div>
      </>}
    </section>
  );
}
