/**
 * Smoke tests for the React demo console.
 *
 * These tests focus on user-visible behavior that must keep working while the
 * backend is still being wired: offline preview, tab navigation, and compliance
 * wording.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";

describe("App", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(async () => {
      throw new Error("offline");
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the offline sample portfolio preview", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText(/Backend offline/i).length).toBeGreaterThan(0);
    });
    expect(screen.getByText("AMD")).toBeInTheDocument();
    expect(screen.getByText("Sample preview")).toBeInTheDocument();
  });

  it("renders all major tabs without the backend", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /03 Disclosure Drift/i }));
    expect(screen.getByText("Export controls")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /04 Evidence/i }));
    expect(screen.getByText("AMD 10-K Item 1A paragraph 44")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /05 Risk Scores/i }));
    expect(screen.getByText("Holding-level risk movement")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /06 Analyst Memo/i }));
    expect(
      screen.getByText("This output is research assistance only and does not constitute investment advice."),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /07 AMD Benchmark/i }));
    expect(screen.getByText("No live number is displayed unless backend returns it.")).toBeInTheDocument();
  });

  it("does not render forbidden recommendation language in the default UI", async () => {
    const { container } = render(<App />);
    await waitFor(() => {
      expect(screen.getAllByText(/Backend offline/i).length).toBeGreaterThan(0);
    });

    expect(container.textContent.toLowerCase()).not.toMatch(
      /\b(buy|sell|hold|short|outperform|underperform)\b/,
    );
  });
});
