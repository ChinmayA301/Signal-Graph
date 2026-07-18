from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from signalgraph_scoring.features import RepoSnapshotInput, StarEventInput

_GRAPHQL_URL = "https://api.github.com/graphql"

# GitHub's REST /stargazers endpoint returns 404 for repos the requesting
# token doesn't own or collaborate on (confirmed against multiple tokens and
# well-known repos as of 2026-07; REST /contributors and /forks on the same
# repos work fine, so this is endpoint-specific, not a scope problem).
# GraphQL's stargazers connection has no such restriction and additionally
# exposes starredAt + account createdAt in one round trip, which is exactly
# what the manipulation-risk heuristics need.
_STARGAZERS_QUERY = """
query($owner: String!, $name: String!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    databaseId
    stargazerCount
    forkCount
    createdAt
    pushedAt
    openIssues: issues(states: OPEN) { totalCount }
    openPullRequests: pullRequests(states: OPEN) { totalCount }
    stargazers(first: $first, after: $after, orderBy: {field: STARRED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      edges {
        starredAt
        node {
          databaseId
          login
          createdAt
          followers { totalCount }
          repositories(privacy: PUBLIC, ownerAffiliations: OWNER) { totalCount }
        }
      }
    }
  }
}
"""

# Recent-activity signals (commits, releases) via the default branch and
# releases connections; merged-PR and opened-issue counts via search, since
# neither has a native "count in window" connection.
_ACTIVITY_QUERY = """
query($owner: String!, $name: String!, $since: GitTimestamp!, $prQuery: String!, $issueQuery: String!) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit { history(since: $since) { totalCount } }
      }
    }
    releases(last: 20, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { createdAt }
    }
  }
  prsMerged: search(query: $prQuery, type: ISSUE) { issueCount }
  issuesOpened: search(query: $issueQuery, type: ISSUE) { issueCount }
}
"""


@dataclass(frozen=True)
class LiveDataset:
    snapshot: RepoSnapshotInput
    star_events: list[StarEventInput]
    github_repo_id: Optional[int]
    peer_overlap_ratio: float


def _parse_github_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


async def _fetch_activity(client: httpx.AsyncClient, headers: dict, owner: str, name: str) -> dict[str, int]:
    """Best-effort: commits/PRs/issues/releases in recent windows. Falls back
    to zeros (durability/builder subscores degrade gracefully) rather than
    failing the whole analysis if search rate limits are hit."""
    now = datetime.now(timezone.utc)
    since_30d = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    since_30d_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    since_90d = now - timedelta(days=90)

    try:
        resp = await client.post(
            _GRAPHQL_URL,
            headers=headers,
            json={
                "query": _ACTIVITY_QUERY,
                "variables": {
                    "owner": owner,
                    "name": name,
                    "since": since_30d,
                    "prQuery": f"repo:{owner}/{name} is:pr is:merged merged:>={since_30d_date}",
                    "issueQuery": f"repo:{owner}/{name} is:issue created:>={since_30d_date}",
                },
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            return {"commits_last_30d": 0, "prs_merged_last_30d": 0, "issues_opened_last_30d": 0, "releases_last_90d": 0}

        repo_data = payload["data"]["repository"] or {}
        branch_ref = repo_data.get("defaultBranchRef") or {}
        commits = ((branch_ref.get("target") or {}).get("history") or {}).get("totalCount") or 0

        releases = (repo_data.get("releases") or {}).get("nodes") or []
        releases_90d = sum(
            1 for r in releases
            if (dt := _parse_github_datetime(r.get("createdAt"))) and dt >= since_90d
        )

        return {
            "commits_last_30d": int(commits),
            "prs_merged_last_30d": int((payload["data"].get("prsMerged") or {}).get("issueCount") or 0),
            "issues_opened_last_30d": int((payload["data"].get("issuesOpened") or {}).get("issueCount") or 0),
            "releases_last_90d": releases_90d,
        }
    except httpx.HTTPError:
        return {"commits_last_30d": 0, "prs_merged_last_30d": 0, "issues_opened_last_30d": 0, "releases_last_90d": 0}


async def fetch_live_dataset(owner: str, name: str, token: str) -> LiveDataset:
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for live ingestion")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    star_events: list[StarEventInput] = []
    repo: dict[str, Any] | None = None
    cursor: Optional[str] = None
    page = 1
    max_pages = 15  # MVP cap to respect rate limits; GH Archive path will replace this
    per_page = 100

    async with httpx.AsyncClient(timeout=30.0) as client:
        while page <= max_pages:
            resp = await client.post(
                _GRAPHQL_URL,
                headers=headers,
                json={
                    "query": _STARGAZERS_QUERY,
                    "variables": {"owner": owner, "name": name, "first": per_page, "after": cursor},
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("errors"):
                raise RuntimeError(f"GitHub GraphQL error: {payload['errors']}")

            repo_data = payload["data"]["repository"]
            if repo_data is None:
                raise RuntimeError(f"Repository {owner}/{name} not found")
            if repo is None:
                repo = repo_data

            edges = repo_data["stargazers"]["edges"]
            for edge in edges:
                user = edge["node"]
                user_id = user.get("databaseId")
                if not user_id:
                    continue
                starred_at = _parse_github_datetime(edge.get("starredAt")) or datetime.now(timezone.utc)
                star_events.append(
                    StarEventInput(
                        user_id=int(user_id),
                        starred_at=starred_at,
                        account_created_at=_parse_github_datetime(user.get("createdAt")),
                        public_repos=int((user.get("repositories") or {}).get("totalCount") or 0),
                        followers=int((user.get("followers") or {}).get("totalCount") or 0),
                    )
                )

            page_info = repo_data["stargazers"]["pageInfo"]
            if not page_info["hasNextPage"] or not edges:
                break
            cursor = page_info["endCursor"]
            page += 1

        if repo is None:
            raise RuntimeError(f"Repository {owner}/{name} not found")

        contributors_count = 1
        try:
            contrib_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/contributors?per_page=100&anon=false",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                follow_redirects=True,
            )
            contrib_resp.raise_for_status()
            contributors = contrib_resp.json()
            contributors_count = len(contributors) if isinstance(contributors, list) else 1
        except httpx.HTTPError:
            contributors_count = 1

        activity = await _fetch_activity(client, headers, owner, name)

        snapshot = RepoSnapshotInput(
            stars_count=int(repo.get("stargazerCount") or 0),
            forks_count=int(repo.get("forkCount") or 0),
            contributors_count=max(1, contributors_count),
            created_at=_parse_github_datetime(repo.get("createdAt")),
            last_push_at=_parse_github_datetime(repo.get("pushedAt")),
            # Matches REST's open_issues_count semantics: open issues + open PRs
            # (GitHub treats PRs as a special issue type internally).
            open_issues_count=(
                int((repo.get("openIssues") or {}).get("totalCount") or 0)
                + int((repo.get("openPullRequests") or {}).get("totalCount") or 0)
            ),
            releases_last_90d=activity["releases_last_90d"],
            commits_last_30d=activity["commits_last_30d"],
            issues_opened_last_30d=activity["issues_opened_last_30d"],
            prs_merged_last_30d=activity["prs_merged_last_30d"],
        )

        if not star_events:
            raise RuntimeError("No stargazers returned; repo may be empty or token lacks access")

        return LiveDataset(
            snapshot=snapshot,
            star_events=star_events,
            github_repo_id=int(repo["databaseId"]) if repo.get("databaseId") is not None else None,
            peer_overlap_ratio=0.0,
        )
