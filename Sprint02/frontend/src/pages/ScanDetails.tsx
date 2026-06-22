import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getScan } from "../api/scans";
import type { Finding, ScanDetails } from "../types/scans";

function FindingTable({ title, findings }: { title: string; findings: Finding[] }) {
  return (
    <div className="section-band">
      <div className="section-title">
        <h2>{title}</h2>
        <span>{findings.length} findings</span>
      </div>
      {findings.length === 0 ? (
        <p className="muted">No findings detected.</p>
      ) : (
        <div className="table">
          <div className="table-row table-head findings-row">
            <span>Severity</span>
            <span>ID</span>
            <span>Location</span>
            <span>Description</span>
          </div>
          {findings.map((finding, index) => (
            <div className="table-row findings-row" key={`${finding.scanner_type}-${finding.vulnerability_id}-${index}`}>
              <span className={`severity ${finding.severity.toLowerCase()}`}>{finding.severity}</span>
              <span>{finding.vulnerability_id ?? "N/A"}</span>
              <span className="truncate">
                {finding.file_path ?? "N/A"}
                {finding.line_number ? `:${finding.line_number}` : ""}
              </span>
              <span className="truncate">{finding.title ?? finding.description ?? "No description"}</span>
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

  if (loading) {
    return <p className="muted">Loading scan details...</p>;
  }

  if (error || !scan) {
    return <p className="error-text">{error ?? "Scan not found."}</p>;
  }

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
          <span>Repository</span>
          <strong className="truncate">{scan.repository_url}</strong>
          <span>Status</span>
          <strong className={`status-text ${scan.status.toLowerCase()}`}>{scan.status}</strong>
          <span>Deployment Approval</span>
          <strong>{scan.deployment_approved ? "Approved" : "Blocked"}</strong>
          <span>Critical</span>
          <strong>{scan.critical_count}</strong>
          <span>High</span>
          <strong>{scan.high_count}</strong>
          <span>Medium</span>
          <strong>{scan.medium_count}</strong>
          <span>Secrets</span>
          <strong>{scan.secrets_count}</strong>
        </div>
      </div>

      <FindingTable title="GitLeaks Results" findings={scan.gitleaks_findings} />
      <FindingTable title="Trivy Filesystem Results" findings={scan.trivy_findings} />
    </section>
  );
}
