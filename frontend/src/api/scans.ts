import type { CreateScanRequest, CreateScanResponse, DashboardSummary, NotificationItem, ProjectCreateRequest, ProjectFinding, ProjectHealth, TriggerScanResponse, ProjectSummary, ReportFilters, ReportHistoryItem, ScanDetails, ScanSummary, AlertItem, AlertStatistics, MonitoringOverview, HistoricalAnalytics, MonitoringWidgets, AIInsights, AIChatResponse, AIRemediationPlan, AlertPolicy, AlertPolicyUpdate } from "../types/scans";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>("/api/v1/scans/dashboard/summary");
}

export function listScans(limit = 10): Promise<ScanSummary[]> {
  return request<ScanSummary[]>(`/api/v1/scans?limit=${limit}`);
}

export function createScan(payload: CreateScanRequest): Promise<CreateScanResponse> {
  return request<CreateScanResponse>("/api/v1/scans", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getScan(scanId: string): Promise<ScanDetails> {
  return request<ScanDetails>(`/api/v1/scans/${scanId}`);
}


export function listProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>("/api/v1/projects");
}

export function createProject(payload: ProjectCreateRequest): Promise<ProjectSummary> {
  return request<ProjectSummary>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getProject(projectKey: string): Promise<ProjectHealth> {
  return request<ProjectHealth>(`/api/v1/projects/${projectKey}`);
}

export function getProjectFindings(projectKey: string, status = "ALL"): Promise<ProjectFinding[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  return request<ProjectFinding[]>(`/api/v1/projects/${projectKey}/findings?${params.toString()}`);
}

export function triggerProjectScan(projectKey: string, branch = "main"): Promise<TriggerScanResponse> {
  return request<TriggerScanResponse>(`/api/v1/projects/${projectKey}/trigger-scan`, {
    method: "POST",
    body: JSON.stringify({ runner: "github-actions", branch })
  });
}

export async function deleteProject(projectKey: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectKey}`, { method: "DELETE" });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
}

export function listReports(filters: ReportFilters = {}): Promise<ReportHistoryItem[]> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const query = params.toString();
  return request<ReportHistoryItem[]>(`/api/v1/reports${query ? `?${query}` : ""}`);
}

export function listNotifications(limit = 25): Promise<NotificationItem[]> {
  return request<NotificationItem[]>(`/api/v1/notifications?limit=${limit}`);
}

export async function deleteReport(scanId: string, reportType: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/reports/${scanId}/${reportType}`, { method: "DELETE" });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
}

export function getMasterReportStatus(scanId: string): Promise<{ scan_id: string; has_master_report: boolean; exports: Record<"PDF" | "DOCX" | "JSON", boolean> }> {
  return request<{ scan_id: string; has_master_report: boolean; exports: Record<"PDF" | "DOCX" | "JSON", boolean> }>(`/api/v1/reports/${scanId}/status`);
}

export async function generateMasterReports(scanId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/reports/${scanId}/generate`, { method: "POST" });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
}

export function reportDownloadUrl(scanId: string, format: "pdf" | "docx" | "json"): string {
  return `${API_BASE_URL}/api/v1/reports/${scanId}/${format}?refresh=true`;
}

export function toolReportDownloadUrl(scanId: string, toolName: string): string {
  return `${API_BASE_URL}/api/v1/scans/${scanId}/reports/${toolName}`;
}

export function toolReportPdfUrl(scanId: string, toolName: string): string {
  return `${API_BASE_URL}/api/v1/scans/${scanId}/reports/${toolName}/pdf`;
}


export function getAiInsights(scanId: string): Promise<AIInsights> {
  return request<AIInsights>(`/api/v1/ai/scans/${scanId}/insights`);
}

export function askAiAssistant(scanId: string, question: string): Promise<AIChatResponse> {
  return request<AIChatResponse>(`/api/v1/ai/scans/${scanId}/chat`, {
    method: "POST",
    body: JSON.stringify({ question })
  });
}

export function aiSummaryReportUrl(scanId: string): string {
  return `${API_BASE_URL}/api/v1/ai/scans/${scanId}/summary-report/pdf`;
}

export function getAiRemediationPlan(scanId: string): Promise<AIRemediationPlan> {
  return request<AIRemediationPlan>(`/api/v1/ai/scans/${scanId}/remediation-plan`);
}

export function aiRemediationPlanUrl(scanId: string): string {
  return `${API_BASE_URL}/api/v1/ai/scans/${scanId}/remediation-plan/pdf`;
}

export function listAlerts(filters: { severity?: string; status?: string; project?: string } = {}): Promise<AlertItem[]> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
  const query = params.toString();
  return request<AlertItem[]>(`/api/v1/alerts${query ? `?${query}` : ""}`);
}

export function getAlertStatistics(): Promise<AlertStatistics> {
  return request<AlertStatistics>("/api/v1/alerts/statistics");
}

export function getAlertPolicy(projectKey: string): Promise<AlertPolicy> {
  return request<AlertPolicy>(`/api/v1/alerts/policies/${projectKey}`);
}

export function updateAlertPolicy(projectKey: string, payload: AlertPolicyUpdate): Promise<AlertPolicy> {
  return request<AlertPolicy>(`/api/v1/alerts/policies/${projectKey}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getMonitoringOverview(): Promise<MonitoringOverview> {
  return request<MonitoringOverview>("/api/v1/monitoring/overview");
}

export function getHistoricalAnalytics(range = "30d"): Promise<HistoricalAnalytics> {
  return request<HistoricalAnalytics>(`/api/v1/monitoring/analytics?range=${range}`);
}

export function getMonitoringWidgets(): Promise<MonitoringWidgets> {
  return request<MonitoringWidgets>("/api/v1/monitoring/widgets");
}

export function getHealth(path = "/health"): Promise<Record<string, string | number>> {
  return request<Record<string, string | number>>(path);
}
