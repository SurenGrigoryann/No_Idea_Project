from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt
from database import init_db, get_db
from progress_test import progress_bp
from home import home_bp
from goals import goals_bp
from mealPlan import meal_bp
from grocery import grocery_bp

app = Flask(__name__)
app.secret_key = "change-this-to-a-secure-random-key"

# Register all blueprints
app.register_blueprint(progress_bp)
app.register_blueprint(home_bp)
app.register_blueprint(goals_bp)
app.register_blueprint(meal_bp)
app.register_blueprint(grocery_bp)


@app.route("/")
def index():
    if "uid" in session:
        return redirect(url_for("home.home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").encode()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and bcrypt.checkpw(password, user["password_hash"].encode()):
            session["uid"]  = user["id"]
            session["user"] = user["email"]
            return redirect(url_for("home.home"))
        else:
            flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").encode()

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            conn.close()
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        hashed = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
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
        return redirect(url_for("home.home"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()   # creates fuelforge.db + tables on first run
    app.run(debug=True)

print('just for you mobeen')