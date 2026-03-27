from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt
from database import init_db, get_db
from progress_test import progress_bp
from home import home_bp
from goals import goals_bp
from mealPlan import meal_bp
from grocery import grocery_bp
from register import register_bp

app = Flask(__name__)
app.secret_key = "change-this-to-a-secure-random-key"

# Register all blueprints
app.register_blueprint(progress_bp)
app.register_blueprint(home_bp)
app.register_blueprint(goals_bp)
app.register_blueprint(meal_bp)
app.register_blueprint(grocery_bp)
app.register_blueprint(register_bp)


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



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()   # creates fuelforge.db + tables on first run
    app.run(debug=True)

print('just for you mobeen')
