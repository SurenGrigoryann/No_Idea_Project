from flask import Blueprint, render_template, session, redirect, url_for

grocery_bp = Blueprint("grocery", __name__)


@grocery_bp.route("/grocery")
def grocery():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("grocery.html")
