from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding.embedder import EmbedTaskType, GeminiEmbedder


class SchemeFilters(BaseModel):
    level: Literal["central", "state"] | None = None
    state: str | None = None
    categories: list[str] | None = None
    is_active: bool = True


class SchemeMatch(BaseModel):
    scheme_id: int
    slug: str
    name: str
    level: str
    state: str | None
    categories: list[str]
    benefit_type: str | None
    benefit_description: str | None
    similarity: float


class SemanticRetriever:
    def __init__(self, session: AsyncSession, embedder: GeminiEmbedder) -> None:
        self._session = session
        self._embedder = embedder

    async def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        min_similarity: float = 0.4,
        filters: SchemeFilters | None = None,
    ) -> list[SchemeMatch]:
        """Semantic search over schemes using pgvector cosine similarity.

        Applies all SQL filters before vector scoring — never post-filters.
        Returns results ordered by similarity DESC.
        """
        if not query.strip():
            return []

        query_vec = await self._embedder.embed_one(query, task_type=EmbedTaskType.RETRIEVAL_QUERY)
        # Embed vector as SQL literal — safe since query_vec is a list[float] from our own code
        vec_literal = "'{}'::vector".format(
            "[" + ",".join(str(v) for v in query_vec) + "]"
        )

        f = filters or SchemeFilters()

        # Build WHERE clauses (no user-supplied values go into vec_literal)
        conditions = ["s.embedding IS NOT NULL", "s.is_active = :is_active"]
        params: dict[str, object] = {
            "top_k": top_k,
            "min_similarity": min_similarity,
            "is_active": f.is_active,
        }

        if f.level is not None:
            conditions.append("s.level = :level")
            params["level"] = f.level

        if f.state is not None:
            conditions.append("s.state = :state")
            params["state"] = f.state

        if f.categories:
            conditions.append("s.categories && :categories")
            params["categories"] = f.categories

        where_clause = " AND ".join(conditions)

        stmt = text(f"""
            SELECT
                s.id,
                s.slug,
                s.name,
                s.level,
                s.state,
                s.categories,
                s.benefit_type,
                s.benefit_description,
                1 - (s.embedding <=> {vec_literal}) AS similarity
            FROM schemes s
            WHERE {where_clause}
              AND 1 - (s.embedding <=> {vec_literal}) >= :min_similarity
            ORDER BY s.embedding <=> {vec_literal}
            LIMIT :top_k
        """)

        result = await self._session.execute(stmt, params)
        rows = result.fetchall()

        return [
            SchemeMatch(
                scheme_id=row.id,
                slug=row.slug,
                name=row.name,
                level=row.level,
                state=row.state,
                categories=list(row.categories or []),
                benefit_type=row.benefit_type,
                benefit_description=row.benefit_description,
                similarity=float(row.similarity),
            )
            for row in rows
        ]
