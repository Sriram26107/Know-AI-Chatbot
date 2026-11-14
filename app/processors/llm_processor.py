
import os
from google import genai

MODEL_NAME = "gemini-3.5-flash-lite"


def get_gemini_client():
    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise ValueError("LLM_API_KEY is not configured.")

    return genai.Client(api_key=api_key)


def generate_response(prompt):
    client = get_gemini_client()

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt
    )

    return interaction.output_text or ""


def generate_response_with_memory(history, prompt):
    client = get_gemini_client()

    conversation = []

    for message in history:
        role = message.get("role")
        content = message.get("content")

        if not content:
            continue

        if role == "user":
            conversation.append(f"User: {content}")

        elif role == "assistant":
            conversation.append(f"Assistant: {content}")

    conversation.append(f"User: {prompt}")

    conversation_text = "\n\n".join(conversation)

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=conversation_text
    )

    return interaction.output_text or ""
