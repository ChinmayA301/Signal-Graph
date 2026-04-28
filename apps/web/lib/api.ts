import type { AnalyzeResponse, CompareDTO } from "@signalgraph/shared-types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function analyzeRepo(repoUrl: string, forceMock?: boolean): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl, force_mock: forceMock ?? false }),
  });
  return parseJson<AnalyzeResponse>(response);
}

export async function fetchRepoReport(owner: string, name: string): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE}/repo/${encodeURIComponent(owner)}/${encodeURIComponent(name)}`, {
    cache: "no-store",
  });
  return parseJson<AnalyzeResponse>(response);
}

export async function fetchCompare(owner: string, name: string, peers: string[]): Promise<CompareDTO> {
  const params = new URLSearchParams();
  for (const peer of peers) {
    params.append("peers", peer);
  }
  const response = await fetch(
    `${API_BASE}/repo/${encodeURIComponent(owner)}/${encodeURIComponent(name)}/compare?${params.toString()}`,
    { cache: "no-store" },
  );
  return parseJson<CompareDTO>(response);
}
