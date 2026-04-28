#!/usr/bin/env python3
"""postToolUse hook: after Write, remind about contracts/docs and run scoring tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _write_path(tool_input: object) -> str:
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            return ""
    if not isinstance(tool_input, dict):
        return ""
    path = tool_input.get("path") or tool_input.get("file_path") or tool_input.get("target_file") or ""
    return str(path).replace("\\", "/")


def main() -> None:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") != "Write":
        print("{}")
        return

    path = _write_path(payload.get("tool_input"))
    if not path:
        print("{}")
        return

    notes: list[str] = []

    if "packages/scoring/" in path or "apps/api/app/scoring/" in path:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", str(ROOT / "packages" / "scoring"), "-q"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0:
                notes.append(
                    "[SignalGraph] packages/scoring tests FAILED.\n"
                    + (proc.stdout or "")
                    + (proc.stderr or "")
                )
            else:
                notes.append("[SignalGraph] packages/scoring tests passed.")
        except FileNotFoundError:
            notes.append(
                "[SignalGraph] pytest not found on PATH for this hook. Install dev deps: pip install -r requirements-dev.txt"
            )
        except Exception as exc:  # noqa: BLE001
            notes.append(f"[SignalGraph] pytest run error: {exc}")

    if any(
        part in path
        for part in (
            "apps/api/app/models/",
            "apps/api/app/schemas/",
            "apps/api/alembic/",
        )
    ):
        notes.append(
            "[SignalGraph] Models/schemas/Alembic touched: ensure Alembic migration exists; align ORM, Pydantic schemas, and packages/shared-types."
        )

    if any(
        part in path
        for part in (
            "apps/api/app/api/",
            "apps/api/app/schemas/",
            "packages/shared-types/",
        )
    ):
        notes.append(
            "[SignalGraph] API routes or contracts touched: sync shared types and review apps/web consumers."
        )

    doc_triggers = (
        "packages/scoring/",
        "apps/api/app/models/",
        "apps/api/app/schemas/",
        "apps/api/app/services/",
        "apps/web/",
        "docker-compose.yml",
        "infra/docker/",
    )
    if any(part in path for part in doc_triggers) and not path.startswith("docs/"):
        notes.append(
            "[SignalGraph] Consider updating docs/SCORING_SPEC.md, DATA_DICTIONARY.md, or PROJECT_BRIEF.md if semantics changed."
        )

    if not notes:
        print("{}")
        return

    print(json.dumps({"additional_context": "\n\n".join(notes)}))


if __name__ == "__main__":
    main()
