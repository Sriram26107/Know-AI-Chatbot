def knowledge_tool(topic):
    knowledge = {
        "rag": "RAG means Retrieval Augmented Generation. It retrieves relevant information and gives it to the LLM as context.",
        "llm": "LLM means Large Language Model. It can understand and generate human language.",
        "agent": "An AI agent can decide what action or tool to use to complete a task."
    }

    return knowledge.get(
        topic.lower(),
        "I don't have information about this topic."
    )