import { useEffect, useState } from "react";
import { Blocks } from "lucide-react";
import { getMonitoringWidgets } from "../api/scans";
import type { MonitoringWidgets } from "../types/scans";

function title(value: string) { return value.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" "); }

export function WidgetsPage() {
  const [widgets, setWidgets] = useState<MonitoringWidgets>({});
  useEffect(() => { getMonitoringWidgets().then(setWidgets).catch(console.error); }, []);
  return <section className="page"><header className="page-header"><div><p className="eyebrow">Reusable SOC Widgets</p><h1>Widgets</h1></div><Blocks /></header>
    <div className="stat-grid sprint4-stats">{Object.entries(widgets).map(([key, value]) => <article className="stat-card" key={key}><strong className="stat-value">{value ?? "--"}</strong><span>{title(key)}</span></article>)}</div>
  </section>;
}
