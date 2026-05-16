from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from app.schemas.raw_scheme import RawScheme


@dataclass
class LoadStats:
    valid: int = 0
    skipped: int = 0


def load_jsonl(path: Path, stats: LoadStats | None = None) -> Iterator[RawScheme]:
    """Yield RawScheme objects from a JSONL file, logging and skipping bad lines."""
    if not path.exists():
        logger.warning(f"JSONL file not found: {path}")
        return

    with path.open() as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                scheme = RawScheme.model_validate(obj)
                if stats:
                    stats.valid += 1
                yield scheme
            except Exception as e:
                if stats:
                    stats.skipped += 1
                logger.warning(f"{path.name}:{lineno}: skipped — {e}")


def load_jsonl_files(paths: list[Path]) -> tuple[list[RawScheme], LoadStats]:
    """Load all schemes from one or more JSONL files."""
    all_schemes: list[RawScheme] = []
    total = LoadStats()

    for path in paths:
        stats = LoadStats()
        for scheme in load_jsonl(path, stats):
            all_schemes.append(scheme)
        total.valid += stats.valid
        total.skipped += stats.skipped
        logger.info(f"Loaded {stats.valid} schemes from {path.name} ({stats.skipped} skipped)")

    return all_schemes, total
