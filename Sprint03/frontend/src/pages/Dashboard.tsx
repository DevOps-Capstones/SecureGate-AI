import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, FileText, Gauge, ShieldAlert, TrendingUp } from "lucide-react";
import { getDashboardSummary, reportDownloadUrl } from "../api/scans";
import type { DashboardSummary } from "../types/scans";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardSummary().then(setSummary).catch((err: Error) => setError(err.message)).finally(() => setLoading(false));
  }, []);

  const stats = [
    { label: "Security score", value: summary?.latest_security_score == null ? "--" : `${summary.latest_security_score}`, icon: Gauge },
    { label: "Approval status", value: summary?.latest_approval_status ?? "PENDING", icon: CheckCircle2 },
    { label: "Critical findings", value: String(summary?.critical_findings ?? 0), icon: ShieldAlert },
    { label: "High findings", value: String(summary?.high_findings ?? 0), icon: AlertTriangle }
  ];

  return (
    <section className="page">
      <header className="page-header">
        <div><p className="eyebrow">Sprint 3</p><h1>Security decision dashboard</h1></div>
        <span className="status-pill">Decision engine active</span>
      </header>

      <div className="stat-grid">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return <article className="stat-card" key={stat.label}><Icon size={22} /><strong className="stat-value">{stat.value}</strong><span>{stat.label}</span></article>;
        })}
      </div>

      {loading && <p className="muted">Loading dashboard...</p>}
      {error && <p className="error-text">{error}</p>}

      {summary && <>
        <div className="dashboard-grid">
          <div className="section-band">
            <div className="section-title"><div><h2>Score trend preview</h2><span>Latest evaluated scans</span></div><TrendingUp size={20} /></div>
            {summary.score_trend.length === 0 ? <p className="muted">No evaluated scans yet.</p> : (
              <div className="trend-chart" aria-label="Security score trend">
                {summary.score_trend.map((point) => <Link to={`/scans/${point.scan_id}`} className="trend-column" key={point.scan_id} title={`${point.scan_id}: ${point.score}`}>
                  <span>{point.score}</span><div style={{ height: `${Math.max(point.score, 4)}%` }} /><small>{point.scan_id.slice(-4)}</small>
                </Link>)}
              </div>
            )}
          </div>

          <div className="section-band">
            <div className="section-title"><div><h2>Recent reports</h2><span>{summary.recent_reports.length} master reports</span></div><FileText size={20} /></div>
            {summary.recent_reports.length === 0 ? <p className="muted">No master reports generated yet.</p> : summary.recent_reports.slice(0, 5).map((report) => (
              <div className="compact-row report-compact" key={`${report.scan_id}-${report.created_at}`}>
                <div><strong>{report.project_name}</strong><span>{formatDate(report.created_at)}</span></div>
                <div className="icon-actions">
                  <a href={reportDownloadUrl(report.scan_id, "pdf")} title="Download PDF" aria-label="Download PDF">PDF</a>
                  <a href={reportDownloadUrl(report.scan_id, "docx")} title="Download DOCX" aria-label="Download DOCX">DOCX</a>
                  <a href={reportDownloadUrl(report.scan_id, "json")} title="Open JSON" aria-label="Open JSON">JSON</a>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="section-band">
          <div className="section-title"><h2>Recent scans</h2><span>Scores and deployment decisions</span></div>
          {summary.recent_scans.length === 0 ? <p className="muted">No scans received yet.</p> : <div className="table">
            <div className="table-row table-head decision-row"><span>Scan ID</span><span>Project</span><span>Score</span><span>Decision</span><span>Received</span></div>
            {summary.recent_scans.map((scan) => <Link className="table-row decision-row linked-row" to={`/scans/${scan.scan_id}`} key={scan.scan_id}>
              <span>{scan.scan_id}</span><span className="truncate">{scan.project_name}</span><span>{scan.security_score ?? "--"}</span>
              <span className={`status-text ${scan.deployment_decision.toLowerCase()}`}>{scan.deployment_decision}</span><span>{formatDate(scan.received_at)}</span>
            </Link>)}
          </div>}
        </div>
      </>}
    </section>
  );
}
