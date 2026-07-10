import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../src/App";
import { createTestRouter } from "../src/router";

const ROUTES: Array<[string, string]> = [
  ["/", "Home"],
  ["/charts", "Charts"],
  ["/scanner", "Scanner"],
  ["/strategies", "Strategies"],
  ["/trends", "Trends"],
  ["/chat", "Chat"],
  ["/settings", "Settings"],
];

describe("App", () => {
  it("renders the disclaimer footer", () => {
    render(<App router={createTestRouter("/")} />);

    expect(
      screen.getByText(
        "Educational analysis. Not investment advice. Past performance ≠ future results."
      )
    ).toBeInTheDocument();
  });

  it.each(ROUTES)("mounts the %s page at %s", (path, heading) => {
    render(<App router={createTestRouter(path)} />);

    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  });
});
