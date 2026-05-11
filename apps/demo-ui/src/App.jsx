/**
 * Root React app for the FinContext demo console.
 *
 * The shell mirrors the local React prototype's analyst-console style while
 * staying honest about backend state. Later commits fill each tab with live
 * Agent API data and clearly labeled sample fallbacks.
 */
import { useEffect, useMemo, useState } from "react";
import { SAMPLE_PORTFOLIO } from "./data/sampleData.js";
import { AgentApiClient, ApiError } from "./lib/apiClient.js";
import { getRuntimeConfig } from "./lib/config.js";

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

function PortfolioTab({ portfolio, client, backendOnline }) {
  const [portfolioName, setPortfolioName] = useState(portfolio.name);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(
    backendOnline
      ? "Choose a CSV file to upload it to Agent API."
      : "Agent API is offline. Showing sample portfolio data.",
  );
  const [uploadedPortfolioId, setUploadedPortfolioId] = useState("");

  async function uploadPortfolio() {
    if (!file) {
      setStatus("Choose a CSV file before uploading.");
      return;
    }
    try {
      setStatus("Uploading CSV to Agent API...");
      const result = await client.uploadPortfolio(file, portfolioName);
      setUploadedPortfolioId(result.portfolio_id || result.portfolioId || "");
      setStatus("Portfolio uploaded successfully.");
    } catch (error) {
      setStatus(formatError(error));
    }
  }

  return (
    <section className="grid grid-portfolio">
      <div className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">{portfolio.sourceLabel}</div>
            <h2>Portfolio holdings</h2>
          </div>
          <Chip tone={backendOnline ? "ok" : "warn"}>
            {backendOnline ? "Agent API available" : "Sample preview"}
          </Chip>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Shares</th>
                <th>Market value</th>
                <th>Weight</th>
                <th>Sector</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.holdings.map((holding) => (
                <tr key={holding.ticker}>
                  <td className="ticker">{holding.ticker}</td>
                  <td>{holding.name}</td>
                  <td>{holding.shares.toLocaleString()}</td>
                  <td>{formatCurrency(holding.marketValue)}</td>
                  <td>{formatPercent(holding.weight)}</td>
                  <td>{holding.sector}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <aside className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Agent API upload</div>
            <h2>Create portfolio</h2>
          </div>
        </div>
        <div className="panel-body form-stack">
          <label>
            Portfolio name
            <input
              value={portfolioName}
              onChange={(event) => setPortfolioName(event.target.value)}
            />
          </label>
          <label>
            CSV file
            <input
              accept=".csv,text/csv"
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <button className="primary-button" onClick={uploadPortfolio} type="button">
            Upload to Agent API
          </button>
          <div className="callout">{status}</div>
          {uploadedPortfolioId && (
            <div className="mini-kv">
              <span>portfolio_id</span>
              <strong>{uploadedPortfolioId}</strong>
            </div>
          )}
        </div>
      </aside>
    </section>
  );
}

function AnalysisTab({ client, backendOnline, defaultPortfolioId }) {
  const [portfolioId, setPortfolioId] = useState(defaultPortfolioId);
  const [question, setQuestion] = useState(
    "What changed in supply-chain or customer concentration risk for my semiconductor holdings?",
  );
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState(
    backendOnline
      ? "Ready to start an Agent API analysis job."
      : "Agent API is offline. This tab is ready for live wiring once the API is reachable.",
  );
  const [jobPayload, setJobPayload] = useState(null);

  async function startAnalysis() {
    if (!portfolioId.trim()) {
      setStatus("Enter a portfolio_id before starting analysis.");
      return;
    }
    try {
      setStatus("Creating analysis job...");
      const result = await client.startAnalysis({
        portfolioId: portfolioId.trim(),
        question: question.trim() || null,
      });
      const nextJobId = result.job_id || result.jobId || "";
      setJobId(nextJobId);
      setJobPayload(result);
      setStatus(nextJobId ? `Analysis job created: ${nextJobId}` : "Analysis job created.");
    } catch (error) {
      setStatus(formatError(error));
    }
  }

  async function refreshJob() {
    if (!jobId.trim()) {
      setStatus("Enter a job_id before refreshing status.");
      return;
    }
    try {
      setStatus("Refreshing job status...");
      const result = await client.getJob(jobId.trim());
      setJobPayload(result);
      setStatus(result.status ? `Current job status: ${result.status}` : "Job status refreshed.");
    } catch (error) {
      setStatus(formatError(error));
    }
  }

  return (
    <section className="grid grid-analysis">
      <div className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Analysis request</div>
            <h2>Run disclosure drift analysis</h2>
          </div>
          <Chip tone={backendOnline ? "ok" : "warn"}>
            {backendOnline ? "Live endpoint" : "Offline controls"}
          </Chip>
        </div>
        <div className="panel-body form-stack">
          <label>
            Portfolio ID
            <input value={portfolioId} onChange={(event) => setPortfolioId(event.target.value)} />
          </label>
          <label>
            Research question
            <textarea
              rows="5"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </label>
          <div className="button-row">
            <button className="primary-button" onClick={startAnalysis} type="button">
              Start analysis
            </button>
            <button className="secondary-button" onClick={refreshJob} type="button">
              Refresh job
            </button>
          </div>
          <label>
            Job ID
            <input value={jobId} onChange={(event) => setJobId(event.target.value)} />
          </label>
        </div>
      </div>

      <aside className="panel">
        <div className="panel-head">
          <div>
            <div className="eyebrow">Backend response</div>
            <h2>Job status</h2>
          </div>
        </div>
        <div className="panel-body form-stack">
          <div className="callout">{status}</div>
          <pre className="json-block">{JSON.stringify(jobPayload || { status }, null, 2)}</pre>
        </div>
      </aside>
    </section>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("portfolio");
  const [backend, setBackend] = useState({
    state: "checking",
    label: "Checking backend",
    detail: "Probing Agent API health endpoint.",
  });
  const config = useMemo(() => getRuntimeConfig(), []);
  const client = useMemo(
    () => new AgentApiClient({ baseUrl: config.agentApiUrl }),
    [config.agentApiUrl],
  );
  const backendOnline = backend.state === "online";

  useEffect(() => {
    let cancelled = false;
    client
      .health()
      .then(() => {
        if (!cancelled) {
          setBackend({
            state: "online",
            label: "Backend online",
            detail: `Agent API is reachable at ${config.agentApiUrl}.`,
          });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setBackend({
            state: "offline",
            label: "Backend offline",
            detail:
              error instanceof ApiError
                ? error.message
                : `Agent API is unreachable at ${config.agentApiUrl}.`,
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [client, config.agentApiUrl]);

  return (
    <div className="app-shell">
      <div className={`backend-banner ${backend.state}`}>
        <StatusDot tone={backendOnline ? "ok" : backend.state === "checking" ? "warn" : "bad"} />
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
            <span className="kv-val">{config.environment}</span>
          </span>
          <span className="kv">
            <StatusDot tone={backendOnline ? "ok" : "bad"} />
            <span className="kv-key">api</span>
            <span className="kv-val">{backendOnline ? "online" : "offline"}</span>
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

        {activeTab === "portfolio" && (
          <PortfolioTab portfolio={SAMPLE_PORTFOLIO} client={client} backendOnline={backendOnline} />
        )}
        {activeTab === "analysis" && (
          <AnalysisTab
            client={client}
            backendOnline={backendOnline}
            defaultPortfolioId={SAMPLE_PORTFOLIO.id}
          />
        )}
        {!["portfolio", "analysis"].includes(activeTab) && (
          <ShellTabPlaceholder activeTab={activeTab} />
        )}
      </main>
    </div>
  );
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value) {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatError(error) {
  return error instanceof Error ? error.message : "Unexpected Agent API error.";
}
