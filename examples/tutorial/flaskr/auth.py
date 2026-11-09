import functools
import os
import uuid

from flask import Blueprint
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from .models import User
from .models import db

bp = Blueprint("auth", __name__, url_prefix="/auth")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    """Check whether the file has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_profile_picture(file):
    """Sanitize the file name, save the image in the upload folder
    and return the stored file name."""
    filename = secure_filename(file.filename)
    # Prefix with a random id so equal names from different users don't collide.
    unique_filename = f"{uuid.uuid4().hex}_{filename}"

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    file.save(os.path.join(upload_folder, unique_filename))
    return unique_filename


def delete_profile_picture(filename):
    """Remove a profile picture from the upload folder, if it exists."""
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(path):
        os.remove(path)


def login_required(view):
    """View decorator that redirects anonymous users to the login page."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = db.session.get(User, user_id)


@bp.route("/register", methods=("GET", "POST"))
def register():
    """Register a new user.

    Validates that the username is not already taken. Hashes the
    password for security. Optionally saves a profile picture.
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        photo = request.files.get("photo")
        error = None
        photo_filename = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        elif photo and photo.filename and not allowed_file(photo.filename):
            error = "Invalid image type. Use png, jpg, jpeg, gif or webp."

        if error is None:
            if photo and photo.filename:
                photo_filename = save_profile_picture(photo)

            user = User(
                username=username,
                password=generate_password_hash(password),
                avatar=photo_filename,
            )
            db.session.add(user)

            try:
                db.session.commit()
            except IntegrityError:
                # The username was already taken, which caused the
                # commit to fail. Undo the transaction and show an error.
                db.session.rollback()
                error = f"User {username} is already registered."

                # Remove the uploaded file, since the user was not created.
                delete_profile_picture(photo_filename)
            else:
                # Success, go to the login page.
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Log in a registered user by adding the user id to the session."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None
        user = db.session.execute(
            db.select(User).filter_by(username=username)
        ).scalar_one_or_none()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user.password, password):
            error = "Incorrect password."

        if error is None:
            # store the user id in a new session and return to the index
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    return redirect(url_for("index"))