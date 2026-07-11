export interface CorrelationVM {
  symbols: string[];
  matrix: number[][];
}

/** Diverging fill over the panel surface: red (−1) ↔ transparent (0) ↔ green (+1).
 * Magnitude sets alpha so 0 reads as the neutral surface; the printed value is
 * the secondary (non-color) encoding, so it stays legible under CVD. */
function cellColor(v: number): string {
  const t = Math.max(-1, Math.min(1, v));
  const alpha = 0.12 + 0.55 * Math.abs(t);
  return t >= 0 ? `rgba(18, 133, 90, ${alpha})` : `rgba(200, 50, 75, ${alpha})`;
}

export function CorrelationMatrix({ data }: { data: CorrelationVM }) {
  return (
    <div className="matrix-scroll">
      <table className="correlation-matrix" data-testid="correlation-matrix">
        <thead>
          <tr>
            <th aria-label="symbol" />
            {data.symbols.map((s) => (
              <th key={s}>{s}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.symbols.map((rowSym, r) => (
            <tr key={rowSym}>
              <th scope="row">{rowSym}</th>
              {data.matrix[r].map((v, c) => (
                <td
                  key={data.symbols[c]}
                  className="num"
                  style={{ background: cellColor(v) }}
                  title={`${rowSym} · ${data.symbols[c]}: ${v.toFixed(2)}`}
                >
                  {v.toFixed(2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
