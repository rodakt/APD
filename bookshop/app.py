from flask import Flask

from views.books import books_bp

# static_url_path="" maps bookshop/static/ to the root URL,
# so static/robots.txt is served at /robots.txt
app = Flask(__name__, static_url_path="", static_folder="static")
app.register_blueprint(books_bp)
