from __future__ import annotations

import re
from dataclasses import dataclass, field

from loguru import logger

from app.schemas.raw_scheme import RawScheme


@dataclass
class DuplicateReport:
    total: int = 0
    unique: int = 0
    exact_dupes: int = 0
    near_dupes: int = 0
    near_dup_pairs: list[tuple[str, str]] = field(default_factory=list)


def _normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    return re.sub(r"\s+", " ", name).strip()


class Deduplicator:
    def filter(
        self, schemes: list[RawScheme]
    ) -> tuple[list[RawScheme], DuplicateReport]:
        report = DuplicateReport(total=len(schemes))

        # ── Stage 1: exact dedup by (source, slug) — last occurrence wins ──
        seen_exact: dict[tuple[str, str], int] = {}  # key → index in `schemes`
        drop_exact: set[int] = set()

        for i, s in enumerate(schemes):
            key = (s.source, s.slug)
            if key in seen_exact:
                drop_exact.add(seen_exact[key])  # drop earlier duplicate
                logger.debug(f"Exact dup: {s.slug!r} from {s.source!r}")
            seen_exact[key] = i

        deduped = [s for i, s in enumerate(schemes) if i not in drop_exact]
        report.exact_dupes = len(drop_exact)

        # ── Stage 2: near-dup by normalized name across different sources ──
        # Prefer central over state; otherwise keep first seen.
        seen_near: dict[str, int] = {}  # normalized_name → index in `deduped`
        drop_near: set[int] = set()

        for i, s in enumerate(deduped):
            norm = _normalize_name(s.name)
            if norm not in seen_near:
                seen_near[norm] = i
                continue

            j = seen_near[norm]
            existing = deduped[j]

            if existing.source == s.source:
                # Same source, different slug — genuinely different schemes
                continue

            # Cross-source near-dup: prefer central over state
            if s.level == "central" and existing.level == "state":
                drop_near.add(j)
                seen_near[norm] = i
                logger.warning(
                    f"Near-dup: '{s.name}' ({s.source}) shadows '{existing.name}' ({existing.source}) — keeping central"
                )
            else:
                drop_near.add(i)
                logger.warning(
                    f"Near-dup: '{s.name}' ({s.source}) duplicates '{existing.name}' ({existing.source}) — keeping first"
                )
            report.near_dup_pairs.append((s.slug, existing.slug))

        final = [s for i, s in enumerate(deduped) if i not in drop_near]
        report.near_dupes = len(drop_near)
        report.unique = len(final)
        return final, report

    @staticmethod
    def print_report(report: DuplicateReport) -> None:
        print(
            f"\n── Dedup report ─────────────────────────────────────\n"
            f"  Total loaded : {report.total}\n"
            f"  Exact dupes  : {report.exact_dupes}\n"
            f"  Near dupes   : {report.near_dupes}\n"
            f"  Unique       : {report.unique}\n"
            f"─────────────────────────────────────────────────────\n"
        )
