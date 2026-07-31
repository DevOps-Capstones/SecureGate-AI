import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BarChart3, CheckCircle2, Gauge, GitBranch, ShieldAlert, TrendingUp, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { getHistoricalAnalytics } from "../api/scans";
import type { HistoricalAnalytics } from "../types/scans";

const ranges = [
  { value: "24h", label: "Last 24 Hours" },
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
  { value: "90d", label: "Last 90 Days" },
  { value: "12m", label: "Last 12 Months" },
];

type TrendRow = Record<string, number | string | null>;

function numberValue(row: TrendRow, key: string) {
  const value = row[key];
  if (typeof value === "number") return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? 0 : parsed;
  }
  return 0;
}

function labelValue(row: TrendRow, key: string) {
  const value = row[key];
  return value == null ? "N/A" : String(value);
}

function average(values: number[]) {
  return values.length ? Math.round(values.reduce((sum, item) => sum + item, 0) / values.length) : 0;
}

export function SecurityAnalytics() {
  const [range, setRange] = useState("30d");
  const [analytics, setAnalytics] = useState<HistoricalAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getHistoricalAnalytics(range)
      .then(setAnalytics)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [range]);

  const trend = analytics?.trend ?? [];
  const metrics = useMemo(() => {
    const totalScans = trend.reduce((sum, row) => sum + numberValue(row, "scans"), 0);
    const approved = trend.reduce((sum, row) => sum + numberValue(row, "approved"), 0);
    const rejected = trend.reduce((sum, row) => sum + numberValue(row, "rejected"), 0);
    const critical = trend.reduce((sum, row) => sum + numberValue(row, "critical"), 0);
    const high = trend.reduce((sum, row) => sum + numberValue(row, "high"), 0);
    const scores = trend.map((row) => numberValue(row, "average_score")).filter((score) => score > 0);
    const approvalRate = totalScans ? Math.round((approved / totalScans) * 100) : 0;
    return { totalScans, approved, rejected, critical, high, averageScore: average(scores), approvalRate };
  }, [trend]);

  const maxFindings = Math.max(1, ...trend.map((row) => numberValue(row, "critical") + numberValue(row, "high")));
  const maxScans = Math.max(1, ...trend.map((row) => numberValue(row, "scans")));
  const latest = trend[trend.length - 1] ?? null;
  const previous = trend[trend.length - 2] ?? latest;
  const scoreDelta = latest && previous ? numberValue(latest, "average_score") - numberValue(previous, "average_score") : 0;
  const kpis = [
    { label: "Total Scans", value: metrics.totalScans, helper: "Across selected range", icon: GitBranch, tone: "info" },
    { label: "Approval Rate", value: `${metrics.approvalRate}%`, helper: `${metrics.approved} Approved / ${metrics.rejected} Rejected`, icon: CheckCircle2, tone: metrics.approvalRate >= 80 ? "good" : "warning" },
    { label: "Average Score", value: `${metrics.averageScore}%`, helper: scoreDelta >= 0 ? `+${scoreDelta} From Previous Point` : `${scoreDelta} From Previous Point`, icon: Gauge, tone: metrics.averageScore >= 80 ? "good" : "critical" },
    { label: "Critical Findings", value: metrics.critical, helper: "Blocking production issues", icon: ShieldAlert, tone: metrics.critical > 0 ? "critical" : "good" },
    { label: "High Findings", value: metrics.high, helper: "Above risk threshold review", icon: AlertTriangle, tone: metrics.high > 0 ? "warning" : "good" },
  ];

  return <section className="page analytics-page">
    <header className="page-header monitoring-hero analytics-hero">
      <div>
        <p className="eyebrow">Historical Security Analytics</p>
        <h1>Security Analytics</h1>
        <p>Trend view for scan volume, deployment decisions, scores, and critical/high vulnerability movement.</p>
      </div>
      <span className={`monitoring-live-pill ${metrics.rejected > 0 || metrics.critical > 0 ? "critical" : "healthy"}`}><TrendingUp size={16} /> {metrics.rejected > 0 ? "Risk Review" : "Stable Trend"}</span>
    </header>

    <div className="analytics-range-card scan-modern-card">
      <div className="scan-card-header compact">
        <span className="scan-card-icon"><BarChart3 size={22} /></span>
        <div>
          <h2>Analytics Range</h2>
          <p>Choose a time window for historical security and deployment trend analysis.</p>
        </div>
      </div>
      <div className="analytics-range-tabs" role="tablist" aria-label="Analytics range">
        {ranges.map((item) => <button className={range === item.value ? "active" : ""} key={item.value} type="button" onClick={() => setRange(item.value)}>{item.label}</button>)}
      </div>
    </div>

    {error && <p className="error-text">{error}</p>}

    <div className="monitoring-telemetry-grid analytics-kpi-grid">
      {kpis.map((card) => {
        const Icon = card.icon;
        return <article className={`monitoring-metric-card ${card.tone}`} key={card.label}>
          <span className="monitoring-icon"><Icon size={21} /></span>
          <div><strong>{card.value}</strong><span>{card.label}</span><small>{card.helper}</small></div>
        </article>;
      })}
    </div>

    <section className="section-band scan-modern-card analytics-trend-card">
      <div className="scan-card-header">
        <span className="scan-card-icon"><TrendingUp size={22} /></span>
        <div>
          <h2>Security Trend</h2>
          <p>Critical and high vulnerability pressure compared with scan activity.</p>
        </div>
        <span className="scan-card-count">{trend.length} Data Points</span>
      </div>
      {loading ? <p className="muted">Loading analytics...</p> : trend.length === 0 ? <p className="muted">No analytics data found for this range.</p> : <div className="analytics-trend-list">
        {trend.map((row, index) => {
          const critical = numberValue(row, "critical");
          const high = numberValue(row, "high");
          const scans = numberValue(row, "scans");
          const findingsTotal = critical + high;
          return <article className="analytics-trend-row" key={`${labelValue(row, "date")}-${index}`}>
            <strong>{labelValue(row, "date")}</strong>
            <div className="analytics-bar-stack" title={`${critical} critical, ${high} high, ${scans} scans`}>
              <span className="critical" style={{ width: `${Math.max(critical / maxFindings * 100, critical ? 5 : 0)}%` }} />
              <span className="high" style={{ width: `${Math.max(high / maxFindings * 100, high ? 5 : 0)}%` }} />
              <i style={{ width: `${Math.max(scans / maxScans * 100, scans ? 5 : 0)}%` }} />
            </div>
            <small>C {critical} / H {high}</small>
            <small>{scans} Scans</small>
          </article>;
        })}
      </div>}
    </section>

    <section className="section-band scan-modern-card analytics-table-card">
      <div className="scan-card-header">
        <span className="scan-card-icon"><Gauge size={22} /></span>
        <div>
          <h2>Decision And Score History</h2>
          <p>Deployment outcome and average score by analytics bucket.</p>
        </div>
        <Link className="scan-card-action" to="/reports">View Reports</Link>
      </div>
      <div className="analytics-modern-list">
        <div className="analytics-modern-row analytics-head"><span>Date</span><span>Scans</span><span>Approved</span><span>Rejected</span><span>Avg Score</span><span>Critical / High</span></div>
        {trend.map((row, index) => <div className="analytics-modern-row" key={`${labelValue(row, "date")}-table-${index}`}>
          <span>{labelValue(row, "date")}</span>
          <span>{numberValue(row, "scans")}</span>
          <span className="analytics-good"><CheckCircle2 size={14} /> {numberValue(row, "approved")}</span>
          <span className="analytics-critical"><XCircle size={14} /> {numberValue(row, "rejected")}</span>
          <span>{numberValue(row, "average_score") || "--"}%</span>
          <span>C {numberValue(row, "critical")} / H {numberValue(row, "high")}</span>
        </div>)}
      </div>
    </section>
  </section>;
}
