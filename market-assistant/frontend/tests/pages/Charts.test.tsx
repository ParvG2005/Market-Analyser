import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ChartsPage } from "../../src/pages/Charts";

vi.mock("lightweight-charts", () => {
  const series = () => ({ setData: vi.fn(), applyOptions: vi.fn() });
  return {
    ColorType: { Solid: "solid" },
    createChart: () => ({
      addCandlestickSeries: series,
      addHistogramSeries: series,
      addLineSeries: series,
      priceScale: () => ({ applyOptions: vi.fn() }),
      applyOptions: vi.fn(),
      remove: vi.fn(),
    }),
  };
});

class FakeWebSocket {
  onopen: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  onclose: (() => void) | null = null;
  send() {}
  close() {}
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeWebSocket as unknown as typeof WebSocket);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ json: async () => [] }));
});

describe("ChartsPage", () => {
  it("renders symbol search, TF switcher, overlays, and disclaimer", async () => {
    render(<ChartsPage />);
    expect(screen.getByTestId("symbol-search")).toBeInTheDocument();
    expect(screen.getByTestId("tf-switcher")).toBeInTheDocument();
    expect(screen.getByTestId("indicator-overlays")).toBeInTheDocument();
    expect(screen.getByText(/Educational analysis/)).toBeInTheDocument();
  });

  it("switches active timeframe tab when clicked", async () => {
    render(<ChartsPage />);
    const fiveMinTab = screen.getByRole("tab", { name: "5m" });
    fireEvent.click(fiveMinTab);
    await waitFor(() => expect(fiveMinTab).toHaveAttribute("aria-selected", "true"));
  });
});
