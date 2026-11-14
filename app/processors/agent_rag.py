from typing import TypedDict
from app.tools.rag_tool import rag_tool
from app.processors.llm_processor import generate_response


class AgentRAGState(TypedDict):
    question: str
    document_id: int
    decision: str
    context: str
    answer: str


def agent_node(state: AgentRAGState):
    question = state["question"].lower()

    if (
        "document" in question
        or "file" in question
        or "according to" in question
        or "uploaded" in question
    ):
        decision = "rag"
    else:
        decision = "llm"

    print("Agent decision:", decision)

    return {
        "decision": decision
    }


def rag_node(state: AgentRAGState):
    print("RAG tool running...")

    context = rag_tool(
        state["question"],
        state["document_id"]
    )

    return {
        "context": context
    }


def llm_node(state: AgentRAGState):
    print("LLM running...")

    answer = generate_response(
        state["question"]
    )

    return {
        "answer": answer
    }


def rag_answer_node(state: AgentRAGState):
    print("Generating answer using RAG...")

    prompt = f"""
Use the following document context to answer the question.

Context:
{state["context"]}

Question:
{state["question"]}
"""

    answer = generate_response(prompt)

    return {
        "answer": answer
    }