import type { Report, WorkOrder } from './types';
import { formatError } from './errors';

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8010/api').replace(/\/+$/, '');

class ApiError extends Error {
  constructor(readonly status: number, readonly payload: unknown) {
    super(`HTTP ${status}: ${formatError(payload, API_BASE_URL)}`);
    this.name = 'ApiError';
  }
}

function queryString(values: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value.trim() !== '') params.set(key, value);
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

async function readResponse<T>(response: Response): Promise<T> {
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, payload);
  return payload as T;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  return readResponse<T>(response);
}

export const api = {
  assetUrl: (path: string) => path.startsWith('http') ? path : `${API_BASE_URL.replace(/\/api\/?$/, '')}${path}`,
  reports: (filters: Record<string, string> = {}) => {
    const params = new URLSearchParams({ limit: '100' });
    for (const [key, value] of Object.entries(filters)) {
      if (value.trim() !== '') params.set(key, value);
    }
    return req<{ items: Report[]; total: number }>(`/reports?${params}`);
  },
  report: (id: string) => req<Report>(`/reports/${encodeURIComponent(id)}`),
  create: (data: unknown) => req<Report>('/reports', { method: 'POST', body: JSON.stringify(data) }),
  upload: async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(`${API_BASE_URL}/uploads`, { method: 'POST', body: form });
    return readResponse<{ image_ref: string }>(response);
  },
  chat: (message: string) => req<{ answer: string; complaint_ids: string[] }>('/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  analytics: (filters: Record<string, string> = {}) => req<any>(`/analytics/summary${queryString(filters)}`),
  history: (id: string) => req<any[]>(`/reports/${encodeURIComponent(id)}/history`),
  duplicates: (id: string) => req<any[]>(`/reports/${encodeURIComponent(id)}/duplicates`),
  duplicateReviews: (id: string) => req<any[]>(`/reports/${encodeURIComponent(id)}/duplicate-reviews`),
  reviewDuplicate: (id: string, candidateId: string, decision: string, note?: string) => req<any>(`/reports/${encodeURIComponent(id)}/duplicate-review`, { method: 'POST', body: JSON.stringify({ candidate_id: candidateId, decision, note }) }),
  assign: (id: string, team: string) => req<Report>(`/admin/reports/${encodeURIComponent(id)}/assignment`, { method: 'PATCH', body: JSON.stringify({ team }) }),
  status: (id: string, status: string, note?: string) => req<Report>(`/admin/reports/${encodeURIComponent(id)}/status`, { method: 'PATCH', body: JSON.stringify({ status, note }) }),
  brief: () => req<any>('/admin/action-brief', { method: 'POST' }),
  resourcePlan: (id: string) => req<any>(`/reports/${encodeURIComponent(id)}/resource-plan`),
  workOrders: () => req<WorkOrder[]>('/admin/work-orders'),
  createWorkOrder: (data: unknown) => req<WorkOrder>('/admin/work-orders', { method: 'POST', body: JSON.stringify(data) }),
  updateWorkOrder: (id: number, data: unknown) => req<WorkOrder>(`/admin/work-orders/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
};
