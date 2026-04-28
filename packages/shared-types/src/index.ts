export type RepositoryDTO = {
  owner: string;
  name: string;
  stars_count: number;
  forks_count: number;
  watchers_count: number;
  open_issues_count: number;
  primary_language: string | null;
  created_at: string | null;
  last_push_at: string | null;
  last_release_at: string | null;
  archived: boolean;
  ingestion_source: string;
};

export type ScorecardDTO = {
  manipulation_risk: number;
  star_integrity: number;
  adoption_score: number;
  builder_score: number;
  durability_score: number;
  credibility_adjusted_traction: number;
  raw_features: Record<string, unknown>;
  subscores: Record<string, number>;
  reasons: Record<string, string[]>;
  snapshot_date: string;
};

export type TimelinePointDTO = {
  date: string;
  stars_delta: number;
  cumulative_stars: number;
};

export type TimelineDTO = {
  points: TimelinePointDTO[];
  suspicious_windows: Array<Record<string, unknown>>;
  overlays: Record<string, unknown[]>;
};

export type ClusterDTO = {
  cluster_id: number;
  time_window_start: string;
  time_window_end: string;
  account_count: number;
  repos_touched: number;
  cluster_score: number;
  reason: string | null;
};

export type AnalyzeResponse = {
  repository: RepositoryDTO;
  scorecard: ScorecardDTO;
  timeline: TimelineDTO;
  clusters: ClusterDTO[];
  disclaimer: string;
};

export type PeerCardDTO = {
  owner: string;
  name: string;
  stars_count: number;
  credibility_adjusted_traction: number;
  manipulation_risk: number;
};

export type CompareDTO = {
  base: PeerCardDTO;
  peers: PeerCardDTO[];
};
