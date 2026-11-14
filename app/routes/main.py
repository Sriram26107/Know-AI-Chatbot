
import os
import uuid

from flask import (
    Blueprint,
    request,
    render_template,
    current_app,
    redirect,
    url_for,
    jsonify
)

from werkzeug.utils import secure_filename

from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import User
from app.models.document import Document
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage

from app.processors.pdf_processor import extract_pdf
from app.processors.docx_processor import extract_docx
from app.processors.text_processor import extract_txt
from app.processors.rag_processor import create_document_chunks


main_bp = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


def get_upload_folder():
    upload_folder = os.path.abspath(
        os.path.join(current_app.root_path, "..", "uploads")
    )

    os.makedirs(upload_folder, exist_ok=True)

    return upload_folder


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def extract_document_text(file_path, extension):
    if extension == "pdf":
        return extract_pdf(file_path)

    if extension == "docx":
        return extract_docx(file_path)

    if extension == "txt":
        return extract_txt(file_path)

    raise ValueError("Unsupported document format.")


# Homepage redirects to Login.
@main_bp.route("/")
def home():
    return redirect(url_for("main.login"))


# Login page.
@main_bp.route("/login")
def login():
    return render_template("login.html")


# Registration page.
@main_bp.route("/register")
def register():
    return render_template("register.html")


# Chat page.
@main_bp.route("/chat")
def chat():
    return render_template("chat.html")


# Test database connection.
@main_bp.route("/db-test")
def db_test():
    try:
        db.session.execute(db.text("SELECT 1"))

        return jsonify({
            "message": "PostgreSQL connected successfully."
        }), 200

    except Exception:
        db.session.rollback()

        current_app.logger.exception("DATABASE CONNECTION ERROR")

        return jsonify({
            "message": "Database connection failed."
        }), 500


# Test upload folder.
@main_bp.route("/upload-test", methods=["GET"])
def upload_test():
    try:
        upload_folder = get_upload_folder()

        return jsonify({
            "message": "Upload folder is ready.",
            "upload_folder": upload_folder
        }), 200

    except Exception:
        current_app.logger.exception("UPLOAD FOLDER ERROR")

        return jsonify({
            "message": "Upload folder test failed."
        }), 500


# Upload a document and link it to a user message.
@main_bp.route("/upload-test", methods=["POST"])
@jwt_required()
def upload_document():
    saved_file_path = None

    try:
        user_id = int(get_jwt_identity())

        uploaded_file = request.files.get("file")

        if not uploaded_file or not uploaded_file.filename:
            return jsonify({
                "message": "Please select a document."
            }), 400

        original_filename = secure_filename(uploaded_file.filename)

        if not original_filename or not allowed_file(original_filename):
            return jsonify({
                "message": "Only PDF, DOCX and TXT files are supported."
            }), 400

        chat_session_id = request.form.get("chat_session_id")

        if not chat_session_id:
            return jsonify({
                "message": "Chat session ID is required."
            }), 400

        try:
            chat_session_id = int(chat_session_id)
        except (TypeError, ValueError):
            return jsonify({
                "message": "Invalid chat session ID."
            }), 400

        chat_session = ChatSession.query.filter_by(
            id=chat_session_id,
            user_id=user_id
        ).first()

        if not chat_session:
            return jsonify({
                "message": "Chat session not found."
            }), 404

        # Message ID is optional for backward compatibility.
        message_id = request.form.get("message_id")
        message = None

        if message_id:
            try:
                message_id = int(message_id)
            except (TypeError, ValueError):
                return jsonify({
                    "message": "Invalid message ID."
                }), 400

            # Ensure the message belongs to this chat and is a user message.
            message = ChatMessage.query.filter_by(
                id=message_id,
                session_id=chat_session_id,
                role="user"
            ).first()

            if not message:
                return jsonify({
                    "message": "User message not found in this chat."
                }), 404

        upload_folder = get_upload_folder()

        extension = original_filename.rsplit(".", 1)[1].lower()

        stored_filename = (
            uuid.uuid4().hex + "_" + original_filename
        )

        saved_file_path = os.path.join(
            upload_folder,
            stored_filename
        )

        uploaded_file.save(saved_file_path)

        extracted_text = extract_document_text(
            saved_file_path,
            extension
        )

        if not extracted_text or not extracted_text.strip():
            raise ValueError(
                "No readable text was found in the uploaded document."
            )

        document = Document(
            filename=original_filename,
            file_path=saved_file_path,
            user_id=user_id,
            chat_session_id=chat_session_id,
            message_id=message_id
        )

        db.session.add(document)

        # Generate the document ID before creating its chunks.
        db.session.flush()

        # Create chunks and embeddings.
        chunk_count = create_document_chunks(
            document.id,
            extracted_text
        )

        # Save document and chunks together.
        db.session.commit()

        current_app.logger.info(
            "Document uploaded: %s, ID: %s, message ID: %s, chunks: %s",
            original_filename,
            document.id,
            message_id,
            chunk_count
        )

        return jsonify({
            "message": "Document uploaded successfully.",
            "document_id": document.id,
            "filename": document.filename,
            "chat_session_id": document.chat_session_id,
            "message_id": document.message_id,
            "chunk_count": chunk_count
        }), 201

    except ValueError as error:
        db.session.rollback()

        if saved_file_path and os.path.exists(saved_file_path):
            os.remove(saved_file_path)

        return jsonify({
            "message": str(error)
        }), 400

    except Exception:
        db.session.rollback()

        if saved_file_path and os.path.exists(saved_file_path):
            os.remove(saved_file_path)

        current_app.logger.exception("DOCUMENT UPLOAD ERROR")

        return jsonify({
            "message": "Document upload failed. Please try again."
        }), 500


# Get all documents belonging to the logged-in user.
@main_bp.route("/documents", methods=["GET"])
@jwt_required()
def get_documents():
    try:
        user_id = int(get_jwt_identity())

        documents = Document.query.filter_by(
            user_id=user_id
        ).order_by(
            Document.created_at.desc()
        ).all()

        return jsonify({
            "documents": [
                {
                    "id": document.id,
                    "filename": document.filename,
                    "chat_session_id": document.chat_session_id,
                    "message_id": document.message_id,
                    "created_at": (
                        document.created_at.isoformat()
                        if document.created_at else None
                    )
                }
                for document in documents
            ]
        }), 200

    except Exception:
        db.session.rollback()

        current_app.logger.exception("DOCUMENT LIST ERROR")

        return jsonify({
            "message": "Unable to load documents."
        }), 500


# Delete a document belonging to the logged-in user.
@main_bp.route("/documents/<int:document_id>", methods=["DELETE"])
@jwt_required()
def delete_document(document_id):
    try:
        user_id = int(get_jwt_identity())

        document = Document.query.filter_by(
            id=document_id,
            user_id=user_id
        ).first()

        if not document:
            return jsonify({
                "message": "Document not found."
            }), 404

        file_path = document.file_path

        # Document chunks are deleted through the model relationship cascade.
        db.session.delete(document)
        db.session.commit()

        # Remove the physical file after successful database deletion.
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                current_app.logger.exception(
                    "DOCUMENT FILE CLEANUP ERROR: %s",
                    file_path
                )

        return jsonify({
            "message": "Document deleted successfully.",
            "document_id": document_id
        }), 200

    except Exception:
        db.session.rollback()

        current_app.logger.exception("DOCUMENT DELETE ERROR")

        return jsonify({
            "message": "Unable to delete document."
        }), 500


# Get the currently logged-in user's profile.
@main_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    try:
        user_id = int(get_jwt_identity())

        user = db.session.get(User, user_id)

        if not user:
            return jsonify({
                "message": "User not found."
            }), 404

        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email
        }), 200

    except (TypeError, ValueError):
        return jsonify({
            "message": "Invalid user identity."
        }), 401

    except Exception:
        db.session.rollback()

        current_app.logger.exception("PROFILE RETRIEVAL ERROR")

        return jsonify({
            "message": "Unable to retrieve profile."
        }), 500
