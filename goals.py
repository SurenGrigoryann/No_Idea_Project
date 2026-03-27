from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import date
from database import get_db

goals_bp = Blueprint("goals", __name__)


@goals_bp.route("/goals", methods=["GET", "POST"])
def goals():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid  = session["uid"]
    conn = get_db()

    if request.method == "POST":
        # Update user profile fields
        conn.execute("""
            UPDATE users SET weight=?, height=?, age=?, budget=? WHERE id=?
        """, (
            float(request.form.get("current_weight", 0)),
            int(request.form.get("height", 0)),
            int(request.form.get("age", 0)),
            int(request.form.get("budget", 0)),
            uid,
        ))

        # Insert new goal
        current_w = float(request.form.get("current_weight", 0))
        conn.execute("""
            INSERT INTO goals (user_id, title, goal_weight, start_weight, created, deadline, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (
            uid,
            request.form.get("title", "New Goal"),
            float(request.form.get("goal_weight", 0)),
            current_w,
            date.today().isoformat(),
            request.form.get("deadline", ""),
        ))

        # Log this weight entry for the chart
        conn.execute(
            "INSERT INTO weight_logs (user_id, date, weight) VALUES (?, ?, ?)",
            (uid, date.today().isoformat(), current_w),
        )

        conn.commit()
        conn.close()
        return redirect(url_for("goals.goals"))

    # GET — load profile + goals from DB
    user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    rows = conn.execute(
        "SELECT * FROM goals WHERE user_id=? ORDER BY created DESC", (uid,)
    ).fetchall()
    conn.close()

    goals_list = []
    for row in rows:
        g = dict(row)
        g["current_weight"] = user["weight"]
        goals_list.append(g)

    data = {
        "app_name":       "FUELFORGE",
        "tagline":        "AI Meal Planner",
        "nav":            ["Home", "Meal Plan", "Progress", "Goals", "Grocery", "Scanner"],
        "active_nav":     "Goals",
        "current_weight": user["weight"],
        "height":         user["height"],
        "age":            user["age"],
        "budget":         user["budget"],
        "goals":          goals_list,
    }

    return render_template("goals.html", d=data)