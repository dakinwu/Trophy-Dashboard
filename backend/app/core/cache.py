import json
import re
import time
from pathlib import Path


class FileCache:
    """JSON file cache with a per-load TTL, so different data types can use
    different freshness windows against the same store."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = re.sub(r"[/\\]", "__", key)
        return self.base_dir / f"{safe}.json"

    def load(self, key: str, ttl_seconds: float) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        if (time.time() - path.stat().st_mtime) > ttl_seconds:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    def save(self, key: str, data: dict) -> None:
        self._path(key).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
