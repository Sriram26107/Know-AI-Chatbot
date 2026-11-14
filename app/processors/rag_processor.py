
import logging

from app.extensions import db
from app.models.document_chunk import DocumentChunk
from app.processors.chunk_processor import chunk_text
from app.processors.embedding_processor import create_embedding
from app.processors.search_processor import similarity_search

logger = logging.getLogger(__name__)


def create_document_chunks(document_id, text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Document text is empty.")

    chunks = chunk_text(text, 500, 50)

    if not chunks:
        raise ValueError("No document chunks were created.")

    for index, chunk in enumerate(chunks):
        embedding = create_embedding(chunk)

        document_chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=index,
            text=chunk,
            embedding=embedding
        )

        db.session.add(document_chunk)

    # Do not commit here.
    # main.py commits the document and its chunks together.

    logger.info(
        "Created %s chunks for document %s",
        len(chunks),
        document_id
    )

    return len(chunks)


def retrieve_context(query, document_id, limit=3):
    results = similarity_search(
        query,
        document_id,
        limit
    )

    if not results:
        logger.warning(
            "No document chunks found for document %s",
            document_id
        )
        return ""

    context = []

    for chunk, distance in results:
        context.append(chunk.text)

    retrieved_text = "\n\n".join(context)

    logger.info(
        "Retrieved %s characters from document %s",
        len(retrieved_text),
        document_id
    )

    return retrieved_text
