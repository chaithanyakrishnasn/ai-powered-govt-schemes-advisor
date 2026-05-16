"""Thread-safe JSONL appender with success/failed/skipped tracking and _index.json."""

import asyncio
import contextlib
import json
from pathlib import Path

from pydantic import BaseModel


class JsonlWriter:
    """Append-only JSONL writer safe for concurrent asyncio tasks."""

    def __init__(self, out_file: Path) -> None:
        self._out_file = out_file
        self._lock = asyncio.Lock()
        self._success = 0
        self._failed = 0
        self._skipped = 0

    @property
    def success_count(self) -> int:
        return self._success

    @property
    def failed_count(self) -> int:
        return self._failed

    @property
    def skipped_count(self) -> int:
        return self._skipped

    def load_done(self) -> set[str]:
        """Return slugs already in the output file; sets skipped count."""
        done: set[str] = set()
        if not self._out_file.exists():
            return done
        with self._out_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    with contextlib.suppress(json.JSONDecodeError, KeyError):
                        done.add(json.loads(line)["slug"])
        self._skipped = len(done)
        return done

    async def append(self, record: BaseModel) -> None:
        async with self._lock:
            with self._out_file.open("a") as f:
                f.write(record.model_dump_json() + "\n")
            self._success += 1

    def mark_failed(self) -> None:
        self._failed += 1

    def write_index(self, extra: dict | None = None) -> None:  # type: ignore[type-arg]
        index: dict = {  # type: ignore[type-arg]
            "success": self._success,
            "failed": self._failed,
            "skipped": self._skipped,
            "total": self._success + self._failed + self._skipped,
        }
        if extra:
            index.update(extra)
        index_file = self._out_file.parent / "_index.json"
        with index_file.open("w") as f:
            json.dump(index, f, indent=2)
