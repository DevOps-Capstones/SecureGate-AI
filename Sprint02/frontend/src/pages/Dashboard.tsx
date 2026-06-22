import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, AlertTriangle, CheckCircle2, Clock3 } from "lucide-react";
import { listScans } from "../api/scans";
import type { ScanSummary } from "../types/scans";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function Dashboard() {
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listScans(10)
      .then(setScans)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const totals = useMemo(() => {
    return scans.reduce(
      (acc, scan) => ({
        critical: acc.critical + scan.critical_count,
        high: acc.high + scan.high_count,
        secrets: acc.secrets + scan.secrets_count,
        approved: acc.approved + (scan.deployment_approved ? 1 : 0)
      }),
      { critical: 0, high: 0, secrets: 0, approved: 0 }
    );
  }, [scans]);

  const stats = [
    { label: "Recent scans", value: scans.length.toString(), icon: Activity },
    { label: "Approved", value: totals.approved.toString(), icon: CheckCircle2 },
    { label: "Critical vulns", value: totals.critical.toString(), icon: AlertTriangle },
    { label: "Secrets", value: totals.secrets.toString(), icon: Clock3 }
  ];

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Sprint 2</p>
          <h1>Automated scan orchestration</h1>
        </div>
        <span className="status-pill">API connected</span>
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

      <div className="section-band">
        <div className="section-title">
          <h2>Recent scans</h2>
          <span>Live backend data</span>
        </div>
        {loading && <p className="muted">Loading scans...</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && !error && scans.length === 0 && <p className="muted">No scans have been submitted yet.</p>}
        {scans.length > 0 && (
          <div className="table">
            <div className="table-row table-head recent-scans-row">
              <span>Scan ID</span>
              <span>Repository</span>
              <span>Status</span>
              <span>Date</span>
            </div>
            {scans.map((scan) => (
              <Link className="table-row recent-scans-row linked-row" to={`/scans/${scan.scan_id}`} key={scan.scan_id}>
                <span>{scan.scan_id}</span>
                <span className="truncate">{scan.repository_url}</span>
                <span className={`status-text ${scan.status.toLowerCase()}`}>{scan.status}</span>
                <span>{formatDate(scan.started_at)}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
