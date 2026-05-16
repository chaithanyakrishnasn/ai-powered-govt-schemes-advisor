from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from app.services.extraction.schemas import ExtractionResult

# Increment this when the extraction schema or prompt changes to invalidate old cache entries.
# 1.1: invalidate entries from runs missing GEMINI_API_KEY (pipeline now refuses to cache
#      failed extractions, but old poisoned entries must be unreachable — see Phase 2 incident).
SCHEMA_VERSION = "1.1"

_DEFAULT_CACHE_DIR = Path("data/cache/extractions")


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total > 0 else 0.0


class ExtractionCache:
    def __init__(self, cache_dir: Path = _DEFAULT_CACHE_DIR) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self.stats = CacheStats()

    def _key(self, eligibility_text: str, scheme_name: str, ministry: str) -> str:
        raw = f"{SCHEMA_VERSION}|{eligibility_text}|{scheme_name}|{ministry}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(
        self, eligibility_text: str, scheme_name: str, ministry: str
    ) -> ExtractionResult | None:
        h = self._key(eligibility_text, scheme_name, ministry)
        path = self._dir / f"{h}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                result = ExtractionResult.model_validate(data)
                self.stats.hits += 1
                return result
            except Exception as e:
                logger.warning(f"Cache entry {h[:8]}… corrupt, discarding: {e}")
                path.unlink(missing_ok=True)
        self.stats.misses += 1
        return None

    def set(
        self,
        eligibility_text: str,
        scheme_name: str,
        ministry: str,
        result: ExtractionResult,
    ) -> None:
        h = self._key(eligibility_text, scheme_name, ministry)
        path = self._dir / f"{h}.json"
        path.write_text(result.model_dump_json(by_alias=True))
