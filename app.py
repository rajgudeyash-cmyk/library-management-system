from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from pathlib import Path
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-deployment"
DB_PATH = Path(__file__).with_name("library.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            mobile TEXT NOT NULL DEFAULT '',
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            total_copies INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 0),
            available_copies INTEGER NOT NULL DEFAULT 1 CHECK(available_copies >= 0)
        );
        CREATE TABLE IF NOT EXISTS allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
            book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            issue_date TEXT NOT NULL DEFAULT (date('now')),
            return_date TEXT,
            status TEXT NOT NULL DEFAULT 'Issued'
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if count == 0:
            db.executemany(
                "INSERT INTO books(title, author, category, total_copies, available_copies) VALUES(?,?,?,?,?)",
                [
                    ("The Secret", "Rhonda Byrne", "Self-help", 4, 4),
                    ("Becoming a Master", "Library Collection", "Education", 3, 3),
                    ("The Sun Does Shine", "Anthony Ray Hinton", "Biography", 2, 2),
                    ("Rich Dad Poor Dad", "Robert T. Kiyosaki", "Finance", 5, 5),
                ],
            )

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("member_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    with get_db() as db:
        stats = {
            "members": db.execute("SELECT COUNT(*) FROM members").fetchone()[0],
            "books": db.execute("SELECT COALESCE(SUM(total_copies),0) FROM books").fetchone()[0],
            "available": db.execute("SELECT COALESCE(SUM(available_copies),0) FROM books").fetchone()[0],
            "issued": db.execute("SELECT COUNT(*) FROM allocations WHERE status='Issued'").fetchone()[0],
        }
        books = db.execute("SELECT * FROM books ORDER BY title LIMIT 5").fetchall()
    return render_template("index.html", stats=stats, books=books)

@app.route("/members")
def members():
    q = request.args.get("q", "").strip()
    with get_db() as db:
        if q:
            rows = db.execute("""SELECT * FROM members
                WHERE name LIKE ? OR username LIKE ? OR class_name LIKE ? OR email LIKE ?
                ORDER BY name""", tuple([f"%{q}%"] * 4)).fetchall()
        else:
            rows = db.execute("SELECT * FROM members ORDER BY name").fetchall()
    return render_template("members.html", members=rows, q=q)

@app.route("/members/add", methods=["GET", "POST"])
def add_member():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        class_name = request.form.get("class_name", "").strip()
        email = request.form.get("email", "").strip()
        mobile = request.form.get("mobile", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not all([name, username, password]):
            flash("Name, username, and password are required.", "error")
            return render_template("member_form.html", member=request.form)
        try:
            with get_db() as db:
                db.execute("""INSERT INTO members(name,class_name,email,mobile,username,password)
                    VALUES(?,?,?,?,?,?)""",
                    (name, class_name, email, mobile, username, password))
            flash("Member added successfully.", "success")
            return redirect(url_for("members"))
        except sqlite3.IntegrityError:
            flash("That username already exists. Please choose another.", "error")
    return render_template("member_form.html", member={})

@app.route("/members/<int:member_id>/delete", methods=["POST"])
def delete_member(member_id):
    with get_db() as db:
        db.execute("DELETE FROM members WHERE id=?", (member_id,))
    flash("Member deleted.", "success")
    return redirect(url_for("members"))

@app.route("/books")
def books():
    q = request.args.get("q", "").strip()
    with get_db() as db:
        if q:
            rows = db.execute("""SELECT * FROM books
                WHERE title LIKE ? OR author LIKE ? OR category LIKE ? ORDER BY title""",
                (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows = db.execute("SELECT * FROM books ORDER BY title").fetchall()
    return render_template("books.html", books=rows, q=q)

@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()
        try:
            copies = int(request.form.get("total_copies", "1"))
            if copies < 0:
                raise ValueError
        except ValueError:
            flash("Number of copies must be zero or more.", "error")
            return render_template("book_form.html", book=request.form)
        if not title:
            flash("Book title is required.", "error")
            return render_template("book_form.html", book=request.form)
        with get_db() as db:
            db.execute("""INSERT INTO books(title,author,category,total_copies,available_copies)
                VALUES(?,?,?,?,?)""", (title, author, category, copies, copies))
        flash("Book added successfully.", "success")
        return redirect(url_for("books"))
    return render_template("book_form.html", book={})

@app.route("/books/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    with get_db() as db:
        active = db.execute("SELECT COUNT(*) FROM allocations WHERE book_id=? AND status='Issued'", (book_id,)).fetchone()[0]
        if active:
            flash("This book has active allocations and cannot be deleted yet.", "error")
        else:
            db.execute("DELETE FROM books WHERE id=?", (book_id,))
            flash("Book deleted.", "success")
    return redirect(url_for("books"))

@app.route("/allocations", methods=["GET", "POST"])
def allocations():
    with get_db() as db:
        if request.method == "POST":
            try:
                member_id = int(request.form["member_id"])
                book_id = int(request.form["book_id"])
            except (ValueError, KeyError):
                flash("Choose a member and a book.", "error")
                return redirect(url_for("allocations"))
            book = db.execute("SELECT available_copies FROM books WHERE id=?", (book_id,)).fetchone()
            member = db.execute("SELECT id FROM members WHERE id=?", (member_id,)).fetchone()
            if not member or not book:
                flash("Member or book not found.", "error")
            elif book["available_copies"] < 1:
                flash("No copies of this book are currently available.", "error")
            else:
                db.execute("INSERT INTO allocations(member_id,book_id) VALUES(?,?)", (member_id, book_id))
                db.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (book_id,))
                flash("Book allocated successfully.", "success")
            return redirect(url_for("allocations"))
        rows = db.execute("""SELECT a.*, m.name AS member_name, b.title AS book_title
            FROM allocations a JOIN members m ON m.id=a.member_id JOIN books b ON b.id=a.book_id
            ORDER BY a.id DESC""").fetchall()
        member_rows = db.execute("SELECT id,name,username FROM members ORDER BY name").fetchall()
        book_rows = db.execute("SELECT id,title,available_copies FROM books WHERE available_copies > 0 ORDER BY title").fetchall()
    return render_template("allocations.html", allocations=rows, members=member_rows, books=book_rows)

@app.route("/allocations/<int:allocation_id>/return", methods=["POST"])
def return_book(allocation_id):
    with get_db() as db:
        row = db.execute("SELECT book_id,status FROM allocations WHERE id=?", (allocation_id,)).fetchone()
        if row and row["status"] == "Issued":
            db.execute("UPDATE allocations SET status='Returned', return_date=date('now') WHERE id=?", (allocation_id,))
            db.execute("UPDATE books SET available_copies=MIN(total_copies, available_copies+1) WHERE id=?", (row["book_id"],))
            flash("Book marked as returned.", "success")
        else:
            flash("Allocation was not found or has already been returned.", "error")
    return redirect(url_for("allocations"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as db:
            member = db.execute("SELECT * FROM members WHERE username=? AND password=?", (username, password)).fetchone()
        if member:
            session["member_id"] = member["id"]
            session["member_name"] = member["name"]
            flash(f"Welcome, {member['name']}!", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password. You can add a member first.", "error")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/profile")
@login_required
def profile():
    with get_db() as db:
        member = db.execute("SELECT id,name,class_name,email,mobile,username,created_at FROM members WHERE id=?", (session["member_id"],)).fetchone()
        history = db.execute("""SELECT a.*, b.title FROM allocations a JOIN books b ON b.id=a.book_id
            WHERE a.member_id=? ORDER BY a.id DESC""", (session["member_id"],)).fetchall()
    if not member:
        session.clear()
        return redirect(url_for("login"))
    return render_template("profile.html", member=member, history=history)

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
