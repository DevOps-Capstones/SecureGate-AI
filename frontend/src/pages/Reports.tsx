import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Download, FileText, Filter, Gauge, Image, ShieldAlert, SlidersHorizontal, Trash2 } from "lucide-react";
import { aiRemediationPlanUrl, aiSummaryReportUrl, deleteReport, listReports, reportDownloadUrl } from "../api/scans";
import type { ReportFilters, ReportHistoryItem } from "../types/scans";

function securityCountClass(value: number | string | null | undefined) {
  return Number(value ?? 0) > 0 ? "security-count nonzero" : "security-count";
}

function reportDecisionIcon(decision: string) {
  if (decision === "APPROVED") return CheckCircle2;
  if (decision === "REJECTED") return AlertTriangle;
  return Gauge;
}

function imageLabel(report: ReportHistoryItem) {
  return report.image_full_path ?? (report.image_name ? `${report.image_name}${report.image_tag ? `:${report.image_tag}` : ""}` : "N/A");
}

const initialFilters: ReportFilters = { project: "", branch: "", image: "", decision: "", severity: "", date_from: "", date_to: "", score_min: "", score_max: "" };

const reportFormatOrder = ["PDF", "DOCX", "JSON", "MASTER", "AI_SUMMARY", "AI_SUMMARY_PDF", "AI_REMEDIATION", "AI_REMEDIATION_PDF"];

interface ReportHistoryGroup extends ReportHistoryItem {
  formats: string[];
  latest_created_at: string;
}

function groupReportsByScan(reports: ReportHistoryItem[]): ReportHistoryGroup[] {
  const grouped = new Map<string, ReportHistoryGroup>();
  reports.forEach((report) => {
    const normalizedType = report.report_type.toUpperCase();
    const existing = grouped.get(report.scan_id);
    if (!existing) {
      grouped.set(report.scan_id, {
        ...report,
        report_type: "MASTER",
        formats: [normalizedType],
        latest_created_at: report.created_at,
      });
      return;
    }
    if (!existing.formats.includes(normalizedType)) existing.formats.push(normalizedType);
    if (new Date(report.created_at).getTime() > new Date(existing.latest_created_at).getTime()) {
      existing.latest_created_at = report.created_at;
    }
  });
  return Array.from(grouped.values())
    .map((report) => ({
      ...report,
      formats: report.formats.sort((a, b) => reportFormatOrder.indexOf(a) - reportFormatOrder.indexOf(b)),
    }))
    .sort((a, b) => new Date(b.latest_created_at).getTime() - new Date(a.latest_created_at).getTime());
}

export function Reports() {
  const [filters, setFilters] = useState<ReportFilters>(initialFilters);
  const [reports, setReports] = useState<ReportHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  function load(activeFilters: ReportFilters) {
    setError(null);
    const min = activeFilters.score_min === "" ? null : Number(activeFilters.score_min);
    const max = activeFilters.score_max === "" ? null : Number(activeFilters.score_max);
    if ((min !== null && (Number.isNaN(min) || min < 0 || min > 100)) || (max !== null && (Number.isNaN(max) || max < 0 || max > 100))) {
      setError("Score filters must be between 0 and 100.");
      return;
    }
    if (min !== null && max !== null && min > max) {
      setError("Min Score cannot be greater than Max Score.");
      return;
    }
    listReports(activeFilters).then(setReports).catch((err: Error) => setError(err.message));
  }

  useEffect(() => { load(initialFilters); }, []);

  const groupedReports = groupReportsByScan(reports);

  async function handleDelete(report: ReportHistoryGroup) {
    const typed = window.prompt(`Type DELETE REPORT ${report.scan_id} to delete this generated report package (${report.formats.join(" / ")}).`);
    if (typed !== `DELETE REPORT ${report.scan_id}`) return;
    setError(null);
    try {
      const results = await Promise.allSettled(report.formats.map((format) => deleteReport(report.scan_id, format)));
      const deletedAny = results.some((result) => result.status === "fulfilled");
      if (!deletedAny) throw new Error("Report not found or already deleted.");
      load(filters);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete report.");
    }
  }

  return <section className="page">
    <header className="page-header"><div><p className="eyebrow">Last 12 Months</p><h1>Report History</h1></div></header>

    <form className="filter-bar reports-filter-card scan-modern-card" onSubmit={(event) => { event.preventDefault(); load(filters); }}>
      <div className="scan-card-header reports-filter-header">
        <span className="scan-card-icon"><SlidersHorizontal size={22} /></span>
        <div>
          <h2>Report Filters</h2>
          <p>Filter reports by project, image, branch, date, decision, score, and vulnerability severity.</p>
        </div>
      </div>
      <label>Project<input value={filters.project} onChange={(event) => setFilters({ ...filters, project: event.target.value })} /></label>
      <label>Branch<input value={filters.branch} onChange={(event) => setFilters({ ...filters, branch: event.target.value })} /></label>
      <label>Image<input value={filters.image} onChange={(event) => setFilters({ ...filters, image: event.target.value })} placeholder="dockerhub-user/repo:tag" /></label>
      <label>Decision<select value={filters.decision} onChange={(event) => setFilters({ ...filters, decision: event.target.value })}><option value="">All</option><option>APPROVED</option><option>REJECTED</option><option>PENDING</option></select></label>
      <label>Severity<select value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}><option value="">All</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label>
      <label>From<input type="date" value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} /></label>
      <label>To<input type="date" value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} /></label>
      <label>Min Score<input type="number" min="0" max="100" value={filters.score_min} onChange={(event) => setFilters({ ...filters, score_min: event.target.value })} /></label>
      <label>Max Score<input type="number" min="0" max="100" value={filters.score_max} onChange={(event) => setFilters({ ...filters, score_max: event.target.value })} /></label>
      <div className="reports-filter-actions">
        <button type="submit"><Filter size={17} /> Apply</button>
        <button type="button" className="secondary-button" onClick={() => { setFilters(initialFilters); load(initialFilters); }}>Reset</button>
      </div>
    </form>
    {error && <p className="error-text">{error}</p>}

    <div className="section-band scan-modern-card reports-history-card">
      <div className="scan-card-header">
        <span className="scan-card-icon"><FileText size={22} /></span>
        <div>
          <h2>Generated Reports</h2>
          <p>Download master reports, review scan decisions, or delete a specific generated report.</p>
        </div>
        <span className="scan-card-count">{groupedReports.length} Results</span>
      </div>
      {groupedReports.length === 0 ? <p className="muted">No reports match these filters.</p> : <div className="reports-modern-list">
        {groupedReports.map((report) => {
          const DecisionIcon = reportDecisionIcon(report.decision);
          return <div className="reports-modern-row" key={report.scan_id}>
            <span className="report-avatar"><FileText size={19} /></span>
            <div className="report-primary-copy">
              <strong>{report.project_name}</strong>
            </div>
            <div className="report-image-copy">
              <Image size={15} />
              <span className="truncate">{imageLabel(report)}</span>
            </div>
            <span className="report-score-pill"><Gauge size={14} /> {report.security_score ?? "--"}</span>
            <span className={`decision-chip ${report.decision.toLowerCase()}`}><DecisionIcon size={14} /> {report.decision}</span>
            <span className="severity-summary report-severity-chip"><ShieldAlert size={14} /> C <b className={securityCountClass(report.critical_count)}>{report.critical_count}</b> / H <b className={securityCountClass(report.high_count)}>{report.high_count}</b><span><b className={securityCountClass(report.critical_count)}>{report.critical_count}</b> critical vulnerabilities<br /><b className={securityCountClass(report.high_count)}>{report.high_count}</b> high vulnerabilities</span></span>
            <div className="icon-actions reports-export-actions"><a href={reportDownloadUrl(report.scan_id, "pdf")} title="Download Master PDF"><Download size={15} /> PDF</a><a href={reportDownloadUrl(report.scan_id, "docx")} title="Download Master DOCX">DOCX</a><a href={reportDownloadUrl(report.scan_id, "json")} title="Open Master JSON">JSON</a><a href={aiSummaryReportUrl(report.scan_id)} title="Download AI Summary PDF">AI Summary</a><a href={aiRemediationPlanUrl(report.scan_id)} title="Download AI Remediation Plan PDF">AI Plan</a><button className="mini-danger" type="button" title="Delete Report Entry" onClick={() => handleDelete(report)}><Trash2 size={14} /> Delete</button></div>
          </div>;
        })}
      </div>}
    </div>
  </section>;
}
