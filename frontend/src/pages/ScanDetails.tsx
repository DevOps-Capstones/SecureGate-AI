import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Activity, BarChart3, Bell, Bot, CheckCircle2, ChevronLeft, ChevronRight, Circle, CircleX, CloudUpload, Download, FileCheck2, FilePlus2, FileText, Flag, FolderSearch, Gauge, Github, Lightbulb, Mail, Package, Play, PlayCircle, Search, Settings, ShieldCheck, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { aiSummaryReportUrl, generateMasterReports, getMasterReportStatus, getScan, reportDownloadUrl, toolReportDownloadUrl, toolReportPdfUrl, triggerProjectScan } from "../api/scans";
import type { Finding, ScanDetails } from "../types/scans";

function repositoryHref(repositoryUrl: string) {
  return /^https?:\/\//i.test(repositoryUrl) ? repositoryUrl : `https://${repositoryUrl}`;
}

function toolLabel(value: string) {
  const labels: Record<string, string> = {
    gitleaks: "GitLeaks",
    semgrep: "Semgrep",
    "trivy-fs": "Trivy FS",
    sonarqube: "SonarQube",
    "unit-tests": "Unit Tests",
    "trivy-image": "Trivy Image",
  };
  return labels[value] ?? value;
}

function notificationRecipientLabel(type: string, recipient: string) {
  if (type.toUpperCase() === "SLACK" && recipient.startsWith("http")) return "Slack Channel Configured";
  return recipient;
}

function toolKey(finding: Finding) {
  const source = finding.tool || finding.source_tool || "";
  const normalized = source.toLowerCase().replace(/\s+/g, "-");
  if (normalized.includes("trivy") && normalized.includes("image")) return "trivy-image";
  if (normalized.includes("trivy")) return "trivy-fs";
  if (normalized.includes("sonar")) return "sonarqube";
  if (normalized.includes("gitleaks")) return "gitleaks";
  if (normalized.includes("semgrep")) return "semgrep";
  if (normalized.includes("unit")) return "unit-tests";
  return normalized;
}

function formatTimelineValue(timestamp: string | null, fallback: string) {
  return timestamp ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(timestamp)) : fallback;
}

function lifecycleIcon(label: string): LucideIcon {
  const normalized = label.toLowerCase();
  if (normalized.includes("created")) return FilePlus2;
  if (normalized.includes("uploaded")) return CloudUpload;
  if (normalized.includes("scoring")) return BarChart3;
  if (normalized.includes("generated")) return FileText;
  if (normalized.includes("notification")) return Bell;
  if (normalized.includes("completed")) return ShieldCheck;
  return FileCheck2;
}

function securityIcon(label: string): LucideIcon {
  const normalized = label.toLowerCase();
  if (normalized.includes("pipeline")) return Play;
  if (normalized.includes("gitleaks")) return Search;
  if (normalized.includes("filesystem")) return FolderSearch;
  if (normalized.includes("sonarqube")) return Gauge;
  if (normalized.includes("quality")) return ShieldCheck;
  if (normalized.includes("docker") || normalized.includes("image")) return Package;
  if (normalized.includes("score")) return ShieldCheck;
  if (normalized.includes("recommendation")) return Lightbulb;
  if (normalized.includes("master")) return FileText;
  if (normalized.includes("slack")) return Bell;
  if (normalized.includes("email")) return Mail;
  if (normalized.includes("completed")) return Flag;
  return CheckCircle2;
}

function toolIcon(value: string): LucideIcon {
  if (value === "gitleaks") return Github;
  if (value === "semgrep") return Search;
  if (value === "trivy-fs" || value === "trivy-image") return Package;
  if (value === "sonarqube") return Activity;
  if (value === "unit-tests") return ShieldCheck;
  return FileText;
}

function notificationIcon(type: string): LucideIcon {
  return type.toUpperCase() === "EMAIL" ? Mail : Bell;
}

function auditIcon(action: string): LucideIcon {
  const normalized = action.toLowerCase();
  if (normalized.includes("scan")) return Download;
  if (normalized.includes("processing")) return Settings;
  if (normalized.includes("scoring")) return ShieldCheck;
  if (normalized.includes("report")) return CloudUpload;
  if (normalized.includes("failed")) return Flag;
  return Activity;
}

function formatShortTimeAgo(value: string) {
  const diffMs = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const severityOrder = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"];

const severityColors: Record<string, string> = {
  CRITICAL: "#7b0d07",
  HIGH: "#c4372e",
  MEDIUM: "#d67835",
  LOW: "#c49422",
  UNKNOWN: "#6f7d78",
};

function securityCountClass(value: number | string | null | undefined) {
  return Number(value ?? 0) > 0 ? "security-count nonzero" : "security-count";
}

function severityLabel(severity: string) {
  const labels: Record<string, string> = {
    CRITICAL: "Critical",
    HIGH: "High",
    MEDIUM: "Medium",
    LOW: "Low",
    UNKNOWN: "Unknown",
  };
  return labels[severity] ?? severity.charAt(0).toUpperCase() + severity.slice(1).toLowerCase();
}

function polarToCartesian(centerX: number, centerY: number, radius: number, angleInDegrees: number) {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180;
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  };
}

function describePieSlice(centerX: number, centerY: number, radius: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(centerX, centerY, radius, endAngle);
  const end = polarToCartesian(centerX, centerY, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

  return [
    `M ${centerX} ${centerY}`,
    `L ${start.x} ${start.y}`,
    `A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`,
    "Z",
  ].join(" ");
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

function FindingTable({ findings, scanId }: { findings: Finding[]; scanId: string }) {
  const [findingPage, setFindingPage] = useState(0);
  const findingsPage = pagedItems(findings, findingPage, 8);

  useEffect(() => {
    setFindingPage(0);
  }, [scanId]);

  return (
    <div id="normalized-findings" className="section-band scan-modern-card normalized-findings-card">
      <div className="scan-card-header">
        <span className="scan-card-icon"><ShieldCheck size={23} /></span>
        <div><h2 title="Findings from each uploaded tool converted into one common SecureGate AI format.">Normalized Findings</h2><p>Unified SecureGate AI finding format</p></div>
        <span className="scan-card-count"><span className={securityCountClass(findings.length)}>{findings.length}</span> Findings</span>
      </div>
      {findings.length === 0 ? <p className="muted">No findings normalized yet.</p> : (
        <>
          <div className="modern-finding-table">
            <div className="modern-finding-row modern-finding-head">
              <span>Tool</span><span>Severity</span><span>File</span><span>Finding</span>
            </div>
            {findingsPage.items.map((finding, index) => {
              const Icon = toolIcon(toolKey(finding));
              return (
                <div className="modern-finding-row" key={`${finding.tool}-${finding.title}-${findingsPage.page}-${index}`}>
                  <span className="finding-tool-cell"><i><Icon size={16} /></i><a href={toolReportPdfUrl(scanId, toolKey(finding))}>{finding.source_tool}</a></span>
                  <span><b className={`severity-dot-label ${finding.severity.toLowerCase()}`}>{finding.severity}</b></span>
                  <span className="truncate">{finding.file ?? "N/A"}</span>
                  <span className="truncate"><a title="Open related tool PDF" href={toolReportPdfUrl(scanId, toolKey(finding))}>{finding.title}</a></span>
                </div>
              );
            })}
          </div>
          <PaginationControls page={findingsPage.page} totalPages={findingsPage.totalPages} onPageChange={setFindingPage} />
        </>
      )}
    </div>
  );
}

export function ScanDetailsPage() {
  const { scanId } = useParams();
  const [scan, setScan] = useState<ScanDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [auditPage, setAuditPage] = useState(0);
  const [triggering, setTriggering] = useState(false);
  const [triggerMessage, setTriggerMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;
    setAuditPage(0);
    getScan(scanId)
      .then(setScan)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [scanId]);

  if (loading) return <p className="muted">Loading scan details...</p>;
  if (error || !scan) return <p className="error-text">{error ?? "Scan not found."}</p>;

  const currentScan = scan;
  const uploadedToolSet = new Set(currentScan.uploaded_reports.map((report) => report.tool_name));
  type TimelineStageStatus = "done" | "failed" | "pending";
  const scanRejected = currentScan.deployment_decision === "REJECTED";
  const pipelineFailed = [currentScan.status, currentScan.pipeline_status].some((value) => ["FAILED", "ERROR", "CANCELLED"].includes((value ?? "").toUpperCase()));
  const scanFinished = ["COMPLETED", "FAILED"].includes((currentScan.status ?? "").toUpperCase());
  const hasFindingForTool = (tool: string, severities?: string[]) => currentScan.findings.some((finding) => {
    if (toolKey(finding) !== tool) return false;
    return !severities || severities.includes((finding.severity ?? "").toUpperCase());
  });
  const uploadedStatus = (tool: string, failWhen = false): TimelineStageStatus => {
    if (uploadedToolSet.has(tool)) return failWhen ? "failed" : "done";
    return scanFinished || pipelineFailed ? "failed" : "pending";
  };
  const notificationStatus = (type: string): TimelineStageStatus => {
    const item = currentScan.notifications.find((notification) => notification.notification_type === type);
    if (!item) return scanFinished || pipelineFailed ? "failed" : "pending";
    return item.status === "SENT" ? "done" : "failed";
  };
  const imageAvailable = Boolean(currentScan.image_full_path || currentScan.image_name);
  const scanApproved = currentScan.deployment_decision === "APPROVED";
  const dockerBuildStatus: TimelineStageStatus = scanRejected
    ? "failed"
    : scanApproved && imageAvailable
      ? "done"
      : (scanFinished || pipelineFailed ? "failed" : "pending");
  const imageScanStatus: TimelineStageStatus = scanRejected
    ? "failed"
    : scanApproved
      ? uploadedStatus("trivy-image", hasFindingForTool("trivy-image", ["CRITICAL", "HIGH"]))
      : (scanFinished || pipelineFailed ? "failed" : "pending");
  const securityTimeline: { label: string; status: TimelineStageStatus }[] = [
    { label: "Pipeline Started", status: currentScan.pipeline_run_id || currentScan.received_at ? "done" : "pending" },
    { label: "GitLeaks", status: uploadedStatus("gitleaks", hasFindingForTool("gitleaks")) },
    { label: "Filesystem Scan", status: uploadedStatus("trivy-fs", hasFindingForTool("trivy-fs", ["CRITICAL", "HIGH"])) },
    { label: "SonarQube", status: uploadedStatus("sonarqube") },
    { label: "Quality Gate", status: currentScan.sonar_quality_gate === "OK" ? "done" : currentScan.sonar_quality_gate === "UNKNOWN" && !scanFinished ? "pending" : "failed" },
    { label: "Docker Build", status: dockerBuildStatus },
    { label: "Image Scan", status: imageScanStatus },
    { label: "Security Score", status: currentScan.security_score !== null ? "done" : scanFinished ? "failed" : "pending" },
    { label: "Recommendations", status: currentScan.security_score !== null ? "done" : scanFinished ? "failed" : "pending" },
    { label: "Master Report", status: currentScan.report_generation_at ? "done" : scanFinished ? "failed" : "pending" },
    { label: "Slack Notification", status: notificationStatus("SLACK") },
    { label: "Email Notification", status: notificationStatus("EMAIL") },
    { label: "Completed", status: scanRejected || pipelineFailed || currentScan.status === "FAILED" ? "failed" : currentScan.status === "COMPLETED" ? "done" : "pending" },
  ];
  const completedSecuritySteps = securityTimeline.filter((event) => event.status === "done").length;
  const failedSecuritySteps = securityTimeline.filter((event) => event.status === "failed").length;
  const findingsBySeverity = Object.entries(currentScan.finding_counts)
    .map(([severity, count]) => {
      const normalizedSeverity = severity.toUpperCase();
      const tools = Array.from(new Set(currentScan.findings.filter((finding) => finding.severity === severity).map(toolKey))).filter(Boolean);
      return { severity: normalizedSeverity, count, tools };
    })
    .filter((item) => item.count > 0)
    .sort((a, b) => {
      const aOrder = severityOrder.includes(a.severity) ? severityOrder.indexOf(a.severity) : severityOrder.length;
      const bOrder = severityOrder.includes(b.severity) ? severityOrder.indexOf(b.severity) : severityOrder.length;
      const severityDiff = aOrder - bOrder;
      if (severityDiff !== 0) return severityDiff;
      return b.count - a.count;
    });
  const totalFindingsBySeverity = findingsBySeverity.reduce((sum, item) => sum + item.count, 0);
  let sliceCursor = 0;
  const severityPieSlices = findingsBySeverity.map((item) => {
    const startAngle = sliceCursor;
    const sliceSize = totalFindingsBySeverity > 0 ? (item.count / totalFindingsBySeverity) * 360 : 0;
    const endAngle = Math.min(sliceCursor + sliceSize, 359.999);
    sliceCursor += sliceSize;
    const midAngle = startAngle + sliceSize / 2;
    const lineStart = polarToCartesian(180, 122, 82, midAngle);
    const lineBend = polarToCartesian(180, 122, 112, midAngle);
    const labelX = lineBend.x >= 180 ? 318 : 42;
    const labelY = lineBend.y;
    const percent = totalFindingsBySeverity > 0 ? Math.round((item.count / totalFindingsBySeverity) * 100) : 0;
    return {
      ...item,
      color: severityColors[item.severity] ?? severityColors.UNKNOWN,
      endAngle,
      label: severityLabel(item.severity),
      labelAnchor: (lineBend.x >= 180 ? "start" : "end") as "start" | "end",
      labelX,
      labelY,
      lineBend,
      lineEnd: { x: lineBend.x >= 180 ? labelX - 12 : labelX + 12, y: labelY },
      lineStart,
      path: describePieSlice(180, 122, 82, startAngle, endAngle),
      percent,
    };
  });
  const auditLogPage = pagedItems(scan.audit_logs, auditPage, 6);

  async function handleTriggerScan() {
    if (!currentScan.project_key) {
      setTriggerMessage("Open the project page to trigger a new scan after the first project record is created.");
      return;
    }
    setTriggering(true);
    setTriggerMessage(null);
    try {
      const result = await triggerProjectScan(currentScan.project_key, currentScan.branch || "main");
      setTriggerMessage(`${result.message} Branch: ${result.branch}.`);
    } catch (err) {
      setTriggerMessage(err instanceof Error ? err.message : "Unable to trigger GitHub Actions workflow.");
    } finally {
      setTriggering(false);
    }
  }

  async function handleMasterDownload(format: "pdf" | "docx" | "json") {
    try {
      const reportStatus = await getMasterReportStatus(currentScan.scan_id);
      if (!reportStatus.has_master_report) {
        const shouldGenerate = window.confirm("No master report was generated for this scan. Would you like SecureGate AI to generate it now?");
        if (!shouldGenerate) return;
        await generateMasterReports(currentScan.scan_id);
      }
      window.location.href = reportDownloadUrl(currentScan.scan_id, format);
    } catch (err) {
      const shouldGenerate = window.confirm("No master report was found or it could not be opened. Would you like SecureGate AI to generate it now?");
      if (!shouldGenerate) return;
      try {
        await generateMasterReports(currentScan.scan_id);
        window.location.href = reportDownloadUrl(currentScan.scan_id, format);
      } catch (nextErr) {
        setError(nextErr instanceof Error ? nextErr.message : "Unable to generate master report.");
      }
    }
  }

  return (
    <section className="page scan-details-page">
      <header className="page-header workspace-header scan-details-header">
        <div>
          <p className="eyebrow">Scan Details</p>
          <h1>{scan.scan_id}</h1>
        </div>
        <div className="workspace-header-actions">
          <button className="secondary-button workspace-action-trigger" type="button" onClick={handleTriggerScan} disabled={triggering}><PlayCircle size={15} /> {triggering ? "Triggering..." : "Trigger Scan"}</button>
          <Link className="inline-action workspace-action-download" to="#" onClick={(event) => { event.preventDefault(); handleMasterDownload("pdf"); }}><Download size={15} /> Download Report</Link>
          <Link className="inline-action workspace-action-analytics" to={scan.project_key ? `/projects/${scan.project_key}/analytics` : "/security-analytics"}><BarChart3 size={15} /> View Analytics</Link>
          <Link className="inline-action workspace-action-alerts" to="/alerts"><Bell size={15} /> View Alerts</Link>
          <Link className="inline-action workspace-action-remediation" to={`/remediation-plan?scan_id=${scan.scan_id}`}><Wrench size={15} /> Remediation Plan</Link>
          <a className="secondary-button workspace-action-ai" href={aiSummaryReportUrl(scan.scan_id)}><Bot size={15} /> AI Summary</a>
        </div>
      </header>

      {triggerMessage && <div className={`trigger-feedback ${triggerMessage.toLowerCase().includes("unable") || triggerMessage.toLowerCase().includes("error") ? "error" : "success"}`}>{triggerMessage}</div>}

      <div className="section-band">
        <div className="summary-grid">
          <span>Project</span>
          <strong>{scan.project_name}</strong>
          <span>Repository</span>
          <strong className="truncate"><a className="repo-link" href={repositoryHref(scan.repository_url)} target="_blank" rel="noreferrer">{scan.repository_url}</a></strong>
          <span>Docker Image Path</span>
          <strong className="truncate">{scan.image_full_path ?? "Not pushed yet"}</strong>
          <span>Branch</span>
          <strong>{scan.branch}</strong>
          <span>Commit SHA</span>
          <strong>{scan.commit_sha}</strong>
          <span>Status</span>
          <strong className={`status-text ${scan.status.toLowerCase()}`}>{scan.status}</strong>
          <span>Pipeline Run</span>
          <strong>{scan.pipeline_run_id ?? "N/A"}</strong>
          <span>Pipeline Status</span>
          <strong>{scan.pipeline_status ?? "N/A"}</strong>
          <span>Security Score</span>
          <strong>{scan.security_score ?? "Pending"}</strong>
          <span>Deployment Decision</span>
          <strong className={`status-text ${scan.deployment_decision.toLowerCase()}`}>{scan.deployment_decision}</strong>
          <span>SonarQube Gate</span>
          <strong className={`gate-status ${scan.sonar_quality_gate.toLowerCase()}`}>{scan.sonar_quality_gate}</strong>
        </div>
        <div className="download-bar">
          <button type="button" onClick={() => handleMasterDownload("pdf")}><Download size={16} /> PDF</button>
          <button type="button" onClick={() => handleMasterDownload("docx")}><Download size={16} /> DOCX</button>
          <button type="button" onClick={() => handleMasterDownload("json")}><Download size={16} /> JSON</button>
        </div>
      </div>

      <div className="section-band lifecycle-panel">
        <div className="timeline-panel-header">
          <span className="timeline-shield"><ShieldCheck size={25} /></span>
          <div><h2>Scan Lifecycle</h2><p>End-to-end lifecycle tracking of your security scan</p></div>
          <span className="timeline-panel-pill"><Activity size={15} /> Lifecycle Tracking</span>
        </div>
        <div className="scan-lifecycle-track">
          {scan.timeline.map((event, index) => {
            const Icon = lifecycleIcon(event.label);
            return (
              <div className={`lifecycle-stage ${event.status.toLowerCase()}`} key={event.label}>
                <div className="lifecycle-node-wrap">
                  <span className="lifecycle-node"><Icon size={26} /></span>
                  <span className="lifecycle-check"><CheckCircle2 size={16} /></span>
                </div>
                <strong>{String(index + 1).padStart(2, "0")}</strong>
                <b>{event.label}</b>
                <span>{formatTimelineValue(event.timestamp, event.status)}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="section-band pipeline-panel">
        <div className="timeline-panel-header">
          <span className="timeline-shield"><ShieldCheck size={25} /></span>
          <div><h2>Security Pipeline Timeline</h2><p>Scanner, report, and notification stages</p></div>
          <span className={`timeline-panel-pill ${failedSecuritySteps > 0 ? "failed" : ""}`}><CheckCircle2 size={15} /> {completedSecuritySteps} / {securityTimeline.length} Completed</span>
        </div>
        <div className="security-pipeline-track">
          {securityTimeline.map((event, index) => {
            const Icon = securityIcon(event.label);
            const StatusIcon = event.status === "failed" ? CircleX : event.status === "pending" ? Circle : CheckCircle2;
            return (
              <div className={`pipeline-stage ${event.status} ${event.label === "Completed" ? "final-stage" : ""}`} key={event.label}>
                {event.label !== "Completed" && <small>{String(index + 1).padStart(2, "0")}</small>}
                <Icon size={28} />
                <strong>{event.label === "Completed" ? "COMPLETED" : event.label}</strong>
                <span><StatusIcon size={15} /></span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="section-band scan-modern-card uploaded-reports-card">
          <div className="scan-card-header">
            <span className="scan-card-icon"><FileText size={23} /></span>
            <div><h2>Uploaded Reports</h2><p>{scan.uploaded_reports.length} Tools</p></div>
            <Link className="scan-card-action" to="/reports">View All Reports <ChevronRight size={15} /></Link>
          </div>
          <div className="modern-list-panel">
            {scan.uploaded_reports.length === 0 ? <p className="muted">No tool reports uploaded yet.</p> : scan.uploaded_reports.map((report) => {
              const Icon = toolIcon(report.tool_name);
              return (
                <div className="modern-report-row" key={`${report.tool_name}-${report.uploaded_at}`}>
                  <span className="tool-avatar"><Icon size={21} /></span>
                  <strong>{toolLabel(report.tool_name)}</strong>
                  <span className={`modern-status-pill ${report.status.toLowerCase()}`}><i />{report.status}</span>
                  <div className="upload-report-buttons modern-file-buttons">
                    {report.scan_id && <a href={toolReportDownloadUrl(report.scan_id, report.tool_name)}><FileText size={13} /> JSON</a>}
                    {report.scan_id && <a href={toolReportPdfUrl(report.scan_id, report.tool_name)}><FileText size={13} /> PDF</a>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="section-band scan-modern-card severity-pie-card modern-severity-card">
          <div className="scan-card-header">
            <span className="scan-card-icon"><ShieldCheck size={23} /></span>
            <div>
              <h2>Open Security Issues By Severity</h2>
              <p>Overall Code • Software Quality: Security • Slice By Severity</p>
            </div>
            <span className="scan-card-count"><span className={securityCountClass(totalFindingsBySeverity)}>{totalFindingsBySeverity}</span> Findings</span>
          </div>
          {severityPieSlices.length === 0 ? <p className="muted">No findings counted yet.</p> : (
            <div className="severity-pie-layout">
              <svg className="severity-pie-svg" viewBox="0 0 360 250" role="img" aria-label="Open security issues by severity">
                {severityPieSlices.map((slice) => (
                  <g className="severity-slice-group" key={slice.severity}>
                    <path className="severity-pie-slice" d={slice.path} fill={slice.color}>
                      <title>{`${slice.label}: ${slice.count} findings, ${slice.percent}%`}</title>
                    </path>
                    <polyline className="severity-callout-line" points={`${slice.lineStart.x},${slice.lineStart.y} ${slice.lineBend.x},${slice.lineBend.y} ${slice.lineEnd.x},${slice.lineEnd.y}`} stroke={slice.color} />
                    <text className="severity-callout-text" x={slice.labelX} y={slice.labelY - 5} textAnchor={slice.labelAnchor}>{slice.label}</text>
                    <text className="severity-callout-percent" x={slice.labelX} y={slice.labelY + 15} textAnchor={slice.labelAnchor}>{slice.percent}%</text>
                  </g>
                ))}
              </svg>
              <div className="severity-pie-legend" aria-label="Severity report links">
                {severityPieSlices.map((slice) => (
                  <div className="severity-pie-legend-item" key={`legend-${slice.severity}`}>
                    <span className="severity-pie-dot" style={{ backgroundColor: slice.color }} />
                    <div>
                      <strong>{slice.label}</strong>
                      <span><span className={securityCountClass(slice.count)}>{slice.count}</span> Findings</span>
                      <div className="severity-pie-tools">
                        {slice.tools.length === 0 ? <small>No tool link</small> : slice.tools.map((tool) => <a key={`${slice.severity}-${tool}`} href={toolReportPdfUrl(scan.scan_id, tool)}>{toolLabel(tool)}</a>)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="section-band scan-modern-card notifications-card">
          <div className="scan-card-header">
            <span className="scan-card-icon"><Bell size={23} /></span>
            <div><h2>Notifications</h2><p>{scan.notifications.length} Events</p></div>
            <Link className="scan-card-action" to="/alerts">View All <ChevronRight size={15} /></Link>
          </div>
          <div className="modern-list-panel notification-list-panel">
            {scan.notifications.length === 0 ? <p className="muted">No notification activity yet.</p> : scan.notifications.map((item) => {
              const Icon = notificationIcon(item.notification_type);
              return (
                <div className="modern-notification-row" key={`${item.notification_type}-${item.created_at}`}>
                  <span className="channel-avatar"><Icon size={23} /></span>
                  <div><strong>{item.notification_type}</strong><span>{notificationRecipientLabel(item.notification_type, item.recipient)}</span></div>
                  <span className={`modern-status-pill ${item.status.toLowerCase()}`}>{item.status}</span>
                  <small>{formatShortTimeAgo(item.created_at)}</small>
                  <i className={`delivery-dot ${item.status.toLowerCase()}`} />
                </div>
              );
            })}
          </div>
        </div>
        <div className="section-band scan-modern-card audit-history-card">
          <div className="scan-card-header">
            <span className="scan-card-icon"><FileText size={23} /></span>
            <div><h2>Audit History</h2><p>{scan.audit_logs.length} Records</p></div>
            <Link className="scan-card-action" to="/monitoring">View All <ChevronRight size={15} /></Link>
          </div>
          {scan.audit_logs.length === 0 ? <p className="muted">No audit records yet.</p> : (
            <>
              <div className="modern-audit-table">
                {auditLogPage.items.map((item) => {
                  const Icon = auditIcon(item.action);
                  return (
                    <div className="modern-audit-row" key={`${item.action}-${item.created_at}`} title={`${item.action}: ${item.message}`}>
                      <span className="audit-avatar"><Icon size={15} /></span>
                      <strong>{item.action}</strong>
                      <span className="audit-message">{item.message}</span>
                      <small>{formatShortTimeAgo(item.created_at)}</small>
                      <em>{item.actor}</em>
                    </div>
                  );
                })}
              </div>
              <PaginationControls page={auditLogPage.page} totalPages={auditLogPage.totalPages} onPageChange={setAuditPage} />
            </>
          )}
        </div>
      </div>

      <FindingTable findings={scan.findings} scanId={scan.scan_id} />
    </section>
  );
}
