
from datetime import datetime
from app.extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    file_path = db.Column(
        db.String(500),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    chat_session_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_sessions.id"),
        nullable=True
    )

    # Links this document to the exact user message.
    # Nullable to preserve existing uploaded documents.
    message_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "chat_messages.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user = db.relationship(
        "User",
        back_populates="documents"
    )

    chat_session = db.relationship(
        "ChatSession",
        back_populates="documents"
    )

    message = db.relationship(
        "ChatMessage",
        backref=db.backref(
            "documents",
            lazy=True
        )
    )

    chunks = db.relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
