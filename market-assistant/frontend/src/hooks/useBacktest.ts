import { useQuery } from "@tanstack/react-query";

import { authedFetch } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface BacktestStats {
  sharpe: number;
  max_dd: number;
  win_rate: number;
  net_return: number;
  trade_count: number;
}

export interface EquityPoint {
  ts: string;
  value: number;
}

export interface BacktestResponse {
  id: string;
  status: string;
  stats: BacktestStats | null;
  equity_curve: EquityPoint[] | null;
}

async function fetchBacktest(id: string): Promise<BacktestResponse> {
  const res = await authedFetch(`${API_BASE}/backtests/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch backtest ${id} (${res.status})`);
  }
  return res.json();
}

/**
 * TanStack Query wrapper over `GET /backtests/{id}`. Polls every 2s while the
 * backtest is still running, and stops once it reaches a terminal state
 * (`status === "done"` or `status === "failed"`).
 */
export function useBacktest(id: string) {
  return useQuery({
    queryKey: ["backtest", id],
    queryFn: () => fetchBacktest(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" ? false : 2000;
    },
  });
}
