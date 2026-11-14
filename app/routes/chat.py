
import logging
import re
import os

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select

from app.extensions import db
from app.models import ChatSession, Document
from app.models.chat_message import ChatMessage

from app.processors.rag_processor import retrieve_context
from app.processors.memory_processor import save_message
from app.processors.llm_processor import generate_response_with_memory


logger = logging.getLogger(__name__)

chat_bp = Blueprint(
    "chat",
    __name__,
    url_prefix="/chats"
)


# --------------------------------
# Format document details
# --------------------------------

def format_document(document):
    return {
        "id": document.id,
        "filename": document.filename,
        "chat_session_id": document.chat_session_id,
        "message_id": document.message_id
    }


# --------------------------------
# Format message details
# --------------------------------

def format_message(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": (
            message.created_at.isoformat()
            if message.created_at else None
        )
    }


# --------------------------------
# Get chat belonging to user
# --------------------------------

def get_user_chat(chat_id, user_id):
    return db.session.execute(
        select(ChatSession).where(
            ChatSession.id == chat_id,
            ChatSession.user_id == user_id
        )
    ).scalar_one_or_none()


# --------------------------------
# Generate chat title
# --------------------------------

def generate_chat_title(content, filename=None):

    if filename:
        title = filename.rsplit(".", 1)[0]

    else:
        title = content.strip()

        title = re.sub(
            r"^please read.*?:",
            "",
            title,
            flags=re.IGNORECASE
        ).strip()

    if not title:
        return "New chat"

    if len(title) > 40:
        title = title[:37].rsplit(" ", 1)[0] + "..."

    return title


# --------------------------------
# Detect reference to an earlier document
# --------------------------------

def refers_to_previous_document(content):

    text = content.lower().strip()

    document_words = [
        "document",
        "documents",
        "file",
        "files",
        "attachment",
        "attachments"
    ]

    reference_words = [
        "earlier",
        "previous",
        "before",
        "already",
        "uploaded",
        "upload",
        "gave you",
        "sent you",
        "shared",
        "attached",
        "last time",
        "i gave",
        "i sent",
        "i uploaded",
        "i shared",
        "that",
        "this"
    ]

    has_document_word = any(
        word in text
        for word in document_words
    )

    has_reference_word = any(
        word in text
        for word in reference_words
    )

    return has_document_word and has_reference_word


# --------------------------------
# Detect filename questions
# --------------------------------

def asks_for_filename(content):

    text = content.lower().strip()

    filename_phrases = [
        "what file",
        "which file",
        "what document",
        "which document",
        "file name",
        "filename",
        "name of the file",
        "name of the document",
        "what was the file",
        "what was the document"
    ]

    return any(
        phrase in text
        for phrase in filename_phrases
    )


# --------------------------------
# Select documents for this question
# --------------------------------

def get_documents_for_message(chat, user_id, user_message):

    # First priority: documents attached to this exact message.

    current_documents = Document.query.filter_by(
        user_id=user_id,
        chat_session_id=chat.id,
        message_id=user_message.id
    ).order_by(
        Document.created_at.asc()
    ).all()

    if current_documents:

        logger.info(
            "Using current message attachments: %s",
            [doc.filename for doc in current_documents]
        )

        return current_documents

    # Check whether the user refers to an earlier document.

    if not refers_to_previous_document(user_message.content):
        return []

    # Search only earlier documents belonging to this user
    # and this particular chat.

    previous_documents = Document.query.filter(
        Document.user_id == user_id,
        Document.chat_session_id == chat.id,
        Document.message_id < user_message.id
    ).order_by(
        Document.message_id.desc(),
        Document.created_at.desc()
    ).all()

    if not previous_documents:
        return []

    # If the user mentions a specific filename, select it.

    mentioned_documents = [
        document
        for document in previous_documents
        if document.filename.lower()
        in user_message.content.lower()
    ]

    if mentioned_documents:
        return mentioned_documents

    # If the user requests all uploaded documents, select all.

    all_documents_requested = any(
        phrase in user_message.content.lower()
        for phrase in [
            "all documents",
            "all files",
            "every document",
            "every file"
        ]
    )

    if all_documents_requested:
        return previous_documents

    # Otherwise, select the most recently uploaded document
    # or documents attached to the same earlier message.

    latest_message_id = previous_documents[0].message_id

    latest_documents = [
        document
        for document in previous_documents
        if document.message_id == latest_message_id
    ]

    logger.info(
        "Using earlier document attachment(s): %s",
        [doc.filename for doc in latest_documents]
    )

    return latest_documents


# --------------------------------
# Generate AI response
# --------------------------------

def generate_chat_response(chat, user_id, user_message):

    content = user_message.content

    # Select current or referenced earlier documents.

    documents = get_documents_for_message(
        chat,
        user_id,
        user_message
    )

    contexts = []
    document_names = []
    failed_documents = []

    # Retrieve relevant context from selected documents.

    for document in documents:

        document_names.append(document.filename)

        try:

            context = retrieve_context(
                content,
                document.id,
                5
            )

            if context and context.strip():

                contexts.append(
                    f"Document filename: {document.filename}\n"
                    f"Document content:\n{context}"
                )

            else:

                failed_documents.append(document.filename)

        except Exception:

            logger.exception(
                "Retrieval failed for document %s",
                document.id
            )

            failed_documents.append(document.filename)

    rag_context = "\n\n".join(contexts)

    logger.info(
        "Chat %s | Message %s | Documents: %s | "
        "Retrieved characters: %s",
        chat.id,
        user_message.id,
        document_names,
        len(rag_context)
    )

    # Generate chat title only once.

    if chat.title == "New chat":

        filename = (
            documents[0].filename
            if documents else None
        )

        chat.title = generate_chat_title(
            content,
            filename
        )

        db.session.commit()

    # Get previous conversation history.

    history_messages = (
        ChatMessage.query
        .filter(
            ChatMessage.session_id == chat.id,
            ChatMessage.id < user_message.id
        )
        .order_by(
            ChatMessage.id.asc()
        )
        .all()
    )

    previous_history = [
        {
            "role": message.role,
            "content": message.content
        }
        for message in history_messages
    ]

    # Describe document availability.

    if not documents:

        document_status = (
            "No document was attached to this message, "
            "and no earlier document was selected."
        )

    elif not rag_context:

        document_status = (
            "The selected document(s) did not provide "
            "retrievable text chunks: "
            + ", ".join(failed_documents)
        )

    else:

        document_status = (
            "Retrieved document(s): "
            + ", ".join(document_names)
        )

    # Detect filename-only questions.

    filename_question = asks_for_filename(content)

    # Prepare the AI prompt.

    prompt = f"""
You are Know AI, a friendly and intelligent AI assistant.

Your name is Know AI.
If the user asks your name, introduce yourself as Know AI.
Never introduce yourself as Knowledge AI.

You can help with:
- General knowledge
- Programming
- Artificial Intelligence
- Machine Learning
- Education
- Science
- Mathematics
- Writing
- Problem solving
- Uploaded documents

General instructions:

1. Answer directly.
2. Use simple and understandable English.
3. Explain difficult concepts step by step.
4. Give examples whenever useful.
5. Use previous conversation history when relevant.
6. Never invent document information.

Document instructions:

7. The retrieved document context belongs to the selected
   documents for this message.

8. If the user refers to an earlier document, use the selected
   earlier document when its content is available.

9. Never claim to have read a document unless its content
   is actually present in the retrieved context.

10. Base document-content answers on retrieved document context.

11. If the answer is not present in the retrieved context,
    clearly explain that it could not be found.

12. If a document was selected but no readable content was
    retrieved, tell the user that you could not retrieve its
    content and ask them to upload it again.

13. If no document is selected and the user asks about an
    earlier document, explain that no earlier attachment
    was found in this chat.

14. For document summaries, organize the answer using
    headings and bullet points.

15. Never mix document content from unrelated chats.

16. If the user asks for the name of an uploaded file,
    use the selected document filenames below.

17. A filename is available as document metadata even when
    document text retrieval fails. You may answer filename
    questions using that metadata.

18. Never say that no earlier file was found when a filename
    is present in the selected document filenames.

Document status:

{document_status}

Is this a filename question?

{filename_question}

Selected document filenames:

{", ".join(document_names) if document_names else "None"}

Retrieved document context:

{rag_context if rag_context else "No document content retrieved."}

Current user question:

{content}
"""

    # Generate AI response.

    answer = generate_response_with_memory(
        previous_history,
        prompt
    )

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("AI returned an empty response.")

    answer = answer.strip()

    # Save assistant response.

    assistant_message = save_message(
        chat.id,
        "assistant",
        answer
    )

    return {
        "chat_message": format_message(assistant_message),
        "documents": [
            format_document(document)
            for document in documents
        ],
        "rag_context": rag_context
    }


# --------------------------------
# Create a new chat
# --------------------------------

@chat_bp.route("", methods=["POST"])
@jwt_required()
def create_chat():

    data = request.get_json(silent=True) or {}

    title = data.get("title", "New chat")

    if not isinstance(title, str) or not title.strip():
        title = "New chat"

    user_id = int(get_jwt_identity())

    chat = ChatSession(
        user_id=user_id,
        title=title.strip()
    )

    try:

        db.session.add(chat)
        db.session.commit()

        return {
            "message": "Chat created successfully",
            "chat": {
                "id": chat.id,
                "title": chat.title,
                "user_id": chat.user_id
            },
            "documents": []
        }, 201

    except Exception:

        db.session.rollback()
        logger.exception("Chat creation failed")

        return {
            "message": "Unable to create chat."
        }, 500


# --------------------------------
# Delete a chat
# --------------------------------

@chat_bp.route("/<int:chat_id>", methods=["DELETE"])
@jwt_required()
def delete_chat(chat_id):

    user_id = int(get_jwt_identity())

    chat = get_user_chat(chat_id, user_id)

    if not chat:
        return {
            "message": "Chat not found."
        }, 404

    try:

        documents = Document.query.filter_by(
            user_id=user_id,
            chat_session_id=chat_id
        ).all()

        files_to_delete = [
            document.file_path
            for document in documents
            if getattr(document, "file_path", None)
        ]

        db.session.delete(chat)
        db.session.commit()

        for file_path in files_to_delete:

            try:

                if os.path.isfile(file_path):
                    os.remove(file_path)

            except OSError:

                logger.exception(
                    "Unable to delete uploaded file: %s",
                    file_path
                )

        return {
            "message": "Chat deleted successfully.",
            "chat_id": chat_id
        }, 200

    except Exception:

        db.session.rollback()
        logger.exception("Chat deletion failed")

        return {
            "message": "Unable to delete chat."
        }, 500


# --------------------------------
# Load messages and chat documents
# --------------------------------

@chat_bp.route("/<int:chat_id>/messages", methods=["GET"])
@jwt_required()
def get_messages(chat_id):

    user_id = int(get_jwt_identity())

    chat = get_user_chat(chat_id, user_id)

    if not chat:
        return {
            "message": "Chat not found."
        }, 404

    messages = (
        ChatMessage.query
        .filter_by(session_id=chat.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )

    documents = Document.query.filter_by(
        user_id=user_id,
        chat_session_id=chat_id
    ).order_by(
        Document.created_at.asc()
    ).all()

    return {
        "chat": {
            "id": chat.id,
            "title": chat.title
        },
        "messages": [
            format_message(message)
            for message in messages
        ],
        "documents": [
            format_document(document)
            for document in documents
        ]
    }, 200


# --------------------------------
# Save user message separately
# --------------------------------

@chat_bp.route("/<int:chat_id>/messages/user", methods=["POST"])
@jwt_required()
def create_user_message(chat_id):

    data = request.get_json(silent=True) or {}

    content = data.get("content", "")

    if not isinstance(content, str) or not content.strip():
        return {
            "message": "Message content is required."
        }, 400

    content = content.strip()

    user_id = int(get_jwt_identity())

    chat = get_user_chat(chat_id, user_id)

    if not chat:
        return {
            "message": "Chat not found."
        }, 404

    try:

        user_message = save_message(
            chat.id,
            "user",
            content
        )

        return {
            "message": "User message saved successfully.",
            "chat": {
                "id": chat.id,
                "title": chat.title
            },
            "user_message": format_message(user_message)
        }, 201

    except Exception:

        db.session.rollback()
        logger.exception("User message creation failed")

        return {
            "message": "Unable to save user message."
        }, 500


# --------------------------------
# Generate response for saved message
# --------------------------------

@chat_bp.route(
    "/<int:chat_id>/messages/<int:message_id>/response",
    methods=["POST"]
)
@jwt_required()
def generate_message_response(chat_id, message_id):

    user_id = int(get_jwt_identity())

    chat = get_user_chat(chat_id, user_id)

    if not chat:
        return {
            "message": "Chat not found."
        }, 404

    user_message = ChatMessage.query.filter_by(
        id=message_id,
        session_id=chat.id,
        role="user"
    ).first()

    if not user_message:
        return {
            "message": "User message not found."
        }, 404

    # Check whether the next message is already an answer.

    next_message = (
        ChatMessage.query
        .filter(
            ChatMessage.session_id == chat.id,
            ChatMessage.id > user_message.id
        )
        .order_by(ChatMessage.id.asc())
        .first()
    )

    if next_message and next_message.role == "assistant":

        return {
            "message": "A response already exists for this message.",
            "chat_message": format_message(next_message)
        }, 200

    try:

        result = generate_chat_response(
            chat,
            user_id,
            user_message
        )

        return {
            "message": "AI response generated successfully.",
            "chat": {
                "id": chat.id,
                "title": chat.title
            },
            **result
        }, 201

    except Exception:

        db.session.rollback()

        logger.exception(
            "Failed to generate response for message %s",
            message_id
        )

        return {
            "message": (
                "Failed to generate response. "
                "Check the Flask terminal."
            )
        }, 500


# --------------------------------
# Existing combined message endpoint
# --------------------------------

@chat_bp.route("/<int:chat_id>/messages", methods=["POST"])
@jwt_required()
def create_message(chat_id):

    data = request.get_json(silent=True) or {}

    content = data.get("content", "")

    if not isinstance(content, str) or not content.strip():
        return {
            "message": "Message content is required."
        }, 400

    content = content.strip()

    user_id = int(get_jwt_identity())

    chat = get_user_chat(chat_id, user_id)

    if not chat:
        return {
            "message": "Chat not found."
        }, 404

    try:

        user_message = save_message(
            chat.id,
            "user",
            content
        )

        result = generate_chat_response(
            chat,
            user_id,
            user_message
        )

        return {
            "message": "Message created successfully",
            "chat": {
                "id": chat.id,
                "title": chat.title
            },
            **result
        }, 201

    except Exception:

        db.session.rollback()

        logger.exception(
            "Failed to process chat message"
        )

        return {
            "message": (
                "Failed to process message. "
                "Check the Flask terminal."
            )
        }, 500
