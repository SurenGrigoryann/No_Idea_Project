from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import date
from database import get_db

goals_bp = Blueprint("goals", __name__)


def log_weight_entry(conn, uid, weight):
    """Insert or update today's weight log entry."""
    existing = conn.execute(
        "SELECT id FROM weight_logs WHERE user_id=? AND date=?",
        (uid, date.today().isoformat())
    ).fetchone()
    if existing:
        conn.execute("UPDATE weight_logs SET weight=? WHERE id=?", (weight, existing["id"]))
    else:
        conn.execute(
            "INSERT INTO weight_logs (user_id, date, weight) VALUES (?, ?, ?)",
            (uid, date.today().isoformat(), weight)
        )


@goals_bp.route("/goals", methods=["GET", "POST"])
def goals():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid  = session["uid"]
    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action", "add_goal")

        # ── Log weight only ──────────────────────────────────────────────
        if action == "log_weight":
            raw = request.form.get("weight", "").strip()
            if raw:
                w = float(raw)
                conn.execute("UPDATE users SET weight=? WHERE id=?", (w, uid))
                log_weight_entry(conn, uid, w)
                conn.commit()
                flash("Weight logged!", "success")
            conn.close()
            return redirect(url_for("goals.goals"))

        # ── Complete a goal ──────────────────────────────────────────────
        if action == "complete_goal":
            gid = request.form.get("goal_id")
            if gid:
                conn.execute(
                    "UPDATE goals SET status='completed' WHERE id=? AND user_id=?",
                    (gid, uid)
                )
                conn.commit()
                flash("Goal marked as completed!", "success")
            conn.close()
            return redirect(url_for("goals.goals"))

        # ── Delete a goal ────────────────────────────────────────────────
        if action == "delete_goal":
            gid = request.form.get("goal_id")
            if gid:
                conn.execute(
                    "DELETE FROM goals WHERE id=? AND user_id=?",
                    (gid, uid)
                )
                conn.commit()
                flash("Goal deleted.", "success")
            conn.close()
            return redirect(url_for("goals.goals"))

        # ── Add new goal (default action) ────────────────────────────────
        title       = request.form.get("title", "").strip()
        goal_weight = request.form.get("goal_weight", "").strip()
        current_w   = request.form.get("current_weight", "").strip()
        deadline    = request.form.get("deadline", "").strip()
        height      = request.form.get("height", "").strip()
        age_val     = request.form.get("age", "").strip()
        budget      = request.form.get("budget", "").strip()

        if not title or not goal_weight or not current_w:
            flash("Goal name, current weight, and target weight are required.", "error")
            conn.close()
            return redirect(url_for("goals.goals"))

        current_w   = float(current_w)
        goal_weight = float(goal_weight)

        # Build dynamic UPDATE for profile fields
        profile = {"weight": current_w}
        if height:  profile["height"] = float(height)
        if age_val: profile["age"]    = int(age_val)
        if budget:  profile["budget"] = float(budget)

        set_clause = ", ".join(f"{k}=?" for k in profile)
        conn.execute(
            f"UPDATE users SET {set_clause} WHERE id=?",
            (*profile.values(), uid)
        )

        # Save goal
        conn.execute("""
            INSERT INTO goals (user_id, title, goal_weight, start_weight, created, deadline, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (uid, title, goal_weight, current_w, date.today().isoformat(), deadline))

        # Log weight entry
        log_weight_entry(conn, uid, current_w)

        conn.commit()
        conn.close()
        flash("Goal saved!", "success")
        return redirect(url_for("goals.goals"))

    # ── GET ──────────────────────────────────────────────────────────────
    user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    rows = conn.execute(
        "SELECT * FROM goals WHERE user_id=? ORDER BY created DESC", (uid,)
    ).fetchall()
    conn.close()

    goals_list = []
    for row in rows:
        g = dict(row)
        g["current_weight"] = user["weight"]
        total = abs(g["start_weight"] - g["goal_weight"])
        done  = abs(g["start_weight"] - user["weight"])
        g["progress_pct"] = min(round((done / total * 100) if total else 0, 1), 100)
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
