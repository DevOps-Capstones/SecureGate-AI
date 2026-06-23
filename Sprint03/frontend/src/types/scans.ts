export interface ScanSummary {
  scan_id: string;
  project_name: string;
  repository_url: string;
  branch: string;
  commit_sha: string;
  status: string;
  received_at: string;
  completed_at: string | null;
  security_score: number | null;
  deployment_decision: "APPROVED" | "REJECTED" | "PENDING";
  sonar_quality_gate: string;
}

export interface ToolReport {
  tool_name: string;
  status: string;
  uploaded_at: string;
}

export interface Finding {
  tool: string;
  severity: string;
  title: string;
  description: string | null;
  file: string | null;
  source_tool: string;
}

export interface ScanDetails extends ScanSummary {
  uploaded_reports: ToolReport[];
  finding_counts: Record<string, number>;
  tool_status: Record<string, string>;
  findings: Finding[];
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
  total_scans: number;
  recent_scans: ScanSummary[];
  latest_uploads: ToolReport[];
  most_recent_findings: Finding[];
  latest_security_score: number | null;
  latest_approval_status: "APPROVED" | "REJECTED" | "PENDING";
  critical_findings: number;
  high_findings: number;
  score_trend: ScoreTrendPoint[];
  recent_reports: DashboardReport[];
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
  decision?: string;
  severity?: string;
  date_from?: string;
  date_to?: string;
}
