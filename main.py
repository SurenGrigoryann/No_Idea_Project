from flask import Flask, render_template, request, redirect, url_for, session, flash
from progress_test import progress_bp
 
app = Flask(__name__)
app.secret_key = "change-this-to-a-secure-random-key"
 
# Register blueprints
app.register_blueprint(progress_bp)
 
# Dummy credentials — replace with DB lookup in production
USERS = {
    "admin@example.com": "password123"
}
 
@app.route("/", methods=["GET"])
def index():
    if "user" in session:
        return redirect(url_for("progress.progress"))
    return redirect(url_for("login"))
 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
 
        if email in USERS and USERS[email] == password:
            session["user"] = email
            return redirect(url_for("progress.progress"))
        else:
            flash("Invalid email or password.", "error")
 
    return render_template("login.html")
 
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
 
if __name__ == "__main__":
    app.run(debug=True)