from typing import TypedDict
from app.processors.memory_processor import get_conversation_history
from app.processors.llm_processor import generate_response_with_memory


from typing import TypedDict
from app.processors.memory_processor import get_conversation_history
from app.processors.llm_processor import generate_response_with_memory


class AgentMemoryState(TypedDict):
    question: str
    chat_id: int
    history: list
    answer: str


def memory_node(state: AgentMemoryState):
    print("Loading memory...")

    history = get_conversation_history(
        state["chat_id"]
    )

    return {
        "history": history
    }


def agent_node(state: AgentMemoryState):
    history = state["history"]

    print("Agent checking memory...")

    if history:
        decision = "memory_llm"
    else:
        decision = "llm"

    print("Agent decision:", decision)

    return {
        "decision": decision
    }


def llm_node(state: AgentMemoryState):
    print("Generating answer...")

    answer = generate_response_with_memory(
        state["history"],
        state["question"]
    )

    return {
        "answer": answer
    }

def memory_node(state: AgentMemoryState):
    print("Loading memory...")

    history = get_conversation_history(
        state["chat_id"]
    )

    return {
        "history": history
    }


def agent_node(state: AgentMemoryState):
    history = state["history"]

    print("Agent checking memory...")

    if history:
        decision = "memory_llm"
    else:
        decision = "llm"

    print("Agent decision:", decision)

    return {
        "decision": decision
    }


def llm_node(state: AgentMemoryState):
    print("Generating answer...")

    answer = generate_response_with_memory(
        state["history"],
        state["question"]
    )

    return {
        "answer": answer
    }