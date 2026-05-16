from collections.abc import AsyncGenerator
from typing import cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db as get_db_session
from app.services.embedding.embedder import GeminiEmbedder
from app.services.embedding.retriever import SemanticRetriever
from app.services.llm.gemini import GeminiClient
from app.services.matching.llm_reranker import LLMReranker
from app.services.matching.service import MatchingService
from app.services.multilingual.translator import QueryTranslator


# Re-export for router convenience
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_gemini_client(request: Request) -> GeminiClient:
    return cast(GeminiClient, request.app.state.gemini_client)


def get_translator(request: Request) -> QueryTranslator | None:
    if not hasattr(request.app.state, "gemini_client") or not request.app.state.gemini_client:
        return None
    return QueryTranslator(request.app.state.gemini_client)


def get_embedder(request: Request) -> GeminiEmbedder:
    return cast(GeminiEmbedder, request.app.state.embedder)


def get_llm_reranker(
    request: Request, session: AsyncSession = Depends(get_db)
) -> LLMReranker | None:
    if not hasattr(request.app.state, "gemini_client") or not request.app.state.gemini_client:
        return None
    return LLMReranker(request.app.state.gemini_client, session)


async def get_retriever(
    session: AsyncSession = Depends(get_db),
    embedder: GeminiEmbedder = Depends(get_embedder),
) -> SemanticRetriever:
    return SemanticRetriever(session, embedder)


async def get_matching_service(
    session: AsyncSession = Depends(get_db),
    llm_reranker: LLMReranker | None = Depends(get_llm_reranker),
    retriever: SemanticRetriever = Depends(get_retriever),
    translator: QueryTranslator | None = Depends(get_translator),
) -> MatchingService:
    service = MatchingService(session, llm_reranker, translator=translator)
    # This is a hack, we need to properly inject the retriever into the semantic reranker
    service.semantic_reranker._retriever = retriever  # type: ignore
    return service
