import { Activity, AlertTriangle, CheckCircle2, Clock3 } from "lucide-react";

const stats = [
  { label: "Validated services", value: "6", icon: CheckCircle2 },
  { label: "Manual tools", value: "3", icon: Activity },
  { label: "Mock open findings", value: "18", icon: AlertTriangle },
  { label: "Avg scan time", value: "2m 14s", icon: Clock3 }
];

const recentScans = [
  { target: "python:3.7", type: "Trivy Image", status: "Manual validation", severity: "Critical" },
  { target: "workspace", type: "GitLeaks", status: "Manual validation", severity: "Low" },
  { target: "source tree", type: "Trivy FS", status: "Manual validation", severity: "Medium" }
];

export function Dashboard() {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Sprint 1</p>
          <h1>Security tool validation dashboard</h1>
        </div>
        <span className="status-pill">Foundation Stage</span>
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
          <h2>Recent mock validations</h2>
          <span>Frontend-only sample data</span>
        </div>
        <div className="table">
          <div className="table-row table-head">
            <span>Target</span>
            <span>Tool</span>
            <span>Status</span>
            <span>Highest severity</span>
          </div>
          {recentScans.map((scan) => (
            <div className="table-row" key={`${scan.target}-${scan.type}`}>
              <span>{scan.target}</span>
              <span>{scan.type}</span>
              <span>{scan.status}</span>
              <span className={`severity ${scan.severity.toLowerCase()}`}>{scan.severity}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
