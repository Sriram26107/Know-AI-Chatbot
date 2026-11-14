from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.tools.calculator_tool import calculator


class ToolState(TypedDict):
    answer: str


def calculator_node(state: ToolState):
    print("Calculator tool running...")

    result = calculator(25, 48, "add")

    return {
        "answer": str(result)
    }


graph_builder = StateGraph(ToolState)

graph_builder.add_node(
    "calculator",
    calculator_node
)

graph_builder.add_edge(
    START,
    "calculator"
)

graph_builder.add_edge(
    "calculator",
    END
)

graph = graph_builder.compile()