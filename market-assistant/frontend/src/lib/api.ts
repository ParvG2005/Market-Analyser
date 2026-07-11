const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface InstrumentDto {
  id: number;
  symbol: string;
  assetClass: string;
  exchange: string;
  active: boolean;
  delayed: boolean;
  delayMinutes: number;
}

interface InstrumentApiShape {
  id: number;
  symbol: string;
  asset_class: string;
  exchange: string;
  active: boolean;
  delayed: boolean;
  delay_minutes: number;
}

function fromApi(raw: InstrumentApiShape): InstrumentDto {
  return {
    id: raw.id,
    symbol: raw.symbol,
    assetClass: raw.asset_class,
    exchange: raw.exchange,
    active: raw.active,
    delayed: raw.delayed,
    delayMinutes: raw.delay_minutes,
  };
}

export async function getInstruments(assetClass?: string): Promise<InstrumentDto[]> {
  const params = assetClass ? `?asset_class=${encodeURIComponent(assetClass)}` : "";
  const res = await fetch(`${API_BASE}/api/instruments${params}`);
  const body: InstrumentApiShape[] = await res.json();
  return body.map(fromApi);
}

export async function createInstrument(payload: {
  symbol: string;
  assetClass: string;
  exchange: string;
}): Promise<InstrumentDto> {
  const res = await fetch(`${API_BASE}/api/instruments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbol: payload.symbol,
      asset_class: payload.assetClass,
      exchange: payload.exchange,
    }),
  });
  const body: InstrumentApiShape = await res.json();
  return fromApi(body);
}

export async function updateInstrument(id: number, active: boolean): Promise<InstrumentDto> {
  const res = await fetch(`${API_BASE}/api/instruments/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });
  const body: InstrumentApiShape = await res.json();
  return fromApi(body);
}

export async function seedNifty50(): Promise<InstrumentDto[]> {
  const res = await fetch(`${API_BASE}/api/instruments/seed-nifty50`, {
    method: "POST",
  });
  const body: InstrumentApiShape[] = await res.json();
  return body.map(fromApi);
}

// --- Chat (Phase 10) ---

export interface ChatSessionDto {
  id: string;
  createdAt: string;
}

interface ChatSessionApiShape {
  id: string;
  user_id: string;
  created_at: string;
}

export interface ChatMessageDto {
  role: "user" | "assistant" | "tool";
  content: string;
}

interface ChatMessageApiShape {
  role: "user" | "assistant" | "tool";
  content: string | null;
}

export function chatTurnUrl(sessionId: string): string {
  return `${API_BASE}/api/chat/sessions/${sessionId}/turns`;
}

export async function createSession(): Promise<ChatSessionDto> {
  const res = await fetch(`${API_BASE}/api/chat/sessions`, { method: "POST" });
  const body: ChatSessionApiShape = await res.json();
  return { id: body.id, createdAt: body.created_at };
}

export async function listSessions(): Promise<ChatSessionDto[]> {
  const res = await fetch(`${API_BASE}/api/chat/sessions`);
  const body: ChatSessionApiShape[] = await res.json();
  return body.map((s) => ({ id: s.id, createdAt: s.created_at }));
}

export async function getSessionMessages(sessionId: string): Promise<ChatMessageDto[]> {
  const res = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}/messages`);
  const body: ChatMessageApiShape[] = await res.json();
  return body
    .filter((m) => m.role !== "tool" && m.content)
    .map((m) => ({ role: m.role, content: m.content ?? "" }));
}
