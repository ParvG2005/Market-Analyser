import { useMemo, useRef, useState } from "react";

import { useWebSocket } from "./useWebSocket";
import { DEV_USER_ID, type ScanHit } from "../lib/scannerTypes";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
const MAX_HITS = 50;

/**
 * Subscribes to the live scanner-hits WebSocket and returns the most recent
 * hits (newest first, bounded to `MAX_HITS`, deduped by rule/instrument/ts).
 * The token is `DEV_USER_ID` so the feed receives hits produced by rules the
 * REST hook creates under that same dev user (real auth arrives in Phase 11).
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

  useWebSocket(`${WS_BASE}/ws/scanner/hits?token=${DEV_USER_ID}`, { onMessage });

  return hits;
}
