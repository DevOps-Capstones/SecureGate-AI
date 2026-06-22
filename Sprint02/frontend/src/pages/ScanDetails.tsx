import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getScan } from "../api/scans";
import type { Finding, ScanDetails } from "../types/scans";

function FindingTable({ findings }: { findings: Finding[] }) {
  return (
    <div className="section-band">
      <div className="section-title">
        <h2>Normalized findings</h2>
        <span>{findings.length} findings</span>
      </div>
      {findings.length === 0 ? <p className="muted">No findings normalized yet.</p> : (
        <div className="table">
          <div className="table-row table-head findings-row">
            <span>Tool</span>
            <span>Severity</span>
            <span>File</span>
            <span>Title</span>
          </div>
          {findings.map((finding, index) => (
            <div className="table-row findings-row" key={`${finding.tool}-${finding.title}-${index}`}>
              <span>{finding.source_tool}</span>
              <span className={`severity ${finding.severity.toLowerCase()}`}>{finding.severity}</span>
              <span className="truncate">{finding.file ?? "N/A"}</span>
              <span className="truncate">{finding.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ScanDetailsPage() {
  const { scanId } = useParams();
  const [scan, setScan] = useState<ScanDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;
    getScan(scanId)
      .then(setScan)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [scanId]);

  if (loading) return <p className="muted">Loading scan details...</p>;
  if (error || !scan) return <p className="error-text">{error ?? "Scan not found."}</p>;

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Scan details</p>
          <h1>{scan.scan_id}</h1>
        </div>
        <Link className="status-pill" to="/">Back to dashboard</Link>
      </header>

      <div className="section-band">
        <div className="summary-grid">
          <span>Project</span>
          <strong>{scan.project_name}</strong>
          <span>Repository</span>
          <strong className="truncate">{scan.repository_url}</strong>
          <span>Branch</span>
          <strong>{scan.branch}</strong>
          <span>Commit SHA</span>
          <strong>{scan.commit_sha}</strong>
          <span>Status</span>
          <strong className={`status-text ${scan.status.toLowerCase()}`}>{scan.status}</strong>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="section-band">
          <div className="section-title">
            <h2>Uploaded reports</h2>
            <span>{scan.uploaded_reports.length} tools</span>
          </div>
          {scan.uploaded_reports.length === 0 ? <p className="muted">No tool reports uploaded yet.</p> : scan.uploaded_reports.map((report) => (
            <div className="compact-row" key={`${report.tool_name}-${report.uploaded_at}`}>
              <strong>{report.tool_name}</strong>
              <span className={`status-text ${report.status.toLowerCase()}`}>{report.status}</span>
            </div>
          ))}
        </div>

        <div className="section-band">
          <div className="section-title">
            <h2>Finding counts</h2>
            <span>By severity</span>
          </div>
          {Object.keys(scan.finding_counts).length === 0 ? <p className="muted">No findings counted yet.</p> : Object.entries(scan.finding_counts).map(([severity, count]) => (
            <div className="compact-row" key={severity}>
              <strong className={`severity ${severity.toLowerCase()}`}>{severity}</strong>
              <span>{count}</span>
            </div>
          ))}
        </div>
      </div>

      <FindingTable findings={scan.findings} />
    </section>
  );
}
