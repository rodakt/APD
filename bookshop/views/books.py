import json
from math import ceil
from pathlib import Path

from flask import Blueprint, abort, render_template, request

books_bp = Blueprint("books", __name__)

PER_PAGE = 5

_data_path = Path(__file__).parent.parent / "books.json"
BOOKS = json.loads(_data_path.read_text(encoding="utf-8"))
_BOOKS_BY_ID = {book["id"]: book for book in BOOKS}


@books_bp.route("/books")
def listing():
    page = request.args.get("page", 1, type=int)
    total_pages = ceil(len(BOOKS) / PER_PAGE)
    if page < 1 or page > total_pages:
        abort(404)
    start = (page - 1) * PER_PAGE
    page_books = BOOKS[start : start + PER_PAGE]
    return render_template(
        "listing.html",
        books=page_books,
        page=page,
        total_pages=total_pages,
    )


@books_bp.route("/book/<int:book_id>")
def detail(book_id):
    book = _BOOKS_BY_ID.get(book_id)
    if book is None:
        abort(404)
    return render_template("detail.html", book=book)
