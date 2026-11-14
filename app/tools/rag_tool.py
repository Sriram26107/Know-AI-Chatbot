from app.processors.rag_processor import retrieve_context


def rag_tool(question, document_id):
    context = retrieve_context(
        question,
        document_id,
        3
    )

    if not context:
        return "No relevant information was found in the document."

    return context