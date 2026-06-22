export interface ScanSummary {
  scan_id: string;
  repository_url: string;
  status: string;
  deployment_approved: boolean;
  started_at: string;
  completed_at: string | null;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  secrets_count: number;
}

export interface Finding {
  scanner_type: string;
  severity: string;
  file_path: string | null;
  line_number: number | null;
  title: string | null;
  description: string | null;
  vulnerability_id: string | null;
}

export interface ScanDetails extends ScanSummary {
  gitleaks_findings: Finding[];
  trivy_findings: Finding[];
}

export interface CreateScanResponse {
  scan_id: string;
  status: string;
  deployment_approved: boolean;
  critical_count: number;
  high_count: number;
  medium_count: number;
  secrets_count: number;
}
