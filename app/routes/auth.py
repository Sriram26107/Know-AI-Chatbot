
from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from sqlalchemy import select

from app.extensions import db
from app.models import User, ChatSession


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# Register a new user.
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = (data.get("username") or data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return {
            "message": "Name, email and password are required."
        }, 400

    if len(password) < 8:
        return {
            "message": "Password must contain at least 8 characters."
        }, 400

    try:
        stmt = select(User).where(User.email == email)
        existing_user = db.session.execute(stmt).scalar_one_or_none()

        if existing_user:
            return {
                "message": "Email already registered."
            }, 409

        user = User(
            name=name,
            email=email,
            password_hash=""
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(
            identity=str(user.id)
        )

        return {
            "message": "Account created successfully.",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }, 201

    except Exception:
        db.session.rollback()
        return {
            "message": "Registration failed. Please try again."
        }, 500


# Login an existing user.
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return {
            "message": "Email and password are required."
        }, 400

    try:
        stmt = select(User).where(User.email == email)
        user = db.session.execute(stmt).scalar_one_or_none()

        if not user or not user.check_password(password):
            return {
                "message": "Invalid email or password."
            }, 401

        access_token = create_access_token(
            identity=str(user.id)
        )

        return {
            "message": "Login successful.",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }, 200

    except Exception:
        db.session.rollback()
        return {
            "message": "Login failed. Please try again."
        }, 500


# Get the currently logged-in user.
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    try:
        user_id = get_jwt_identity()

        stmt = select(User).where(
            User.id == int(user_id)
        )

        user = db.session.execute(stmt).scalar_one_or_none()

        if not user:
            return {
                "message": "User not found."
            }, 404

        return {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }, 200

    except (TypeError, ValueError):
        return {
            "message": "Invalid user identity."
        }, 401

    except Exception:
        db.session.rollback()
        return {
            "message": "Unable to retrieve user details."
        }, 500


# Get all chats belonging to the logged-in user.
@auth_bp.route("/my-chats", methods=["GET"])
@jwt_required()
def my_chats():
    try:
        user_id = get_jwt_identity()

        stmt = select(ChatSession).where(
            ChatSession.user_id == int(user_id)
        )

        chats = db.session.execute(stmt).scalars().all()

        return {
            "chats": [
                {
                    "id": chat.id,
                    "title": chat.title,
                    "created_at": (
                        chat.created_at.isoformat()
                        if chat.created_at else None
                    )
                }
                for chat in chats
            ]
        }, 200

    except (TypeError, ValueError):
        return {
            "message": "Invalid user identity."
        }, 401

    except Exception:
        db.session.rollback()
        return {
            "message": "Unable to retrieve chats."
        }, 500

