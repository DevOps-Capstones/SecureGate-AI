export interface ScanSummary {
  scan_id: string;
  project_name: string;
  repository_url: string;
  image_name: string | null;
  image_tag: string | null;
  image_full_path: string | null;
  branch: string;
  commit_sha: string;
  status: string;
  pipeline_run_id: string | null;
  pipeline_status: string | null;
  received_at: string;
  processing_at: string | null;
  scoring_at: string | null;
  report_generation_at: string | null;
  notification_sent_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  security_score: number | null;
  deployment_decision: "APPROVED" | "REJECTED" | "PENDING";
  sonar_quality_gate: string;
}

export interface ToolReport {
  tool_name: string;
  status: string;
  uploaded_at: string;
  file_path: string | null;
  scan_id: string | null;
}

export interface Finding {
  tool: string;
  severity: string;
  title: string;
  description: string | null;
  file: string | null;
  source_tool: string;
  resolution_status: string;
  resolved_at: string | null;
}

export interface TimelineEvent {
  label: string;
  status: "DONE" | "PENDING" | "FAILED" | string;
  timestamp: string | null;
}

export interface NotificationItem {
  notification_type: string;
  category: string;
  severity_level: string;
  summary_period: string | null;
  recipient: string;
  status: string;
  created_at: string;
  sent_at: string | null;
  error_message: string | null;
}

export interface AuditLogItem {
  action: string;
  message: string;
  actor: string;
  created_at: string;
  log_metadata: Record<string, unknown>;
}

export interface ScanDetails extends ScanSummary {
  project_key: string | null;
  uploaded_reports: ToolReport[];
  finding_counts: Record<string, number>;
  tool_status: Record<string, string>;
  findings: Finding[];
  timeline: TimelineEvent[];
  notifications: NotificationItem[];
  audit_logs: AuditLogItem[];
}

export interface CreateScanRequest {
  project_name: string;
  repository_url: string;
  branch: string;
  commit_sha: string;
}

export interface CreateScanResponse {
  scan_id: string;
  status: string;
}

export interface DashboardSummary {
  total_projects: number;
  active_project_name: string | null;
  active_project_key: string | null;
  active_repository_url: string | null;
  total_scans: number;
  active_scans: number;
  recent_scans: ScanSummary[];
  latest_uploads: ToolReport[];
  most_recent_findings: Finding[];
  latest_security_score: number | null;
  latest_approval_status: "APPROVED" | "REJECTED" | "PENDING";
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  pending_findings: number;
  resolved_findings: number;
  vulnerability_trend: VulnerabilityTrendPoint[];
  score_trend: ScoreTrendPoint[];
  recent_reports: DashboardReport[];
  recent_notifications: NotificationItem[];
}

export interface VulnerabilityTrendPoint {
  scan_id: string;
  project_name: string;
  evaluated_at: string;
  CRITICAL: number;
  HIGH: number;
  MEDIUM: number;
  LOW: number;
  PENDING: number;
  RESOLVED: number;
}

export interface ScoreTrendPoint {
  scan_id: string;
  score: number;
  evaluated_at: string;
}

export interface DashboardReport {
  scan_id: string;
  project_name: string;
  report_type: string;
  file_path: string;
  created_at: string;
}

export interface ReportHistoryItem {
  scan_id: string;
  project_name: string;
  branch: string;
  image_name: string | null;
  image_tag: string | null;
  image_full_path: string | null;
  report_type: string;
  decision: "APPROVED" | "REJECTED" | "PENDING";
  security_score: number | null;
  critical_count: number;
  high_count: number;
  created_at: string;
}

export interface ReportFilters {
  project?: string;
  branch?: string;
  image?: string;
  decision?: string;
  severity?: string;
  date_from?: string;
  date_to?: string;
  score_min?: string;
  score_max?: string;
}


export interface ProjectSummary {
  project_key: string;
  name: string;
  repository_url: string;
  created_at: string;
}

export interface ProjectCreateRequest {
  name: string;
  repository_url: string;
}

export interface ToolHealth {
  tool: string;
  label: string;
  status: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface ProjectHealth extends ProjectSummary {
  latest_scan: ScanSummary | null;
  total_scans: number;
  latest_security_score: number | null;
  latest_decision: string;
  sonar_quality_gate: string;
  severity_counts: Record<string, number>;
  decision_counts: Record<string, number>;
  tool_health: ToolHealth[];
  recent_scans: ScanSummary[];
}




export interface TriggerScanResponse {
  status: string;
  runner: string;
  workflow_file: string;
  branch: string;
  repository: string;
  message: string;
}

export interface ProjectFinding {
  tool: string;
  severity: string;
  title: string;
  description: string | null;
  file: string | null;
  source_tool: string;
  first_seen_scan_id: string;
  first_seen_at: string;
  latest_seen_scan_id: string;
  latest_seen_at: string;
  occurrences: number;
  resolution_status: "OPEN" | "RESOLVED" | "PENDING_RECHECK" | string;
  resolved_at: string | null;
}

export interface AlertItem {
  id: string;
  alert_id: string;
  scan_id: string | null;
  project_name: string;
  repository: string | null;
  branch: string | null;
  severity: string;
  alert_type: string;
  status: string;
  notification_channels: string[];
  description: string;
  recommendation: string;
  runbook_url: string;
  escalation_level: number;
  escalation_history: unknown[];
  created_at: string;
  resolved_at: string | null;
  resolution_time: number | null;
}

export interface AlertPolicy {
  project_key: string;
  project_name: string;
  repository_url: string;
  enabled: boolean;
  slack_enabled: boolean;
  email_enabled: boolean;
  slack_min_severity: string;
  email_min_severity: string;
  updated_at: string | null;
}

export interface AlertPolicyUpdate {
  enabled: boolean;
  slack_enabled: boolean;
  email_enabled: boolean;
  slack_min_severity: string;
  email_min_severity: string;
}

export interface AlertStatistics {
  total_alerts: number;
  open_alerts: number;
  resolved_alerts: number;
  escalated_alerts: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
}

export interface MonitoringOverview {
  security_score: number | null;
  deployment_approval_rate: number;
  critical_findings: number;
  high_findings: number;
  running_scans: number;
  completed_scans: number;
  failed_scans: number;
  reports_generated: number;
  average_scan_time: number;
  top_risk_projects: Array<{ project: string; risk_findings: number }>;
  alerts: AlertStatistics;
  notifications: Record<string, number | string>;
}

export interface HistoricalAnalytics {
  range: string;
  trend: Array<Record<string, number | string | null>>;
}

export type MonitoringWidgets = Record<string, string | number | null>;


export interface AIInsights {
  scan_id: string;
  project_name: string;
  repository_url: string;
  branch: string;
  executive_summary: string;
  overall_risk: string;
  ai_readiness: string;
  deployment_recommendation: string;
  estimated_fix_time: string;
  top_recommendations: string[];
  confidence: string;
  model: string;
  ollama_status: string;
  ai_text: string;
  generated_at: string;
}

export interface AIChatResponse {
  scan_id: string;
  answer: string;
  model: string;
  ollama_status: string;
}

export interface RemediationDetail {
  issue_name: string;
  tool: string;
  source_tool: string;
  severity: string;
  location: string;
  affected_file: string;
  root_cause: string;
  business_impact: string;
  why_it_matters: string;
  step_by_step_fix: string[];
  verification_steps: string[];
  recommended_version: string;
  example_configuration: string;
  estimated_time: string;
  estimated_minutes: number;
  priority: number;
  priority_label: string;
  status: string;
}

export interface AIRemediationPlan {
  scan_id: string;
  project_name: string;
  repository_url: string;
  branch: string;
  deployment_decision: string;
  security_score: number | null;
  ai_readiness_score: number;
  overall_priority: string;
  overall_risk: string;
  estimated_fix_time: string;
  total_findings: number;
  total_recommended_actions: number;
  finding_counts: Record<string, number | string>;
  top_three_risks: Array<{ issue: string; severity: string; tool: string; location: string }>;
  priority_matrix: Array<{ issue: string; severity: string; tool: string; estimated_fix_time: string; status: string; priority: number; priority_label: string }>;
  detailed_remediation: RemediationDetail[];
  production_readiness_checklist: Array<{ label: string; complete: boolean }>;
  completion_percentage: number;
  remediation_timeline: Array<{ task: string; estimated_time: string; priority: number; assigned_area: string }>;
  production_ready: boolean;
  remaining_blockers: string[];
  final_recommendation: string;
  generated_at: string;
  model: string;
  ollama_status: string;
}
