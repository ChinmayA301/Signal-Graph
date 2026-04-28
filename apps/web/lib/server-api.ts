import type { AnalyzeResponse, CompareDTO } from "@signalgraph/shared-types";

function apiBase(): string {
  return process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function fetchRepoReportServer(owner: string, name: string): Promise<AnalyzeResponse> {
  const response = await fetch(
    `${apiBase()}/repo/${encodeURIComponent(owner)}/${encodeURIComponent(name)}`,
    { cache: "no-store" },
  );
  return parseJson<AnalyzeResponse>(response);
}

export async function fetchCompareServer(owner: string, name: string, peers: string[]): Promise<CompareDTO | null> {
  if (peers.length === 0) {
    return null;
  }
  const params = new URLSearchParams();
  for (const peer of peers) {
    params.append("peers", peer);
  }
  const response = await fetch(
    `${apiBase()}/repo/${encodeURIComponent(owner)}/${encodeURIComponent(name)}/compare?${params.toString()}`,
    { cache: "no-store" },
  );
  return parseJson<CompareDTO>(response);
}
