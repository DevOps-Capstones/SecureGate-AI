import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Clock3, FolderKanban } from "lucide-react";
import { getDashboardSummary } from "../api/scans";
import type { DashboardSummary } from "../types/scans";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const criticalFindings = summary?.most_recent_findings.filter((finding) => finding.severity === "CRITICAL").length ?? 0;
  const stats = [
    { label: "Total projects", value: String(summary?.total_projects ?? 0), icon: FolderKanban },
    { label: "Total scans", value: String(summary?.total_scans ?? 0), icon: CheckCircle2 },
    { label: "Latest uploads", value: String(summary?.latest_uploads.length ?? 0), icon: Clock3 },
    { label: "Recent critical", value: String(criticalFindings), icon: AlertTriangle }
  ];

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Sprint 2</p>
          <h1>Report ingestion dashboard</h1>
        </div>
        <span className="status-pill">GitHub Actions ready</span>
      </header>

      <div className="stat-grid">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <article className="stat-card" key={stat.label}>
              <Icon size={22} />
              <strong>{stat.value}</strong>
              <span>{stat.label}</span>
            </article>
          );
        })}
      </div>

      {loading && <p className="muted">Loading dashboard...</p>}
      {error && <p className="error-text">{error}</p>}

      {summary && (
        <>
          <div className="section-band">
            <div className="section-title">
              <h2>Recent scans</h2>
              <span>Received from CI pipelines</span>
            </div>
            {summary.recent_scans.length === 0 ? <p className="muted">No scans received yet.</p> : (
              <div className="table">
                <div className="table-row table-head recent-scans-row">
                  <span>Scan ID</span>
                  <span>Project</span>
                  <span>Status</span>
                  <span>Received</span>
                </div>
                {summary.recent_scans.map((scan) => (
                  <Link className="table-row recent-scans-row linked-row" to={`/scans/${scan.scan_id}`} key={scan.scan_id}>
                    <span>{scan.scan_id}</span>
                    <span className="truncate">{scan.project_name}</span>
                    <span className={`status-text ${scan.status.toLowerCase()}`}>{scan.status}</span>
                    <span>{formatDate(scan.received_at)}</span>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="dashboard-grid">
            <div className="section-band">
              <div className="section-title">
                <h2>Latest uploads</h2>
                <span>{summary.latest_uploads.length} reports</span>
              </div>
              {summary.latest_uploads.length === 0 ? <p className="muted">No reports uploaded yet.</p> : summary.latest_uploads.map((report) => (
                <div className="compact-row" key={`${report.tool_name}-${report.uploaded_at}`}>
                  <strong>{report.tool_name}</strong>
                  <span>{formatDate(report.uploaded_at)}</span>
                </div>
              ))}
            </div>

            <div className="section-band">
              <div className="section-title">
                <h2>Most recent findings</h2>
                <span>{summary.most_recent_findings.length} findings</span>
              </div>
              {summary.most_recent_findings.length === 0 ? <p className="muted">No findings normalized yet.</p> : summary.most_recent_findings.map((finding, index) => (
                <div className="compact-row" key={`${finding.tool}-${finding.title}-${index}`}>
                  <strong className={`severity ${finding.severity.toLowerCase()}`}>{finding.severity}</strong>
                  <span className="truncate">{finding.title}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
