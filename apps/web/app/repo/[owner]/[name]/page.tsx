import type { CompareDTO } from "@signalgraph/shared-types";

import { RiskBadge } from "@/components/RiskBadge";
import { TimelineChart } from "@/components/TimelineChart";
import { fetchCompareServer, fetchRepoReportServer } from "@/lib/server-api";

export const dynamic = "force-dynamic";

type PageProps = {
  params: { owner: string; name: string };
  searchParams?: Record<string, string | string[] | undefined>;
};

function normalizePeers(searchParams: PageProps["searchParams"]): string[] {
  const raw = searchParams?.peers;
  if (!raw) {
    return [];
  }
  return (Array.isArray(raw) ? raw : [raw]).map((value) => value.trim()).filter(Boolean);
}

export default async function RepoPage({ params, searchParams }: PageProps) {
  const owner = decodeURIComponent(params.owner);
  const name = decodeURIComponent(params.name);
  const peers = normalizePeers(searchParams);

  let data;
  try {
    data = await fetchRepoReportServer(owner, name);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load repository";
    return (
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Unable to load report</h2>
        <p className="muted">{message}</p>
        <p className="muted" style={{ marginTop: 12 }}>
          Run an analysis from the home page first, or call POST <code>/analyze</code> for this repository.
        </p>
      </div>
    );
  }

  let compare: CompareDTO | null = null;
  if (peers.length > 0) {
    try {
      compare = await fetchCompareServer(owner, name, peers);
    } catch {
      compare = null;
    }
  }

  const score = data.scorecard;

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h1 style={{ margin: 0, letterSpacing: "-0.03em" }}>
              {data.repository.owner}/{data.repository.name}
            </h1>
            <p className="muted" style={{ marginTop: 8, marginBottom: 0 }}>
              Ingestion source: <strong>{data.repository.ingestion_source}</strong>
            </p>
          </div>
          <RiskBadge manipulationRisk={score.manipulation_risk} />
        </div>

        <div className="grid cols-3" style={{ marginTop: 16 }}>
          <Metric label="GitHub stars (raw)" value={data.repository.stars_count.toLocaleString()} />
          <Metric
            label="Credibility-adjusted traction"
            value={score.credibility_adjusted_traction.toFixed(1)}
            hint="Weighted blend that down-weights raw popularity."
          />
          <Metric label="Star integrity" value={score.star_integrity.toFixed(1)} />
          <Metric label="Adoption" value={score.adoption_score.toFixed(1)} />
          <Metric label="Builder quality" value={score.builder_score.toFixed(1)} />
          <Metric label="Durability" value={score.durability_score.toFixed(1)} />
        </div>

        <p className="muted" style={{ marginTop: 14, lineHeight: 1.55 }}>
          {data.disclaimer}
        </p>
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Star timeline</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Orange bands mark days where daily star velocity is an outlier versus the repo&apos;s own baseline (heuristic).
        </p>
        <TimelineChart timeline={data.timeline} />
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Why these scores?</h2>
        <ScoreExplain title="Manipulation risk" items={score.reasons.manipulation_risk ?? []} />
        <ScoreExplain title="Star integrity" items={score.reasons.star_integrity ?? []} />
        <details className="explain" style={{ marginTop: 12 }}>
          <summary>Raw feature snapshot</summary>
          <pre
            style={{
              overflow: "auto",
              fontSize: 12,
              background: "#0b1220",
              color: "#e2e8f0",
              padding: 12,
              borderRadius: 10,
            }}
          >
            {JSON.stringify(score.raw_features, null, 2)}
          </pre>
        </details>
      </div>

      {compare ? (
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>Peer comparison</h2>
          <p className="muted" style={{ marginTop: 6 }}>
            Peers were loaded from the query string, e.g.{" "}
            <code>?peers=facebook/react&peers=vercel/next.js</code>
          </p>
          <div className="grid cols-3" style={{ marginTop: 12 }}>
            <PeerCard title="Base" peer={compare.base} />
            {compare.peers.map((peer) => (
              <PeerCard key={`${peer.owner}/${peer.name}`} title="Peer" peer={peer} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12 }}>
      <div className="muted" style={{ fontSize: 12 }}>
        {label}
      </div>
      <div style={{ fontSize: 22, fontWeight: 750, marginTop: 6 }}>{value}</div>
      {hint ? (
        <div className="muted" style={{ fontSize: 12, marginTop: 6, lineHeight: 1.4 }}>
          {hint}
        </div>
      ) : null}
    </div>
  );
}

function ScoreExplain({ title, items }: { title: string; items: string[] }) {
  return (
    <details className="explain" style={{ marginTop: 10 }}>
      <summary>
        {title} ({items.length} notes)
      </summary>
      <ul style={{ marginTop: 8 }}>
        {items.map((item) => (
          <li key={item} style={{ marginBottom: 6 }}>
            {item}
          </li>
        ))}
      </ul>
    </details>
  );
}

function PeerCard({ title, peer }: { title: string; peer: CompareDTO["base"] }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12 }}>
      <div className="muted" style={{ fontSize: 12 }}>
        {title}
      </div>
      <div style={{ fontWeight: 800, marginTop: 6 }}>
        {peer.owner}/{peer.name}
      </div>
      <div className="muted" style={{ marginTop: 10, fontSize: 13 }}>
        Stars: <strong>{peer.stars_count.toLocaleString()}</strong>
      </div>
      <div className="muted" style={{ marginTop: 6, fontSize: 13 }}>
        Adjusted traction: <strong>{peer.credibility_adjusted_traction.toFixed(1)}</strong>
      </div>
      <div className="muted" style={{ marginTop: 6, fontSize: 13 }}>
        Manipulation risk: <strong>{peer.manipulation_risk.toFixed(1)}</strong>
      </div>
    </div>
  );
}
