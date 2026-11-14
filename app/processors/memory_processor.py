from app.extensions import db
from app.models import ChatMessage


def get_conversation_history(chat_id):
    messages = (
        ChatMessage.query
        .filter_by(session_id=chat_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    history = []

    for message in messages:
        history.append({
            "role": message.role,
            "content": message.content
        })

    return history


def format_conversation_history(history):
    messages = []

    for message in history:
        messages.append({
            "role": message["role"],
            "content": message["content"]
        })

    return messages


def save_message(chat_id, role, content):
    message = ChatMessage(
        session_id=chat_id,
        role=role,
        content=content
    )

    db.session.add(message)
    db.session.commit()

    return message