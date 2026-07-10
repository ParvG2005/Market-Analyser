import { useCallback, useEffect, useRef, useState } from "react";

export type WebSocketStatus = "connecting" | "open" | "closed";

export interface UseWebSocketOptions {
  onMessage: (data: string) => void;
  reconnectDelayMs?: number;
}

/**
 * Reconnecting WebSocket hook. Exposes a live `status` and a `send()` that
 * JSON-encodes its argument. Auto-reconnects (with a fixed delay) on close
 * unless the component unmounts. No-ops gracefully where `WebSocket` is
 * unavailable (e.g. server-side / jsdom without a stub).
 */
export function useWebSocket(
  url: string,
  { onMessage, reconnectDelayMs = 1000 }: UseWebSocketOptions,
) {
  const [status, setStatus] = useState<WebSocketStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (typeof WebSocket === "undefined") {
      setStatus("closed");
      return;
    }

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      setStatus("connecting");

      ws.onopen = () => setStatus("open");
      ws.onmessage = (event: MessageEvent<string>) => onMessageRef.current(event.data);
      ws.onclose = () => {
        setStatus("closed");
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, reconnectDelayMs);
        }
      };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, [url, reconnectDelayMs]);

  const send = useCallback((data: unknown) => {
    wsRef.current?.send(JSON.stringify(data));
  }, []);

  return { status, send };
}
