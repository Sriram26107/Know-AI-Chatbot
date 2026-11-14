from datetime import datetime
from app.extensions import db

class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship(
        "User",
        back_populates="chats"
    )

    messages = db.relationship(
        "ChatMessage",
        back_populates="session",
        lazy=True
    )

    documents = db.relationship(
        "Document",
        back_populates="chat_session",
        lazy=True
    )