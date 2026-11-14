
import logging

from app.extensions import db
from app.models.document_chunk import DocumentChunk
from app.processors.embedding_processor import create_embedding

logger = logging.getLogger(__name__)


def similarity_search(query, document_id, limit=3):
    if not isinstance(query, str) or not query.strip():
        return []

    query_embedding = create_embedding(query)

    if len(query_embedding) != 384:
        raise ValueError(
            f"Expected 384 embedding values, got {len(query_embedding)}."
        )

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    results = (
        db.session.query(
            DocumentChunk,
            distance.label("distance")
        )
        .filter(
            DocumentChunk.document_id == document_id
        )
        .order_by(distance)
        .limit(limit)
        .all()
    )

    logger.info(
        "Document retrieval: document_id=%s, results=%s",
        document_id,
        len(results)
    )

    return results
