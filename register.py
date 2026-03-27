import re
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_db

register_bp = Blueprint("register", __name__)


def validate_password(password: str):
    """
    Returns a list of error strings.
    Empty list means the password passed all checks.
    """
    errors = []
    if len(password) < 12:
        errors.append("At least 12 characters long")
    if not re.search(r"[A-Z]", password):
        errors.append("At least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("At least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("At least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/`~]", password):
        errors.append("At least one special character (!@#$%^&* …)")
    return errors


@register_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email     = request.form.get("email", "").strip().lower()
        password  = request.form.get("password", "")
        confirm   = request.form.get("confirm_password", "")

        # ── Password match ───────────────────────────────────────────────
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html", email=email)

        # ── Password strength ────────────────────────────────────────────
        errors = validate_password(password)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", email=email)

        # ── Duplicate email check ────────────────────────────────────────
        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            conn.close()
            flash("An account with that email already exists.", "error")
            return render_template("register.html", email=email)

        # ── All good — create user ───────────────────────────────────────
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur = conn.execute("""
            INSERT INTO users (email, password_hash, weight, height, age, budget)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            email, hashed,
            float(request.form.get("weight", 0)),
            float(request.form.get("height", 0)),
            int(request.form.get("age", 0)),
            float(request.form.get("budget", 0)),
        ))
        conn.commit()
        session["uid"]  = cur.lastrowid
        session["user"] = email
        conn.close()

        flash("Account created! Welcome to FuelForge.", "success")
        return redirect(url_for("home.home"))

    return render_template("register.html", email="")
