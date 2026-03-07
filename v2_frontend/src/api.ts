/**
 * ShufaClaw V2 — API Client
 *
 * Centralized fetch helpers for the dashboard backend.
 * Uses VITE_API_BASE or relative /api when proxied.
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface SystemMetrics {
  health_status: string;
  ingestion_lag_ms: number;
  execution_latency_ms: number;
  active_strategies: number;
  api_errors_1h: number;
  last_updated: string;
}

export const api = {
  monitoring: {
    summary: () => fetchApi<SystemMetrics>('/api/monitoring/summary'),
  },
  portfolio: () => fetchApi<{ status: string; data: unknown[] }>('/api/portfolio'),
  features: (symbol: string, timeframe = '1h') =>
    fetchApi<{ status: string; data: { vector: unknown; regime: string } }>(
      `/api/features/current/${encodeURIComponent(symbol)}?timeframe=${timeframe}`
    ),
  v2: {
    strategies: (limit = 50) =>
      fetchApi<{ status: string; data: unknown[] }>(`/api/v2/strategies?limit=${limit}`),
    backtests: (symbol?: string, strategyId?: string, limit = 50) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (symbol) params.set('symbol', symbol);
      if (strategyId) params.set('strategy_id', strategyId);
      return fetchApi<{ status: string; data: unknown[] }>(`/api/v2/backtests?${params}`);
    },
    orders: (symbol?: string, limit = 50) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (symbol) params.set('symbol', symbol);
      return fetchApi<{ status: string; data: unknown[] }>(`/api/v2/orders?${params}`);
    },
    riskEvents: (limit = 50) =>
      fetchApi<{ status: string; data: unknown[] }>(`/api/v2/risk/events?limit=${limit}`),
    agentReports: (limit = 20, agentType?: string) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (agentType) params.set('agent_type', agentType);
      return fetchApi<{ status: string; data: unknown[] }>(`/api/v2/agents/reports?${params}`);
    },
  },
};
