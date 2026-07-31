import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Bot, CheckCircle2, Download, FileText, ShieldAlert, Timer, Wrench } from "lucide-react";
import { aiRemediationPlanUrl, getAiRemediationPlan, listScans } from "../api/scans";
import type { AIRemediationPlan, ScanSummary } from "../types/scans";

function severityClass(value: string) {
  return value.toLowerCase();
}

function securityCountClass(value: number | string | null | undefined) {
  return Number(value ?? 0) > 0 ? "security-count nonzero" : "security-count";
}

function friendlyError(message: string) {
  if (message.includes("less_than_equal") || message.includes("Input should be less than or equal")) {
    return "SecureGate AI can load up to 50 recent scans at a time. Please refresh the page.";
  }
  try {
    const parsed = JSON.parse(message);
    return parsed.detail?.[0]?.msg ?? parsed.detail ?? "Unable to load remediation data.";
  } catch {
    return message || "Unable to load remediation data.";
  }
}

export function RemediationPlanPage() {
  const [searchParams] = useSearchParams();
  const requestedScanId = searchParams.get("scan_id");
  const [plan, setPlan] = useState<AIRemediationPlan | null>(null);
  const [scanId, setScanId] = useState<string | null>(null);
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [planLoading, setPlanLoading] = useState(false);

  const loadPlan = async (nextScanId: string) => {
    setPlanLoading(true);
    setError(null);
    setScanId(nextScanId);
    try {
      setPlan(await getAiRemediationPlan(nextScanId));
    } catch (err) {
      setError(err instanceof Error ? friendlyError(err.message) : "Unable to load remediation plan.");
      setPlan(null);
    } finally {
      setPlanLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    listScans(50)
      .then(async (items) => {
        setScans(items);
        const selected = items.find((item) => item.scan_id === requestedScanId) ?? items[0];
        if (!selected?.scan_id) {
          setPlan(null);
          setScanId(null);
          return;
        }
        await loadPlan(selected.scan_id);
      })
      .catch((err: Error) => setError(friendlyError(err.message)))
      .finally(() => setLoading(false));
  }, [requestedScanId]);

  if (loading) return <section className="page"><div className="section-band scan-modern-card"><strong>Loading AI Remediation Plan...</strong></div></section>;

  return <section className="page">
    <header className="page-header"><div><p className="eyebrow">AI Remediation</p><h1>Remediation Plan</h1><p className="dashboard-subtitle">Short, developer-focused actions for the selected SecureGate AI scan.</p></div></header>
    {error && <p className="error-text">{error}</p>}
    <div className="section-band scan-modern-card remediation-selector-card">
      <div className="scan-card-header">
        <span className="scan-card-icon"><Bot size={22} /></span>
        <div><h2>Choose Scanned Project</h2><p>Select a recent scan. The plan below updates for that project, branch, and scan result.</p></div>
        {planLoading && <span className="scan-card-count">Loading</span>}
      </div>
      <select className="remediation-scan-select" value={scanId ?? ""} onChange={(event) => loadPlan(event.target.value)} disabled={scans.length === 0 || planLoading}>
        {scans.length === 0 ? <option value="">No scans available</option> : scans.map((scan) => (
          <option value={scan.scan_id} key={scan.scan_id}>{scan.project_name} · {scan.branch} · {scan.scan_id} · {scan.deployment_decision}</option>
        ))}
      </select>
    </div>
    {!plan ? <div className="section-band scan-modern-card"><div className="scan-card-header"><span className="scan-card-icon"><Bot size={22} /></span><div><h2>No Remediation Plan Yet</h2><p>Run a scan first. SecureGate AI will generate a remediation plan from the Master Security Report.</p></div></div></div> : <>
      <div className="section-band scan-modern-card remediation-plan-card">
        <div className="scan-card-header"><span className="scan-card-icon"><Wrench size={22} /></span><div><h2>{plan.project_name}</h2><p>{plan.repository_url} | {plan.branch} | {plan.scan_id}</p></div><span className={`scan-card-count ${plan.production_ready ? "" : "failed"}`}>{plan.production_ready ? "PRODUCTION READY" : "NOT PRODUCTION READY"}</span></div>
        <div className="remediation-kpi-grid">
          <div><span>Priority</span><strong>{plan.overall_priority}</strong></div>
          <div><span>Security Score</span><strong>{plan.security_score ?? "--"}/100</strong></div>
          <div><span>AI Readiness</span><strong>{plan.ai_readiness_score}/100</strong></div>
          <div><span>Fix Time</span><strong>{plan.estimated_fix_time}</strong></div>
          <div><span>Open Actions</span><strong className={securityCountClass(plan.total_recommended_actions)}>{plan.total_recommended_actions}</strong></div>
        </div>
        <div className="remediation-action-row">
          {scanId && <a className="green-pill-button" href={aiRemediationPlanUrl(scanId)}><Download size={14} /> Download PDF</a>}
          {scanId && <Link className="green-pill-button" to={`/scans/${scanId}`}><FileText size={14} /> Open Scan</Link>}
        </div>
      </div>

      <div className="section-band scan-modern-card">
        <div className="scan-card-header"><span className="scan-card-icon"><ShieldAlert size={22} /></span><div><h2>Priority Matrix</h2><p>Only the highest-priority fixes are shown here to keep the plan focused.</p></div><span className="scan-card-count"><span className={securityCountClass(Math.min(plan.priority_matrix.length, 6))}>{Math.min(plan.priority_matrix.length, 6)}</span> Priority Actions</span></div>
        <div className="table remediation-table"><div className="table-row table-head"><span>Priority</span><span>Issue</span><span>Severity</span><span>Tool</span><span>Fix Time</span></div>{plan.priority_matrix.slice(0, 6).map((item) => <div className="table-row" key={`${item.priority}-${item.issue}`}><span>P{item.priority}</span><strong>{item.issue}</strong><span className={`severity ${severityClass(item.severity)}`}>{item.severity}</span><span>{item.tool}</span><span>{item.estimated_fix_time}</span></div>)}</div>
      </div>

      <div className="section-band scan-modern-card">
        <div className="scan-card-header"><span className="scan-card-icon"><CheckCircle2 size={22} /></span><div><h2>Production Readiness Checklist</h2><p>Completion percentage: {plan.completion_percentage}%</p></div></div>
        <div className="remediation-checklist">{plan.production_readiness_checklist.map((item) => <span className={item.complete ? "complete" : "pending"} key={item.label}>{item.complete ? "Done" : "Pending"} · {item.label}</span>)}</div>
      </div>

      <div className="section-band scan-modern-card">
        <div className="scan-card-header"><span className="scan-card-icon"><Timer size={22} /></span><div><h2>Fix Timeline</h2><p>Total estimated remediation time: {plan.estimated_fix_time}</p></div></div>
        <div className="remediation-timeline-list">{plan.remediation_timeline.slice(0, 4).map((item) => <span key={`${item.priority}-${item.task}`}><strong>{item.task}</strong><small>{item.estimated_time} · P{item.priority} · {item.assigned_area}</small></span>)}</div>
      </div>

      <div className="section-band scan-modern-card">
        <div className="scan-card-header"><span className="scan-card-icon"><Bot size={22} /></span><div><h2>AI Final Recommendation</h2><p>Generated from the latest remediation context.</p></div></div>
        <p className="muted">{plan.final_recommendation}</p>
      </div>
    </>}
  </section>;
}
