"""Same-day co-adoption for stargazers, via GitHub GraphQL.

For each sampled stargazer, count how many OTHER repositories they starred on the same UTC day
as the target repo. This fills ``StarEventInput.same_day_other_stars``, which drives the
``co_adoption_farm_share`` signal (manufactured-virality Phase B: lockstep-flagged repos have a
median 0.96 of stargazers with 20+ other same-day stars, normal repos 0.05).

Scope: this needs stargazer logins. Since 30 June 2026 GitHub lists a repo's stargazers only
to its admins and collaborators, so for other repos the live ingest gets no stargazers and this
step has nothing to probe. Validation against GH Archive (manufactured-virality PHASE_B.md, B6):
on lockstep repos that still exist, the GraphQL farm share tracks GH Archive (0.83-0.86 vs
0.85-0.95 on the farm-heavy ones; normal repos <= 0.10); after GitHub deletes a campaign's
repos the evidence is gone, so it reads ~0.

Why GraphQL rather than GH Archive: a per-analysis BigQuery scan over every day a repo received
stars is too large for the free tier. GraphQL reuses the token SignalGraph already has.

Differences from the GH Archive measure the thresholds were set on:
- GraphQL shows stars that still exist. Stars later removed, and deleted or suspended accounts,
  are missing, so counts can only be equal or lower. (Deleted accounts get ``None``.)
- To bound cost, only a sample of stargazers is probed (``max_users``), and each user's star
  list is read newest-first for at most ``max_pages`` pages. A user who has starred more than
  that since the target day is unresolved: reported as a lower
  bound when it already reaches the farm threshold, otherwise ``None``.

Best-effort throughout: any failure leaves the affected users at ``None``. The scorer treats
``None`` as missing and stays inactive below 8 resolved stargazers, so analysis never fails
because of this step.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from typing import Optional, Sequence

import httpx

from signalgraph_scoring.features import StarEventInput

logger = logging.getLogger(__name__)

_GRAPHQL_URL = "https://api.github.com/graphql"
FARM_THRESHOLD = 20  # matches co_adoption_farm_share in signalgraph_scoring.features


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _utc_day(value: datetime | str) -> date:
    dt = value if isinstance(value, datetime) else _parse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


@dataclass
class _Probe:
    """Progress for one stargazer."""
    login: str
    day: date
    count: int = 0
    cursor: Optional[str] = None
    pages: int = 0
    done: bool = False
    truncated: bool = False   # stopped at max_pages before reaching the target day's end
    value: Optional[int] = None


def build_query(n: int, per_page: int) -> str:
    var_defs = ", ".join(f"$l{i}: String!, $c{i}: String" for i in range(n))
    body = "\n".join(
        f"  u{i}: user(login: $l{i}) {{ starredRepositories(first: {per_page}, after: $c{i}, "
        f"orderBy: {{field: STARRED_AT, direction: DESC}}) {{ pageInfo {{ hasNextPage endCursor }} "
        f"edges {{ starredAt node {{ databaseId }} }} }} }}"
        for i in range(n)
    )
    return f"query({var_defs}) {{\n{body}\n}}"


def consume_page(probe: _Probe, conn: Optional[dict], target_repo_id: Optional[int], max_pages: int) -> None:
    """Advance one probe with one page of its newest-first star list."""
    if conn is None:            # deleted / suspended account, or field unavailable
        probe.done, probe.value = True, None
        return
    probe.pages += 1
    for edge in conn.get("edges") or []:
        starred = _parse(edge.get("starredAt"))
        if starred is None:
            continue
        d = starred.astimezone(timezone.utc).date()
        if d > probe.day:
            continue
        if d < probe.day:       # walked past the target day: count is complete
            probe.done, probe.value = True, probe.count
            return
        node = edge.get("node") or {}
        if target_repo_id is None or node.get("databaseId") != target_repo_id:
            probe.count += 1
    info = conn.get("pageInfo") or {}
    if not info.get("hasNextPage"):
        probe.done, probe.value = True, probe.count
    elif probe.pages >= max_pages:
        probe.done, probe.truncated = True, True
        probe.value = probe.count if probe.count >= FARM_THRESHOLD else None   # lower bound or unknown
    else:
        probe.cursor = info.get("endCursor")


def sample_indices(n: int, max_users: int) -> list[int]:
    """Evenly spaced indices, so the sample covers the whole fetched star history."""
    if n <= max_users:
        return list(range(n))
    step = n / max_users
    return sorted({int(i * step) for i in range(max_users)})


@dataclass
class CoadoptionResult:
    events: list[StarEventInput]
    sampled: int = 0
    resolved: int = 0
    lower_bounds: int = 0
    queries: int = 0
    errors: list[str] = field(default_factory=list)


async def enrich_same_day_stars(
    client: httpx.AsyncClient,
    headers: dict,
    star_events: Sequence[StarEventInput],
    logins: dict[int, str],
    target_repo_id: Optional[int],
    *,
    max_users: int = 60,
    batch_size: int = 5,
    per_page: int = 50,
    max_pages: int = 4,
    concurrency: int = 1,
    time_budget_s: float = 30.0,
) -> CoadoptionResult:
    """Fill ``same_day_other_stars`` for an evenly spaced sample of stargazers.

    Sizing (measured Nov 2026): GitHub spends about 1 s of server time per user's star page;
    batches of 10 users x 100 stars time out (502 after ~10 s), and three queries in flight
    trip the secondary rate limit (403). So: small batches, one at a time, and a 30 s budget,
    which typically resolves a few dozen stargazers. 30 stargazers estimate a farm share with
    standard error <= 0.09, against a 0.05 vs 0.96 normal/farm gap. On a 403/429 the step stops
    and leaves the rest unresolved rather than retrying.
    """
    events = list(star_events)
    idx = [i for i in sample_indices(len(events), max_users) if events[i].user_id in logins]
    probes = {i: _Probe(login=logins[events[i].user_id], day=_utc_day(events[i].starred_at)) for i in idx}
    result = CoadoptionResult(events=events, sampled=len(probes))
    sem = asyncio.Semaphore(max(1, concurrency))
    loop = asyncio.get_running_loop()
    deadline = loop.time() + time_budget_s

    stop = {"rate_limited": False}

    async def run_chunk(chunk: list[int]) -> None:
        if stop["rate_limited"]:
            for i in chunk:
                probes[i].done = True
            return
        if loop.time() > deadline:
            for i in chunk:
                probes[i].done = True
            if "time_budget" not in result.errors:
                result.errors.append("time_budget")
            return
        variables = {}
        for j, i in enumerate(chunk):
            variables[f"l{j}"] = probes[i].login
            variables[f"c{j}"] = probes[i].cursor
        try:
            async with sem:
                result.queries += 1
                resp = await client.post(_GRAPHQL_URL, headers=headers,
                                         json={"query": build_query(len(chunk), per_page), "variables": variables})
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if len(chunk) > 1 and status in (502, 504):     # GitHub query timeout: retry users one at a time
                for i in chunk:
                    await run_chunk([i])
                return
            if status in (403, 429):                         # secondary rate limit: stop the whole step
                stop["rate_limited"] = True
            result.errors.append(f"http_{status}" if status else type(exc).__name__)
            logger.warning("Co-adoption fetch failed for %d stargazers: %s", len(chunk), exc)
            for i in chunk:
                probes[i].done = True
            return
        data = payload.get("data") or {}
        if not data and payload.get("errors"):
            result.errors.append("graphql")
            for i in chunk:
                probes[i].done = True
            return
        for j, i in enumerate(chunk):
            user = data.get(f"u{j}")
            consume_page(probes[i], user.get("starredRepositories") if user else None, target_repo_id, max_pages)

    while True:
        pending = [i for i, p in probes.items() if not p.done]
        if not pending:
            break
        await asyncio.gather(*(run_chunk(pending[k:k + batch_size]) for k in range(0, len(pending), batch_size)))

    for i, p in probes.items():
        if p.value is not None:
            events[i] = replace(events[i], same_day_other_stars=p.value)
            result.resolved += 1
            if p.truncated:
                result.lower_bounds += 1
    return result
