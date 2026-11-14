from datetime import datetime
from app.extensions import db
from pgvector.sqlalchemy import Vector

class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"

    id = db.Column(db.Integer, primary_key=True)

    document_id = db.Column(
        db.Integer,
        db.ForeignKey("documents.id"),
        nullable=False
    )

    chunk_index = db.Column(
        db.Integer,
        nullable=False
    )

    text = db.Column(
        db.Text,
        nullable=False
    )

    embedding = db.Column(
        Vector(384),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    document = db.relationship(
        "Document",
        back_populates="chunks"
    )