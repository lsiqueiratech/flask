from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    _tablename_ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(255))  # nome do arquivo da foto de perfil

    posts = db.relationship(
        "Post", back_populates="author", cascade="all, delete-orphan"
    )


class Post(db.Model):
    _tablename_ = "post"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    imagem_post = db.Column(db.String(255))  # nome do arquivo da imagem do post

    author = db.relationship("User", back_populates="posts")