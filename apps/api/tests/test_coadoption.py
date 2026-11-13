"""Same-day co-adoption enrichment against a fake GitHub GraphQL endpoint (no network)."""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.services.coadoption_ingest import (
    _Probe,
    consume_page,
    enrich_same_day_stars,
    sample_indices,
)
from signalgraph_scoring.features import StarEventInput, co_adoption_farm_share

TARGET = 999
DAY = datetime(2024, 5, 10, 12, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _stars(same_day_others: int, *, newer: int = 0, include_target: bool = True) -> list[dict]:
    """Newest-first star list: `newer` stars after the target day, then the target day, then older."""
    out = [{"starredAt": _iso(DAY + timedelta(days=2, minutes=i)), "node": {"databaseId": 10_000 + i}} for i in range(newer)]
    day_stars = [{"starredAt": _iso(DAY + timedelta(minutes=i)), "node": {"databaseId": 20_000 + i}} for i in range(same_day_others)]
    if include_target:
        day_stars.append({"starredAt": _iso(DAY - timedelta(minutes=5)), "node": {"databaseId": TARGET}})
    out += sorted(day_stars, key=lambda e: e["starredAt"], reverse=True)
    out += [{"starredAt": _iso(DAY - timedelta(days=3 + i)), "node": {"databaseId": 30_000 + i}} for i in range(5)]
    return out


def _fake_github(star_lists: dict[str, list[dict]], per_page_seen: list[int]):
    """Serve aliased `user(login:) { starredRepositories(first:, after:) }` queries with cursor paging."""
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        per_page = int(re.search(r"first: (\d+)", body["query"]).group(1))
        per_page_seen.append(per_page)
        data = {}
        for key, login in body["variables"].items():
            if not key.startswith("l"):
                continue
            j = key[1:]
            stars = star_lists.get(login)
            if stars is None:
                data[f"u{j}"] = None
                continue
            start = int(body["variables"].get(f"c{j}") or 0)
            page = stars[start:start + per_page]
            end = start + len(page)
            data[f"u{j}"] = {"starredRepositories": {
                "pageInfo": {"hasNextPage": end < len(stars), "endCursor": str(end)},
                "edges": page,
            }}
        return httpx.Response(200, json={"data": data})
    return httpx.MockTransport(handler)


def _run(events, logins, star_lists, **kw):
    seen: list[int] = []
    async def go():
        async with httpx.AsyncClient(transport=_fake_github(star_lists, seen)) as client:
            return await enrich_same_day_stars(client, {}, events, logins, TARGET, **kw)
    return asyncio.run(go()), seen


def test_counts_other_same_day_stars_excluding_target() -> None:
    events = [StarEventInput(user_id=1, starred_at=DAY - timedelta(minutes=5))]
    res, _ = _run(events, {1: "alice"}, {"alice": _stars(3, newer=4)})
    assert res.events[0].same_day_other_stars == 3
    assert (res.sampled, res.resolved) == (1, 1)


def test_pages_through_newer_stars() -> None:
    events = [StarEventInput(user_id=1, starred_at=DAY)]
    res, _ = _run(events, {1: "bob"}, {"bob": _stars(2, newer=7)}, per_page=3, max_pages=10)
    assert res.events[0].same_day_other_stars == 2
    assert res.queries >= 3


def test_truncated_heavy_starrer_is_lower_bound_or_unknown() -> None:
    events = [StarEventInput(user_id=1, starred_at=DAY), StarEventInput(user_id=2, starred_at=DAY)]
    lists = {"farm": _stars(40), "light": _stars(2, newer=50)}
    res, _ = _run(events, {1: "farm", 2: "light"}, lists, per_page=10, max_pages=3)
    assert res.events[0].same_day_other_stars is not None and res.events[0].same_day_other_stars >= 20
    assert res.events[1].same_day_other_stars is None   # never reached the target day
    assert res.lower_bounds == 1


def test_deleted_account_and_missing_login_stay_none() -> None:
    events = [StarEventInput(user_id=1, starred_at=DAY), StarEventInput(user_id=2, starred_at=DAY)]
    res, _ = _run(events, {1: "ghost"}, {})
    assert res.events[0].same_day_other_stars is None
    assert res.events[1].same_day_other_stars is None
    assert res.sampled == 1


def test_http_failure_is_best_effort() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502)
    events = [StarEventInput(user_id=1, starred_at=DAY)]
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as client:
            return await enrich_same_day_stars(client, {}, events, {1: "a"}, TARGET)
    res = asyncio.run(go())
    assert res.events[0].same_day_other_stars is None and res.errors


def test_farm_campaign_activates_scoring_signal() -> None:
    n = 12
    events = [StarEventInput(user_id=i, starred_at=DAY + timedelta(seconds=30 * i)) for i in range(n)]
    lists = {f"u{i}": _stars(25) for i in range(n)}
    res, _ = _run(events, {i: f"u{i}" for i in range(n)}, lists, max_users=50)
    out = co_adoption_farm_share(res.events)
    assert out["farm_share"] == 1.0 and out["co_adoption_farm_score"] == 1.0


def test_sample_indices_spread_and_cap() -> None:
    assert sample_indices(5, 10) == [0, 1, 2, 3, 4]
    idx = sample_indices(1500, 300)
    assert len(idx) == 300 and idx[0] == 0 and idx[-1] >= 1490


def test_consume_page_stops_past_target_day() -> None:
    p = _Probe(login="x", day=DAY.date())
    conn = {"pageInfo": {"hasNextPage": True, "endCursor": "c"}, "edges": _stars(1)}
    consume_page(p, conn, TARGET, max_pages=3)
    assert p.done and p.value == 1 and not p.truncated


def test_gateway_timeout_on_batch_retries_users_singly() -> None:
    lists = {f"u{i}": _stars(i) for i in range(4)}
    seen: list[int] = []
    inner = _fake_github(lists, seen)

    def handler(request: httpx.Request) -> httpx.Response:
        n_users = sum(1 for k in json.loads(request.content)["variables"] if k.startswith("l"))
        return httpx.Response(502) if n_users > 1 else inner.handle_request(request)

    events = [StarEventInput(user_id=i, starred_at=DAY) for i in range(4)]
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await enrich_same_day_stars(client, {}, events, {i: f"u{i}" for i in range(4)}, TARGET, batch_size=4)
    res = asyncio.run(go())
    assert [e.same_day_other_stars for e in res.events] == [0, 1, 2, 3]
    assert not res.errors


def test_secondary_rate_limit_stops_the_step() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(403, json={"message": "You have exceeded a secondary rate limit."})

    events = [StarEventInput(user_id=i, starred_at=DAY) for i in range(20)]
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await enrich_same_day_stars(client, {}, events, {i: f"u{i}" for i in range(20)}, TARGET)
    res = asyncio.run(go())
    assert len(calls) == 1 and res.resolved == 0 and res.errors == ["http_403"]
