import type { CreateScanResponse, ScanDetails, ScanSummary } from "../types/scans";

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

export function listScans(limit = 10): Promise<ScanSummary[]> {
  return request<ScanSummary[]>(`/api/v1/scans?limit=${limit}`);
}

export function createScan(repositoryUrl: string): Promise<CreateScanResponse> {
  return request<CreateScanResponse>("/api/v1/scans", {
    method: "POST",
    body: JSON.stringify({ repository_url: repositoryUrl })
  });
}

export function getScan(scanId: string): Promise<ScanDetails> {
  return request<ScanDetails>(`/api/v1/scans/${scanId}`);
}
