import os
import uuid

from flask import Blueprint
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from sqlalchemy.orm import joinedload
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from .auth import login_required
from .models import Post
from .models import db

bp = Blueprint("blog", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    """Check whether the file has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_upload_folder():
    """Return the upload folder path, creating it if needed."""
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    return folder


def save_post_image(file):
    """Sanitize the file name, save the image and return the stored file name."""
    filename = secure_filename(file.filename)
    # Prefix with a random id so equal names from different posts don't collide.
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    file.save(os.path.join(get_upload_folder(), unique_filename))
    return unique_filename


def delete_post_image(filename):
    """Remove an image from the upload folder, if it exists."""
    if not filename:
        return
    path = os.path.join(get_upload_folder(), filename)
    if os.path.exists(path):
        os.remove(path)


@bp.route("/")
def index():
    """Show all the posts, most recent first."""
    posts = (
        db.session.execute(
            db.select(Post)
            .options(joinedload(Post.author))
            .order_by(Post.created.desc())
        )
        .scalars()
        .all()
    )
    return render_template("blog/index.html", posts=posts)


def get_post(id, check_author=True):
    """Get a post and its author by id.

    Checks that the id exists and optionally that the current user is
    the author.

    :param id: id of post to get
    :param check_author: require the current user to be the author
    :return: the post (the author is available as ``post.author``)
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    post = db.session.get(Post, id)

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post.author_id != g.user.id:
        abort(403)

    return post


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new post for the current user."""
    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        image = request.files.get("image")
        error = None

        if not title:
            error = "Title is required."
        elif image and image.filename and not allowed_file(image.filename):
            error = "Invalid image type. Use png, jpg, jpeg, gif or webp."

        if error is not None:
            flash(error)
        else:
            image_filename = None
            if image and image.filename:
                image_filename = save_post_image(image)

            post = Post(
                title=title,
                body=body,
                author_id=g.user.id,
                imagem_post=image_filename,
            )
            db.session.add(post)
            db.session.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/create.html")


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    post = get_post(id)

    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        image = request.files.get("image")
        error = None

        if not title:
            error = "Title is required."
        elif image and image.filename and not allowed_file(image.filename):
            error = "Invalid image type. Use png, jpg, jpeg, gif or webp."

        if error is not None:
            flash(error)
        else:
            old_image = post.imagem_post

            post.title = title
            post.body = body

            # Keep the current image unless a new one was uploaded.
            if image and image.filename:
                post.imagem_post = save_post_image(image)

            db.session.commit()

            # Only remove the old file after the commit succeeded.
            if image and image.filename:
                delete_post_image(old_image)

            return redirect(url_for("blog.index"))

    return render_template("blog/update.html", post=post)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a post.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    post = get_post(id)
    image_filename = post.imagem_post

    db.session.delete(post)
    db.session.commit()
    delete_post_image(image_filename)
    return redirect(url_for("blog.index"))