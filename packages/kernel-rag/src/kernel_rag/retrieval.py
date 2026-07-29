"""Retrieval and citation primitives."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from kernel_core import ChunkEmbedding, Document, DocumentChunk, KnowledgeBase
from kernel_observability import LatencyTimer, MetricsRecorder, NoOpMetricsRecorder
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)

from kernel_rag.embeddings import EmbeddingProvider, MockEmbeddingProvider


@dataclass(frozen=True)
class Citation:
    knowledge_base_id: UUID
    document_id: UUID
    document_title: str
    document_source_uri: str
    chunk_id: UUID
    chunk_index: int
    start_char: int
    end_char: int


@dataclass(frozen=True)
class RetrievalResult:
    content: str
    score: float
    citation: Citation
    metadata: dict[str, object]


@dataclass(frozen=True)
class RetrievalResponse:
    knowledge_base_id: UUID
    query: str
    model: str
    results: list[RetrievalResult]


class RetrievalError(RuntimeError):
    """Raised when retrieval cannot be completed."""


class KnowledgeBaseNotFoundError(RetrievalError):
    """Raised when retrieval targets a missing knowledge base."""


class CitationBuilder:
    def build(
        self,
        *,
        knowledge_base: KnowledgeBase,
        document: Document,
        chunk: DocumentChunk,
    ) -> Citation:
        return Citation(
            knowledge_base_id=knowledge_base.id,
            document_id=document.id,
            document_title=document.title,
            document_source_uri=document.source_uri,
            chunk_id=chunk.id,
            chunk_index=chunk.index,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
        )


class Retriever:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        citation_builder: CitationBuilder | None = None,
        metrics_recorder: MetricsRecorder | None = None,
    ) -> None:
        self._embedding_provider = embedding_provider or MockEmbeddingProvider()
        self._citation_builder = citation_builder or CitationBuilder()
        self._metrics_recorder = metrics_recorder or NoOpMetricsRecorder()

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        return self._embedding_provider

    def retrieve(
        self,
        *,
        knowledge_base_id: UUID,
        query: str,
        knowledge_base_repository: KnowledgeBaseRepository,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        embedding_repository: ChunkEmbeddingRepository,
        top_k: int = 5,
    ) -> RetrievalResponse:
        timer = LatencyTimer.start()
        try:
            response = self._retrieve(
                knowledge_base_id=knowledge_base_id,
                query=query,
                knowledge_base_repository=knowledge_base_repository,
                document_repository=document_repository,
                chunk_repository=chunk_repository,
                embedding_repository=embedding_repository,
                top_k=top_k,
            )
        except RetrievalError as error:
            latency_ms = timer.elapsed_ms()
            self._record_retrieval_failure_metrics(
                error_type=type(error).__name__,
                latency_ms=latency_ms,
            )
            raise

        latency_ms = timer.elapsed_ms()
        self._record_retrieval_success_metrics(
            result_count=len(response.results),
            latency_ms=latency_ms,
        )
        return response

    def _retrieve(
        self,
        *,
        knowledge_base_id: UUID,
        query: str,
        knowledge_base_repository: KnowledgeBaseRepository,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        embedding_repository: ChunkEmbeddingRepository,
        top_k: int,
    ) -> RetrievalResponse:
        knowledge_base = knowledge_base_repository.get(knowledge_base_id)
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError(
                f"Knowledge base {knowledge_base_id} was not found."
            )

        normalized_query = query.strip()
        if not normalized_query:
            return RetrievalResponse(
                knowledge_base_id=knowledge_base_id,
                query=query,
                model=self._embedding_provider.model,
                results=[],
            )

        limit = max(1, top_k)
        query_vector = self._embedding_provider.embed_texts([normalized_query])[0]
        scored_embeddings = embedding_repository.similarity_search(
            knowledge_base_id=knowledge_base_id,
            query_vector=query_vector,
            model=self._embedding_provider.model,
            limit=limit,
        )

        results = [
            self._result_from_embedding(
                knowledge_base=knowledge_base,
                embedding=embedding,
                score=score,
                document_repository=document_repository,
                chunk_repository=chunk_repository,
            )
            for embedding, score in scored_embeddings
        ]
        return RetrievalResponse(
            knowledge_base_id=knowledge_base_id,
            query=query,
            model=self._embedding_provider.model,
            results=[result for result in results if result is not None],
        )

    def _result_from_embedding(
        self,
        *,
        knowledge_base: KnowledgeBase,
        embedding: ChunkEmbedding,
        score: float,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
    ) -> RetrievalResult | None:
        document = document_repository.get(embedding.document_id)
        chunk = chunk_repository.get(embedding.chunk_id)
        if document is None or chunk is None:
            return None

        return RetrievalResult(
            content=chunk.content,
            score=score,
            citation=self._citation_builder.build(
                knowledge_base=knowledge_base,
                document=document,
                chunk=chunk,
            ),
            metadata={
                "document_metadata": document.metadata,
                "chunk_metadata": chunk.metadata,
                "embedding_id": str(embedding.id),
                "embedding_model": embedding.model,
            },
        )

    def _record_retrieval_success_metrics(self, *, result_count: int, latency_ms: int) -> None:
        labels = {"model": self._embedding_provider.model, "status": "succeeded"}
        self._metrics_recorder.increment("rag_retrievals_total", labels=labels)
        self._metrics_recorder.observe("rag_retrieval_latency_ms", latency_ms, labels=labels)
        self._metrics_recorder.observe("rag_retrieval_result_count", result_count, labels=labels)

    def _record_retrieval_failure_metrics(self, *, error_type: str, latency_ms: int) -> None:
        labels = {
            "model": self._embedding_provider.model,
            "status": "failed",
            "error_type": error_type,
        }
        self._metrics_recorder.increment("rag_retrievals_total", labels=labels)
        self._metrics_recorder.increment("rag_retrieval_failure_total", labels=labels)
        self._metrics_recorder.observe("rag_retrieval_latency_ms", latency_ms, labels=labels)
