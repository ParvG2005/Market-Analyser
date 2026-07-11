import { useMemo, useRef, useState } from "react";

import { buildWsUrl } from "../lib/api";
import type { ScanHit } from "../lib/scannerTypes";
import { useAccessToken } from "./useAccessToken";
import { useWebSocket } from "./useWebSocket";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
const MAX_HITS = 50;

/**
 * Subscribes to the live scanner-hits WebSocket and returns the most recent
 * hits (newest first, bounded to `MAX_HITS`, deduped by rule/instrument/ts).
 * Carries the real Supabase access token as `?token=`; stays disconnected
 * until a token is available (i.e. the user is signed in).
 */
export function useScanHits(): ScanHit[] {
  const [hits, setHits] = useState<ScanHit[]>([]);
  const seen = useRef(new Set<string>());

  const onMessage = useMemo(
    () => (data: string) => {
      let hit: ScanHit;
      try {
        hit = JSON.parse(data);
      } catch {
        return;
      }
      const key = `${hit.rule_id}-${hit.instrument_id}-${hit.ts}`;
      if (seen.current.has(key)) return;
      seen.current.add(key);
      setHits((prev) => [hit, ...prev].slice(0, MAX_HITS));
    },
    [],
  );

  const token = useAccessToken();
  const wsUrl = token ? buildWsUrl(`${WS_BASE}/ws/scanner/hits`, token) : "";
  useWebSocket(wsUrl, { onMessage });

  return hits;
}
