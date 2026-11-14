from typing import TypedDict

from app.tools.calculator_tool import calculator
from app.tools.rag_tool import rag_tool
from app.processors.memory_processor import get_conversation_history
from app.processors.llm_processor import generate_response_with_memory


class AgentState(TypedDict):
    question: str
    chat_id: int
    document_id: int
    decision: str
    history: list
    context: str
    answer: str


def agent_node(state: AgentState):
    question = state["question"].lower()

    if "+" in question or "-" in question or "*" in question or "/" in question:
        decision = "calculator"

    elif (
        "document" in question
        or "file" in question
        or "according to" in question
        or "uploaded" in question
    ):
        decision = "rag"

    else:
        decision = "memory_llm"

    print("Agent decision:", decision)

    return {
        "decision": decision
    }


def memory_node(state: AgentState):
    print("Loading memory...")

    history = get_conversation_history(
        state["chat_id"]
    )

    return {
        "history": history
    }


def calculator_node(state: AgentState):
    print("Calculator tool running...")

    result = calculator(
        25,
        48,
        "add"
    )

    return {
        "answer": str(result)
    }


def rag_node(state: AgentState):
    print("RAG tool running...")

    context = rag_tool(
        state["question"],
        state["document_id"]
    )

    return {
        "context": context
    }


def llm_node(state: AgentState):
    print("LLM running...")

    answer = generate_response_with_memory(
        state["history"],
        state["question"]
    )

    return {
        "answer": answer
    }


def rag_answer_node(state: AgentState):
    print("Generating RAG answer...")

    prompt = f"""
Use the following document context to answer the question.

Context:
{state["context"]}

Question:
{state["question"]}
"""

    answer = generate_response_with_memory(
        state["history"],
        prompt
    )

    return {
        "answer": answer
    }