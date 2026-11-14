from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.tools.calculator_tool import calculator


class AgentState(TypedDict):
    question: str
    decision: str
    answer: str


def agent_node(state: AgentState):
    question = state["question"].lower()

    if (
        "+" in question
        or "-" in question
        or "*" in question
        or "/" in question
        or "calculate" in question
        or "multiply" in question
        or "add" in question
    ):
        decision = "calculator"
    else:
        decision = "llm"

    print("Agent decision:", decision)

    return {
        "decision": decision
    }


def calculator_node(state: AgentState):
    print("Calculator selected")

    result = calculator(25, 48, "add")

    return {
        "answer": str(result)
    }


def llm_node(state: AgentState):
    print("LLM selected")

    return {
        "answer": "This question would be answered by the LLM."
    }


def route_agent(state: AgentState):
    return state["decision"]


graph_builder = StateGraph(AgentState)

graph_builder.add_node("agent", agent_node)
graph_builder.add_node("calculator", calculator_node)
graph_builder.add_node("llm", llm_node)

graph_builder.add_edge(START, "agent")

graph_builder.add_conditional_edges(
    "agent",
    route_agent,
    {
        "calculator": "calculator",
        "llm": "llm"
    }
)

graph_builder.add_edge("calculator", END)
graph_builder.add_edge("llm", END)

graph = graph_builder.compile()