from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from pgvector.sqlalchemy import Vector

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()