import os
import secrets
import sqlite3
from functools import wraps

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff'
);
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.path.join(app.instance_path, "app.sqlite"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)
    os.makedirs(app.instance_path, exist_ok=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        admin_pw = os.environ.get("ADMIN_PASSWORD")
        if admin_pw and not db.execute("SELECT 1 FROM users").fetchone():
            db.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                ("admin", generate_password_hash(admin_pw)),
            )
            db.commit()

    def csrf_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        return session["_csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def check_csrf():
        if request.method == "POST" and not app.config.get("TESTING_NO_CSRF"):
            if not secrets.compare_digest(request.form.get("_csrf", ""), session.get("_csrf", "x")):
                abort(400)

    def login_required(roles=None):
        def deco(view):
            @wraps(view)
            def wrapped(*a, **kw):
                if "user_id" not in session:
                    return redirect(url_for("login"))
                if roles and session.get("role") not in roles:
                    abort(403)
                return view(*a, **kw)
            return wrapped
        return deco

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = get_db().execute(
                "SELECT * FROM users WHERE username = ?", (request.form.get("username", ""),)
            ).fetchone()
            if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
                session.clear()
                session.update(user_id=user["id"], username=user["username"], role=user["role"])
                return redirect(url_for("dashboard"))
            flash("اسم المستخدم أو كلمة المرور غير صحيحة")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required()
    def dashboard():
        db = get_db()
        total = db.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        recent = db.execute("SELECT * FROM customers ORDER BY id DESC LIMIT 5").fetchall()
        return render_template("dashboard.html", total=total, recent=recent)

    @app.route("/customers")
    @login_required()
    def customers():
        q = request.args.get("q", "").strip()
        like = f"%{q}%"
        rows = get_db().execute(
            "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY id DESC", (like, like)
        ).fetchall()
        return render_template("customers.html", rows=rows, q=q)

    @app.route("/customers/new", methods=["GET", "POST"])
    @login_required()
    def customer_new():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("الاسم مطلوب")
            else:
                db = get_db()
                db.execute(
                    "INSERT INTO customers (name, phone, email, notes) VALUES (?, ?, ?, ?)",
                    (name, request.form.get("phone", "").strip(),
                     request.form.get("email", "").strip(), request.form.get("notes", "").strip()),
                )
                db.commit()
                return redirect(url_for("customers"))
        return render_template("customer_form.html")

    @app.post("/customers/<int:cid>/delete")
    @login_required(roles=("admin",))
    def customer_delete(cid):
        db = get_db()
        db.execute("DELETE FROM customers WHERE id = ?", (cid,))
        db.commit()
        return redirect(url_for("customers"))

    @app.route("/users", methods=["GET", "POST"])
    @login_required(roles=("admin",))
    def users():
        db = get_db()
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "staff")
            if role not in ("admin", "staff") or not username or len(password) < 8:
                flash("بيانات غير صالحة (كلمة المرور 8 أحرف على الأقل)")
            else:
                try:
                    db.execute(
                        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                        (username, generate_password_hash(password), role),
                    )
                    db.commit()
                except sqlite3.IntegrityError:
                    flash("اسم المستخدم موجود مسبقًا")
        rows = db.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
        return render_template("users.html", rows=rows)

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", msg="غير مصرح لك بالوصول"), 403

    return app
