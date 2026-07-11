import { useState } from "react";

import { DelayBadge } from "../components/common/DelayBadge";
import { Disclaimer } from "../components/Disclaimer";
import { EmptyState } from "../components/common/EmptyState";
import { useInstruments } from "../hooks/useInstruments";

const ASSET_CLASSES = ["crypto", "equity", "fx", "index"];

export default function Universe() {
  const { data: instruments = [], isLoading, isError, create, toggleActive } = useInstruments();
  const [symbol, setSymbol] = useState("");
  const [assetClass, setAssetClass] = useState(ASSET_CLASSES[0]);
  const [exchange, setExchange] = useState("");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim() || !exchange.trim()) return;
    create.mutate(
      { symbol: symbol.trim(), assetClass, exchange: exchange.trim() },
      { onSuccess: () => setSymbol("") },
    );
  };

  return (
    <div className="universe-page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Universe</h1>
          <p className="page-sub">Manage tracked instruments across asset classes</p>
        </div>
      </div>

      <form className="universe-form" onSubmit={handleCreate}>
        <input
          className="search"
          placeholder="Symbol — e.g. RELIANCE.NS"
          aria-label="Symbol"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />
        <select
          aria-label="Asset class"
          value={assetClass}
          onChange={(e) => setAssetClass(e.target.value)}
        >
          {ASSET_CLASSES.map((ac) => (
            <option key={ac} value={ac}>
              {ac}
            </option>
          ))}
        </select>
        <input
          className="search"
          placeholder="Exchange — e.g. NSE"
          aria-label="Exchange"
          value={exchange}
          onChange={(e) => setExchange(e.target.value)}
        />
        <button type="submit" disabled={create.isPending}>
          Add instrument
        </button>
      </form>

      {isLoading && <p className="page-sub">Loading instruments…</p>}

      {isError && (
        <EmptyState
          glyph="⚠"
          title="Couldn't load instruments"
          message="The instruments service didn't respond. Check that the backend is running and reload."
        />
      )}

      {!isLoading && !isError && instruments.length === 0 && (
        <EmptyState
          glyph="◧"
          title="No instruments tracked"
          message="Add an instrument above to start tracking it in the universe."
        />
      )}

      {instruments.length > 0 && (
        <table className="universe-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Asset class</th>
              <th>Exchange</th>
              <th>Status</th>
              <th>Delay</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {instruments.map((i) => (
              <tr key={i.id}>
                <td>{i.symbol}</td>
                <td>{i.assetClass}</td>
                <td>{i.exchange}</td>
                <td>{i.active ? "Active" : "Inactive"}</td>
                <td>
                  <DelayBadge delayed={i.delayed} delayMinutes={i.delayMinutes} />
                </td>
                <td>
                  <button
                    type="button"
                    onClick={() => toggleActive.mutate({ id: i.id, active: !i.active })}
                    disabled={toggleActive.isPending}
                  >
                    {i.active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Disclaimer />
    </div>
  );
}
