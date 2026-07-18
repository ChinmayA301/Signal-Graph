from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from signalgraph_scoring.features import RepoSnapshotInput, StarEventInput


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


async def fetch_live_dataset(owner: str, name: str, token: str) -> LiveDataset:
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for live ingestion")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        repo_resp = await client.get(f"https://api.github.com/repos/{owner}/{name}", headers=headers)
        repo_resp.raise_for_status()
        repo = repo_resp.json()

        contributors_count = 1
        try:
            contributors_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/contributors?per_page=100&anon=false",
                headers=headers,
            )
            contributors_resp.raise_for_status()
            contributors = contributors_resp.json()
            contributors_count = len(contributors) if isinstance(contributors, list) else 1
        except httpx.HTTPError:
            contributors_count = 1

        # Best-effort activity signals (may be rate limited on busy repos)
        commits_last_30d = 0
        prs_merged_last_30d = 0
        issues_opened_last_30d = 0
        releases_last_90d = 0

        snapshot = RepoSnapshotInput(
            stars_count=int(repo.get("stargazers_count") or 0),
            forks_count=int(repo.get("forks_count") or 0),
            contributors_count=max(1, contributors_count),
            created_at=_parse_github_datetime(repo.get("created_at")),
            last_push_at=_parse_github_datetime(repo.get("pushed_at")),
            open_issues_count=int(repo.get("open_issues_count") or 0),
            releases_last_90d=releases_last_90d,
            commits_last_30d=commits_last_30d,
            issues_opened_last_30d=issues_opened_last_30d,
            prs_merged_last_30d=prs_merged_last_30d,
        )

        star_events: list[StarEventInput] = []
        page = 1
        per_page = 100
        max_pages = 15  # MVP cap to respect rate limits; GH Archive path will replace this

        while page <= max_pages:
            stars_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/stargazers?per_page={per_page}&page={page}",
                headers={**headers, "Accept": "application/vnd.github.star+json"},
            )
            stars_resp.raise_for_status()
            batch = stars_resp.json()
            if not batch:
                break

            for entry in batch:
                user = entry.get("user") or {}
                user_id = int(user.get("id") or 0)
                if user_id == 0:
                    continue
                starred_at = _parse_github_datetime(entry.get("starred_at")) or datetime.now(timezone.utc)
                created_at = _parse_github_datetime(user.get("created_at"))
                star_events.append(
                    StarEventInput(
                        user_id=user_id,
                        starred_at=starred_at,
                        account_created_at=created_at,
                        public_repos=int(user.get("public_repos") or 0),
                        followers=int(user.get("followers") or 0),
                    )
                )

            if len(batch) < per_page:
                break
            page += 1

        if not star_events:
            raise RuntimeError("No stargazers returned; repo may be empty or token lacks access")

        return LiveDataset(
            snapshot=snapshot,
            star_events=star_events,
            github_repo_id=int(repo.get("id")) if repo.get("id") is not None else None,
            peer_overlap_ratio=0.0,
        )
