import { heatColor } from "../../lib/heatColor";
import type { WatchlistTileData } from "../../stores/watchlistStore";

/** Presentational live-price tile; background heat-mapped by daily % change. */
export function WatchlistTile({ symbol, last, changePct }: WatchlistTileData) {
  const up = changePct >= 0;
  return (
    <div
      className="wl-tile"
      data-testid={`tile-${symbol}`}
      style={{ background: heatColor(changePct) }}
    >
      <div className="wl-tile-top">
        <span className="wl-sym">{symbol}</span>
        <span className={`wl-arrow ${up ? "up" : "down"}`} aria-hidden="true">
          {up ? "▲" : "▼"}
        </span>
      </div>
      <div className="wl-price num" data-testid={`tile-${symbol}-price`}>
        {last.toFixed(2)}
      </div>
      <div className="wl-change num" data-testid={`tile-${symbol}-change`}>
        {(changePct * 100).toFixed(2)}%
      </div>
    </div>
  );
}
