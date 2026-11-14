from typing import TypedDict
from app.tools.calculator_tool import calculator
from app.tools.knowledge_tool import knowledge_tool


class AgentState(TypedDict):
    question: str
    tool: str
    answer: str


def agent_node(state: AgentState):
    question = state["question"].lower()

    if "+" in question:
        tool = "calculator"
    elif "rag" in question:
        tool = "knowledge"
    elif "llm" in question:
        tool = "knowledge"
    elif "agent" in question:
        tool = "knowledge"
    else:
        tool = "none"

    print("Selected tool:", tool)

    return {
        "tool": tool
    }


def calculator_node(state: AgentState):
    print("Calculator running...")

    result = calculator(25, 48, "add")

    return {
        "answer": str(result)
    }


def knowledge_node(state: AgentState):
    print("Knowledge tool running...")

    question = state["question"].lower()

    if "rag" in question:
        topic = "rag"
    elif "llm" in question:
        topic = "llm"
    else:
        topic = "agent"

    result = knowledge_tool(topic)

    return {
        "answer": result
    }


def no_tool_node(state: AgentState):
    print("No tool required.")

    return {
        "answer": "I don't have a tool for this question."
    }