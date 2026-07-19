import { useEffect, useRef, useState } from "react";

import { Badge } from "../components/common/Badge";
import { Panel } from "../components/common/Panel";
import { StatCard } from "../components/common/StatCard";
import { EmbeddedMiniChat } from "../components/home/EmbeddedMiniChat";
import { NewsPanel } from "../components/news/NewsPanel";
import { createSession } from "../lib/api";
import { useNews } from "../hooks/useNews";

const VOL_HEAT = ["up", "up", "down", "up", "down", "down", "up", "up", "up"] as const;

export function Home() {
  const { data: news } = useNews();

  // The embedded chat needs a REAL persisted session: the backend types
  // session_id as uuid.UUID and 404s the turn endpoint for an unknown session,
  // so the old literal "home-embedded" made every desk-chat turn fail. Create
  // one session per mount, guarded against StrictMode's double-invoke.
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const createdRef = useRef(false);
  useEffect(() => {
    if (createdRef.current) return;
    createdRef.current = true;
    let cancelled = false;
    createSession()
      .then((s) => {
        if (!cancelled) setChatSessionId(s.id);
      })
      .catch(() => {
        /* leave chat disabled if session creation fails */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div data-testid="home-dashboard">
      <h1 className="page-title">Home</h1>
      <p className="page-sub">Live crypto · delayed equities · updated 14:32:07 UTC</p>

      <div className="breadth">
        <StatCard label="% Above 50-SMA" value={<>62<span style={{ fontSize: "15px", color: "var(--ink-faint)" }}>%</span></>} gauge={62} />
        <StatCard
          label="Advancers / Decliners"
          value={<><span className="up">312</span><span style={{ color: "var(--ink-faint)", fontSize: "15px" }}> / </span><span className="down">188</span></>}
          gauge={62}
        />
        <div className="stat">
          <div className="lbl">Market Regime</div>
          <div style={{ margin: "6px 0 4px" }}>
            <span className="pill risk-on"><span className="dot" />Risk-On</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--ink-faint)" }}>Trend + breadth aligned</div>
        </div>
        <div className="stat">
          <div className="lbl">Volatility</div>
          <div className="heat-grid">
            {VOL_HEAT.map((d, i) => (
              <i key={i} style={{ background: d === "up" ? "var(--up-bg)" : "var(--down-bg)" }} />
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="col">
          <Panel title="Active Signals" tag="3 live · analysis only">
            <article className="signal">
              <div className="sig-top">
                <span className="sig-sym">BTC-USD</span>
                <Badge variant="long">Long setup</Badge>
                <div className="sig-conf">
                  <div className="k">Confidence</div>
                  <div className="conf-bar"><span style={{ width: "72%" }} /></div>
                </div>
              </div>
              <div className="levels">
                <div className="lvl"><div className="k">Ref entry</div><div className="v num">67,180</div></div>
                <div className="lvl"><div className="k">Stop-loss</div><div className="v num down">65,900</div></div>
                <div className="lvl"><div className="k">Take-profit</div><div className="v num up">70,400</div></div>
              </div>
              <p className="rationale">
                EMA 9/21 cross reclaimed with VWAP support.{" "}
                <b>Setup detected — historically 61% win rate over 240 trades (net of fees).</b>
              </p>
              <p className="disc">Educational analysis. Not a recommendation to trade.</p>
            </article>

            <article className="signal">
              <div className="sig-top">
                <span className="sig-sym">NVDA</span>
                <Badge variant="short">Short setup</Badge>
                <Badge>15-min delayed</Badge>
                <div className="sig-conf">
                  <div className="k">Confidence</div>
                  <div className="conf-bar"><span style={{ width: "54%" }} /></div>
                </div>
              </div>
              <div className="levels">
                <div className="lvl"><div className="k">Ref entry</div><div className="v num">126.80</div></div>
                <div className="lvl"><div className="k">Stop-loss</div><div className="v num down">129.10</div></div>
                <div className="lvl"><div className="k">Take-profit</div><div className="v num up">121.40</div></div>
              </div>
              <p className="rationale">
                Bollinger upper rejection + RSI divergence on 1h.{" "}
                <b>Setup detected — historically 57% win rate over 96 trades (net of fees).</b>
              </p>
              <p className="disc">Educational analysis. Not a recommendation to trade.</p>
            </article>
          </Panel>

          <Panel title="Top Scanner Hits" tag="last 30 min">
            <div className="feed-row">
              <span className="sym">ETH-USD</span>
              <div className="rule">VWAP reclaim · vol &gt; 2× avg</div>
              <div style={{ textAlign: "right" }}>
                <svg className="spark" viewBox="0 0 58 22" aria-hidden="true"><polyline points="0,16 10,15 20,17 30,11 40,9 50,5 58,3" fill="none" stroke="var(--up)" strokeWidth="1.5" /></svg>
                <div className="t num">14:29</div>
              </div>
            </div>
            <div className="feed-row">
              <span className="sym">SOL-USD</span>
              <div className="rule">EMA 9/21 bearish cross</div>
              <div style={{ textAlign: "right" }}>
                <svg className="spark" viewBox="0 0 58 22" aria-hidden="true"><polyline points="0,4 10,6 20,7 30,11 40,13 50,16 58,18" fill="none" stroke="var(--down)" strokeWidth="1.5" /></svg>
                <div className="t num">14:24</div>
              </div>
            </div>
            <div className="feed-row">
              <span className="sym">AAPL</span>
              <div className="rule">ORB breakout · 15m</div>
              <div style={{ textAlign: "right" }}>
                <svg className="spark" viewBox="0 0 58 22" aria-hidden="true"><polyline points="0,14 10,13 20,12 30,10 40,11 50,7 58,5" fill="none" stroke="var(--up)" strokeWidth="1.5" /></svg>
                <div className="t num">14:18</div>
              </div>
            </div>
          </Panel>
        </div>

        <div className="col">
          <Panel title="News & Sentiment">
            <NewsPanel items={news ?? []} />
          </Panel>

          <Panel title="Watchlist" tag="live">
            <div className="watch">
              <div className="wtile gain"><div className="sym">BTC-USD</div><div className="px num">67,412</div><div className="chg up num">+2.14%</div></div>
              <div className="wtile loss"><div className="sym">SOL-USD</div><div className="px num">184.63</div><div className="chg down num">−0.73%</div></div>
              <div className="wtile gain"><div className="sym">ETH-USD</div><div className="px num">3,284.5</div><div className="chg up num">+1.02%</div></div>
              <div className="wtile skel"><div className="sym">AAPL</div><div className="bar w60" /><div className="bar w40" /></div>
            </div>
          </Panel>

          <Panel title="Ask the desk" tag="beta">
            {chatSessionId ? (
              <EmbeddedMiniChat sessionId={chatSessionId} />
            ) : (
              <p className="page-sub">Starting a session…</p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
