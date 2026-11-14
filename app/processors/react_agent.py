from typing import TypedDict
from app.tools.calculator_tool import calculator


class ReactState(TypedDict):
    question: str
    thought: str
    action: str
    observation: str
    answer: str


def agent_think(state: ReactState):
    question = state["question"].lower()

    if "+" in question:
        thought = "I need to use the calculator."
        action = "calculator"
    else:
        thought = "I can answer this without using the calculator."
        action = "finish"

    print("Thought:", thought)
    print("Action:", action)

    return {
        "thought": thought,
        "action": action
    }


def calculator_action(state: ReactState):
    print("Running calculator...")

    result = calculator(25, 48, "add")

    return {
        "observation": str(result)
    }


def agent_observe(state: ReactState):
    observation = state["observation"]

    answer = f"The answer is {observation}."

    print("Observation:", observation)
    print("Final answer:", answer)

    return {
        "answer": answer
    }


def finish_action(state: ReactState):
    answer = "This question does not require the calculator."

    print("Final answer:", answer)

    return {
        "answer": answer
    }