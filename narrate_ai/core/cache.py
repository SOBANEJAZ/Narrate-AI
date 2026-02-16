from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any


class MultiLayerCache:
    """Small memory + filesystem cache for agent outputs."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, Any] = {}

    def _hash_key(self, namespace: str, key: str) -> str:
        raw = f"{namespace}:{key}".encode("utf-8")
        return sha256(raw).hexdigest()

    def _path(self, namespace: str, key: str) -> Path:
        namespace_dir = self.root / namespace
        namespace_dir.mkdir(parents=True, exist_ok=True)
        return namespace_dir / f"{self._hash_key(namespace, key)}.json"

    def get(self, namespace: str, key: str) -> Any | None:
        memory_key = f"{namespace}:{key}"
        if memory_key in self._memory:
            return self._memory[memory_key]

        path = self._path(namespace, key)
        if not path.exists():
            return None

        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            self._memory[memory_key] = value
            return value
        except json.JSONDecodeError:
            return None

    def set(self, namespace: str, key: str, value: Any) -> None:
        memory_key = f"{namespace}:{key}"
        self._memory[memory_key] = value
        path = self._path(namespace, key)
        path.write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding="utf-8")
