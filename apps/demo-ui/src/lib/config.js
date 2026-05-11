/**
 * Runtime configuration for the static React Space.
 *
 * Static browser apps cannot keep secrets. This file intentionally reads only
 * public configuration such as the Agent API base URL. Demo authentication,
 * CORS, and rate limiting must be handled by the Agent API.
 */

const DEFAULT_AGENT_API_URL = "http://localhost:8090";

export function getRuntimeConfig() {
  const hfVariables = globalThis.window?.huggingface?.variables ?? {};
  const envUrl = import.meta.env.VITE_AGENT_API_URL;
  const hfUrl = hfVariables.AGENT_API_URL;

  return {
    agentApiUrl: normalizeUrl(envUrl || hfUrl || DEFAULT_AGENT_API_URL),
    environment: import.meta.env.MODE || "development",
  };
}

export function normalizeUrl(url) {
  return String(url || DEFAULT_AGENT_API_URL).replace(/\/+$/, "");
}
