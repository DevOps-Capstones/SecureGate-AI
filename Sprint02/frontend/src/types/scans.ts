export interface ScanSummary {
  scan_id: string;
  project_name: string;
  repository_url: string;
  branch: string;
  commit_sha: string;
  status: string;
  received_at: string;
  completed_at: string | null;
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
}
