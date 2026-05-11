/**
 * Root React app for the FinContext demo console.
 *
 * The shell mirrors the local React prototype's analyst-console style while
 * staying honest about backend state. Later commits fill each tab with live
 * Agent API data and clearly labeled sample fallbacks.
 */
import { useMemo, useState } from "react";

const TABS = [
  { id: "portfolio", num: "01", label: "Portfolio" },
  { id: "analysis", num: "02", label: "Analysis Run" },
  { id: "drift", num: "03", label: "Disclosure Drift" },
  { id: "evidence", num: "04", label: "Evidence" },
  { id: "risk", num: "05", label: "Risk Scores" },
  { id: "memo", num: "06", label: "Analyst Memo" },
  { id: "benchmark", num: "07", label: "AMD Benchmark" },
];

function StatusDot({ tone = "bad", pulse = false }) {
  return <span className={`status-dot ${tone}${pulse ? " pulse" : ""}`} />;
}

function Chip({ children, tone = "muted" }) {
  return <span className={`chip chip-${tone}`}>{children}</span>;
}

function ShellTabPlaceholder({ activeTab }) {
  const tab = TABS.find((item) => item.id === activeTab);
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">React console shell</div>
          <h2>{tab?.label}</h2>
        </div>
        <Chip>Sample shell</Chip>
      </div>
      <div className="empty-state">
        <strong>{tab?.label} content is being wired in the next commits.</strong>
        <span>
          This branch replaces the Gradio fallback with a Vite React console
          that deploys as a HuggingFace Static Space.
        </span>
      </div>
    </section>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("portfolio");
  const backend = useMemo(
    () => ({
      state: "offline",
      label: "Backend offline",
      detail:
        "Agent API is not reachable in local preview. Sample data will be clearly labeled.",
    }),
    [],
  );

  return (
    <div className="app-shell">
      <div className={`backend-banner ${backend.state}`}>
        <StatusDot tone="bad" />
        <span className="mono strong">{backend.label}</span>
        <span>{backend.detail}</span>
      </div>

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">FC</div>
          <div>
            <div className="brand-name">FinContext Agent</div>
            <div className="brand-sub">SEC Disclosure Drift</div>
          </div>
        </div>

        <button className="command-search" type="button">
          <span>Search filings, tickers, citations</span>
          <kbd>CMD K</kbd>
        </button>

        <div className="topbar-spacer" />

        <div className="top-meta">
          <span className="kv">
            <span className="kv-key">env</span>
            <span className="kv-val">local preview</span>
          </span>
          <span className="kv">
            <StatusDot tone="bad" />
            <span className="kv-key">api</span>
            <span className="kv-val">offline</span>
          </span>
        </div>
      </header>

      <nav className="tabbar" aria-label="Demo sections">
        {TABS.map((tab) => (
          <button
            className={`tab ${activeTab === tab.id ? "active" : ""}`}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            <span className="tab-num">{tab.num}</span>
            <span>{tab.label}</span>
          </button>
        ))}
        <div className="tabbar-spacer" />
        <Chip tone="info">React Static Space</Chip>
      </nav>

      <main className="content">
        <section className="hero-row">
          <div>
            <div className="eyebrow">Citation-grounded filing intelligence</div>
            <h1>SEC disclosure drift research console</h1>
            <p>
              Compare filing language changes, inspect citation-ready evidence,
              and keep every memo claim tied to source paragraphs.
            </p>
          </div>
          <aside className="status-card">
            <div className="eyebrow">Backend state</div>
            <strong>{backend.label}</strong>
            <p>{backend.detail}</p>
          </aside>
        </section>

        <ShellTabPlaceholder activeTab={activeTab} />
      </main>
    </div>
  );
}
