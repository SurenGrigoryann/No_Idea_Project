
from flask import Flask, render_template, request, redirect, url_for, session, flash


app = Flask(__name__)
app.secret_key = "change-this-to-a-secure-random-key"

# Dummy credentials — replace with DB lookup in production
USERS = {
    "admin@example.com": "password123"
}

@app.route("/", methods=["GET"])
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if email in USERS and USERS[email] == password:
            session["user"] = email
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "error")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return f"<h2>Welcome, {session['user']}!</h2><a href='/logout'>Logout</a>"

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
