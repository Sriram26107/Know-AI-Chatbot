from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.processors.memory_processor import get_conversation_history, save_message
from app.processors.rag_processor import retrieve_context
from app.processors.llm_processor import generate_response_with_memory
from app.tools.calculator_tool import calculator

class GraphState(TypedDict):
    question: str
    history: list
    context: str
    answer: str
    chat_id: int
    document_id: int


def question_node(state: GraphState):
    print("Question node...")

    return {
        "question": state["question"]
    }


def memory_node(state: GraphState):
    print("Memory node...")

    history = get_conversation_history(
        state["chat_id"]
    )

    return {
        "history": history
    }


def rag_node(state: GraphState):
    print("RAG node...")

    context = retrieve_context(
        state["question"],
        state["document_id"],
        3
    )

    return {
        "context": context
    }


def llm_node(state: GraphState):
    print("LLM node...")

    prompt = state["question"]

    if state["context"]:
        prompt = f"""
Use the following context to answer the question.

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


def save_answer_node(state: GraphState):
    print("Saving answer...")

    save_message(
        state["chat_id"],
        "assistant",
        state["answer"]
    )

    return {
        "answer": state["answer"]
    }

def calculator_node(state: GraphState):
    print("Calculator tool running...")

    result = calculator(25, 48, "add")

    return {
        "answer": str(result)
    }


graph_builder = StateGraph(GraphState)

graph_builder.add_node(
    "question",
    question_node
)

graph_builder.add_node(
    "memory",
    memory_node
)

graph_builder.add_node(
    "rag",
    rag_node
)

graph_builder.add_node(
    "llm",
    llm_node
)

graph_builder.add_node(
    "save_answer",
    save_answer_node
)

graph_builder.add_edge(
    START,
    "question"
)

graph_builder.add_edge(
    "question",
    "memory"
)

graph_builder.add_edge(
    "memory",
    "rag"
)

graph_builder.add_edge(
    "rag",
    "llm"
)

graph_builder.add_edge(
    "llm",
    "save_answer"
)

graph_builder.add_edge(
    "save_answer",
    END
)

graph = graph_builder.compile()