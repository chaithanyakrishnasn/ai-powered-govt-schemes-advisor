"""Unit tests for GeminiEmbedder (no live network)."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.embedding.embedder import (
    _EMBEDDING_DIM,
    _MAX_CHARS,
    EmbedTaskType,
    GeminiEmbedder,
)


def _fake_embedding(dim: int = _EMBEDDING_DIM) -> list[float]:
    """Return a unit vector (first dim set to 1/sqrt(dim) for normalization)."""
    val = 1.0 / math.sqrt(dim)
    return [val] * dim


def _make_embedder(return_embedding: list[float] | None = None) -> tuple[GeminiEmbedder, MagicMock]:
    mock_client = MagicMock()
    vec = return_embedding or _fake_embedding()

    embed_response = MagicMock()
    embed_response.embeddings = [MagicMock(values=vec)]
    mock_client.raw_client.aio.models.embed_content = AsyncMock(return_value=embed_response)

    return GeminiEmbedder(mock_client), mock_client


class TestEmbedOne:
    @pytest.mark.asyncio
    async def test_returns_correct_dimension(self) -> None:
        embedder, _ = _make_embedder()
        result = await embedder.embed_one("hello", task_type=EmbedTaskType.RETRIEVAL_DOCUMENT)
        assert len(result) == _EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_passes_task_type_to_api(self) -> None:
        embedder, mock_client = _make_embedder()
        with patch("app.services.embedding.embedder.types") as mock_types:
            mock_types.EmbedContentConfig.return_value = MagicMock()
            await embedder.embed_one("test", task_type=EmbedTaskType.RETRIEVAL_QUERY)
            mock_types.EmbedContentConfig.assert_called_once_with(
                task_type=EmbedTaskType.RETRIEVAL_QUERY.value,
                output_dimensionality=768,
            )

    @pytest.mark.asyncio
    async def test_truncates_long_input(self) -> None:
        embedder, mock_client = _make_embedder()
        long_text = "x" * (_MAX_CHARS + 500)

        await embedder.embed_one(long_text, task_type=EmbedTaskType.RETRIEVAL_DOCUMENT)

        assert embedder.truncation_count == 1
        call_kwargs = mock_client.raw_client.aio.models.embed_content.call_args
        actual_contents = call_kwargs.kwargs.get("contents") or call_kwargs.args[1]
        assert len(actual_contents) == _MAX_CHARS

    @pytest.mark.asyncio
    async def test_does_not_truncate_short_input(self) -> None:
        embedder, _ = _make_embedder()
        short_text = "short text"
        await embedder.embed_one(short_text, task_type=EmbedTaskType.RETRIEVAL_DOCUMENT)
        assert embedder.truncation_count == 0

    @pytest.mark.asyncio
    async def test_raises_on_empty_embeddings(self) -> None:
        mock_client = MagicMock()
        resp = MagicMock()
        resp.embeddings = []
        mock_client.raw_client.aio.models.embed_content = AsyncMock(return_value=resp)
        embedder = GeminiEmbedder(mock_client)

        with pytest.raises(ValueError, match="Empty embedding response"):
            await embedder.embed_one("test", task_type=EmbedTaskType.RETRIEVAL_DOCUMENT)

    @pytest.mark.asyncio
    async def test_returned_vector_is_l2_normalized(self) -> None:
        """text-embedding-004 returns normalized vectors; verify the mock returns ~unit vector."""
        embedder, _ = _make_embedder()
        vec = await embedder.embed_one("test", task_type=EmbedTaskType.RETRIEVAL_DOCUMENT)
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6, f"Expected unit vector, got norm={norm}"


class TestEmbedBatch:
    @pytest.mark.asyncio
    async def test_empty_input(self) -> None:
        embedder, _ = _make_embedder()
        result = await embedder.embed_batch([], task_type=EmbedTaskType.RETRIEVAL_DOCUMENT)
        assert result == []

    @pytest.mark.asyncio
    async def test_batch_returns_correct_count(self) -> None:
        embedder, _ = _make_embedder()
        texts = ["a", "b", "c", "d"]
        result = await embedder.embed_batch(texts, task_type=EmbedTaskType.RETRIEVAL_DOCUMENT)
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_batch_each_entry_has_correct_dim(self) -> None:
        embedder, _ = _make_embedder()
        result = await embedder.embed_batch(
            ["hello", "world"], task_type=EmbedTaskType.RETRIEVAL_DOCUMENT
        )
        for vec in result:
            assert len(vec) == _EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_failed_embeddings_become_zero_vectors(self) -> None:
        mock_client = MagicMock()
        call_count = 0

        async def _failing_embed(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("API error")
            resp = MagicMock()
            resp.embeddings = [MagicMock(values=_fake_embedding())]
            return resp

        mock_client.raw_client.aio.models.embed_content = _failing_embed
        embedder = GeminiEmbedder(mock_client)

        results = await embedder.embed_batch(
            ["ok1", "bad", "ok2"], task_type=EmbedTaskType.RETRIEVAL_DOCUMENT
        )
        assert len(results) == 3
        # The failed one should be a zero vector
        failed_vec = results[1]
        assert all(v == 0.0 for v in failed_vec)
        # Others should be non-zero
        assert any(v != 0.0 for v in results[0])

    def test_estimate_cost(self) -> None:
        texts = ["hello" * 100, "world" * 200]
        cost = GeminiEmbedder.estimate_cost(texts)
        assert cost >= 0
        assert cost < 1.0  # should be very cheap
