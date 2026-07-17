"""End-to-end smoke test for the SignalGraph API on SQLite (no external services).

Exercises the full analyze → read → compare flow in mock mode, which is the
zero-config demo path documented in the README.
"""
from __future__ import annotations

import os
import tempfile

# Point the app at a throwaway SQLite file *before* importing app modules so the
# engine binds to it. Mock mode is the default, so no GitHub token is needed.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["MOCK_MODE"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_analyze_read_and_compare_flow() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

        # Analyze two repos in mock mode.
        r = client.post(
            "/analyze",
            json={"repo_url": "https://github.com/facebook/react", "force_mock": True},
        )
        assert r.status_code == 200, r.text
        body = r.json()

        # Scorecard is populated and scores are within the documented 0-100 range.
        card = body["scorecard"]
        for key in (
            "manipulation_risk",
            "star_integrity",
            "adoption_score",
            "builder_score",
            "durability_score",
            "credibility_adjusted_traction",
        ):
            assert 0.0 <= card[key] <= 100.0, f"{key} out of range: {card[key]}"

        assert body["timeline"]["points"], "timeline should not be empty"
        assert body["disclaimer"], "response must carry the false-positive disclaimer"

        # Persisted read path works.
        assert client.get("/repo/facebook/react").status_code == 200

        # Peer comparison against a second analyzed repo.
        client.post(
            "/analyze",
            json={"repo_url": "https://github.com/vercel/next.js", "force_mock": True},
        )
        cmp = client.get("/repo/facebook/react/compare", params={"peers": "vercel/next.js"})
        assert cmp.status_code == 200, cmp.text
        assert len(cmp.json()["peers"]) == 1


def test_unknown_repo_returns_404() -> None:
    with TestClient(app) as client:
        assert client.get("/repo/never/analyzed").status_code == 404
