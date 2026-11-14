
import os
import ollama


ollama_client = ollama.Client(
    host=os.getenv("OLLAMA_HOST", "http://localhost:11434")
)


def generate_response(prompt):
    response = ollama_client.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


def generate_response_with_memory(history, prompt):
    messages = history.copy()

    messages.append({
        "role": "user",
        "content": prompt
    })

    response = ollama_client.chat(
        model="llama3.2:3b",
        messages=messages
    )

    return response["message"]["content"]
