import { useEffect, useState } from "react";
import { Download, Filter } from "lucide-react";
import { listReports, reportDownloadUrl } from "../api/scans";
import type { ReportFilters, ReportHistoryItem } from "../types/scans";

const initialFilters: ReportFilters = { project: "", branch: "", decision: "", severity: "", date_from: "", date_to: "" };

export function Reports() {
  const [filters, setFilters] = useState<ReportFilters>(initialFilters);
  const [reports, setReports] = useState<ReportHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  function load(activeFilters: ReportFilters) {
    setError(null);
    listReports(activeFilters).then(setReports).catch((err: Error) => setError(err.message));
  }

  useEffect(() => { load(initialFilters); }, []);

  return <section className="page">
    <header className="page-header"><div><p className="eyebrow">Last 12 months</p><h1>Report history</h1></div></header>
    <form className="filter-bar" onSubmit={(event) => { event.preventDefault(); load(filters); }}>
      <label>Project<input value={filters.project} onChange={(event) => setFilters({ ...filters, project: event.target.value })} /></label>
      <label>Branch<input value={filters.branch} onChange={(event) => setFilters({ ...filters, branch: event.target.value })} /></label>
      <label>Decision<select value={filters.decision} onChange={(event) => setFilters({ ...filters, decision: event.target.value })}><option value="">All</option><option>APPROVED</option><option>REJECTED</option><option>PENDING</option></select></label>
      <label>Severity<select value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}><option value="">All</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label>
      <label>From<input type="date" value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} /></label>
      <label>To<input type="date" value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} /></label>
      <button type="submit"><Filter size={17} /> Apply</button>
    </form>
    {error && <p className="error-text">{error}</p>}
    <div className="section-band">
      <div className="section-title"><h2>Generated reports</h2><span>{reports.length} results</span></div>
      {reports.length === 0 ? <p className="muted">No reports match these filters.</p> : <div className="table">
        <div className="table-row table-head report-row"><span>Project</span><span>Branch</span><span>Score</span><span>Decision</span><span>Severity</span><span>Exports</span></div>
        {reports.map((report) => <div className="table-row report-row" key={`${report.scan_id}-${report.report_type}-${report.created_at}`}>
          <span className="truncate">{report.project_name}</span><span>{report.branch}</span><span>{report.security_score ?? "--"}</span>
          <span className={`status-text ${report.decision.toLowerCase()}`}>{report.decision}</span><span>C {report.critical_count} / H {report.high_count}</span>
          <div className="icon-actions"><a href={reportDownloadUrl(report.scan_id, "pdf")} title="Download PDF"><Download size={15} /> PDF</a><a href={reportDownloadUrl(report.scan_id, "docx")} title="Download DOCX">DOCX</a><a href={reportDownloadUrl(report.scan_id, "json")} title="Open JSON">JSON</a></div>
        </div>)}
      </div>}
    </div>
  </section>;
}
