"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { analyzeRepo } from "@/lib/api";
import { parseGithubRepoUrl } from "@/lib/github";

export default function HomePage() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("https://github.com/microsoft/vscode");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const parsed = parseGithubRepoUrl(repoUrl);
      await analyzeRepo(repoUrl, false);
      router.push(`/repo/${encodeURIComponent(parsed.owner)}/${encodeURIComponent(parsed.name)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to analyze repository");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <h1 style={{ marginTop: 0, letterSpacing: "-0.03em" }}>Repository diligence</h1>
      <p className="muted" style={{ marginTop: 8, lineHeight: 1.5 }}>
        Paste a public GitHub repository URL to generate a manipulation-risk-aware scorecard. Language stays probabilistic:
        suspicious patterns, not accusations.
      </p>

      <form onSubmit={onSubmit} style={{ marginTop: 18, display: "grid", gap: 12 }}>
        <label className="muted" style={{ fontSize: 13 }}>
          GitHub repository URL
          <input className="url" style={{ marginTop: 6 }} value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} />
        </label>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button className="primary" type="submit" disabled={loading}>
            {loading ? "Analyzing…" : "Run analysis"}
          </button>
          <span className="muted" style={{ fontSize: 13 }}>
            Mock mode is on by default, so the demo runs end-to-end without any GitHub token.
          </span>
        </div>
        {error ? (
          <pre style={{ whiteSpace: "pre-wrap", color: "var(--risk-high)", margin: 0, fontSize: 13 }}>{error}</pre>
        ) : null}
      </form>
    </div>
  );
}
