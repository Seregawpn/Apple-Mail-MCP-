from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .recipient_resolver import RecipientCandidate, resolve_candidates


class RecipientIndexStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._cache_dir = self._root / ".cache"
        self._index_file = self._cache_dir / "recipient_index.json"

    @property
    def index_file(self) -> Path:
        return self._index_file

    def write(self, messages: list[dict]) -> dict:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "messages": messages,
        }
        self._index_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    def read_messages(self) -> list[dict]:
        if not self._index_file.exists():
            return []
        payload = json.loads(self._index_file.read_text())
        return payload.get("messages", [])

    def read_meta(self) -> dict:
        if not self._index_file.exists():
            return {"exists": False, "path": str(self._index_file)}
        payload = json.loads(self._index_file.read_text())
        return {
            "exists": True,
            "path": str(self._index_file),
            "updatedAt": payload.get("updatedAt"),
            "messageCount": len(payload.get("messages", [])),
        }

    def resolve_from_cache(self, query: str, max_results: int = 5) -> list[RecipientCandidate]:
        return resolve_candidates(self.read_messages(), query=query, max_results=max_results)
