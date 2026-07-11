import { useCallback, useState } from "react";

import { authedFetch, chatTurnUrl } from "../lib/api";
import { useChatStore, type ToolEventVM } from "../stores/chatStore";

interface StreamEvent {
  type: "token" | "tool_call" | "tool_result" | "done" | "error";
  payload: Record<string, unknown>;
}

/**
 * Sends a turn to the SSE endpoint and folds the streamed events into store
 * state: tokens accumulate into the forming assistant message, tool_call events
 * surface as activity chips, and `done` commits the final answer.
 *
 * The turn endpoint is a POST returning `text/event-stream`, so we read the
 * response body as a stream rather than using EventSource (which is GET-only).
 */
export function useChatStream(sessionId: string) {
  const messages = useChatStore((s) => s.messagesBySession[sessionId] ?? []);
  const appendMessage = useChatStore((s) => s.appendMessage);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [toolEvents, setToolEvents] = useState<ToolEventVM[]>([]);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !sessionId || isStreaming) return;

      appendMessage(sessionId, { role: "user", content: trimmed });
      setIsStreaming(true);
      setStreamingText("");
      setToolEvents([]);
      setError(null);

      try {
        const res = await authedFetch(chatTurnUrl(sessionId), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: trimmed }),
        });
        if (!res.ok || !res.body) {
          throw new Error(res.status === 429 ? "You've hit the message limit. Try again later." : "The assistant is unavailable right now.");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let answer = "";
        let acc = "";
        let streamError: string | null = null;
        const turnTools: ToolEventVM[] = [];

        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const line = frame.split("\n").find((l) => l.startsWith("data: "));
            if (!line) continue;
            const event: StreamEvent = JSON.parse(line.slice("data: ".length));
            if (event.type === "token") {
              acc += String(event.payload.text ?? "");
              setStreamingText(acc);
            } else if (event.type === "tool_call") {
              const evt = { name: String(event.payload.name), ok: Boolean(event.payload.ok) };
              turnTools.push(evt);
              setToolEvents((prev) => [...prev, evt]);
            } else if (event.type === "done") {
              answer = String(event.payload.answer ?? acc);
            } else if (event.type === "error") {
              streamError = String(event.payload.message ?? "The assistant is unavailable right now.");
            }
          }
        }

        if (streamError) {
          setError(streamError);
        } else {
          appendMessage(sessionId, {
            role: "assistant",
            content: answer || acc,
            toolEvents: turnTools.length > 0 ? turnTools : undefined,
          });
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        setIsStreaming(false);
        setStreamingText("");
      }
    },
    [sessionId, isStreaming, appendMessage],
  );

  return { messages, toolEvents, isStreaming, streamingText, error, sendMessage };
}
