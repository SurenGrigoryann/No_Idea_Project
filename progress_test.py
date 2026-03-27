from flask import Blueprint, render_template, session, redirect, url_for
from datetime import date, timedelta
from database import get_db

progress_bp = Blueprint('progress', __name__)


def update_streak(uid, conn):
    """Auto-update login streak on each /progress visit."""
    user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last      = user.get("last_login_date", "") or ""

    if last == today:
        return user  # already counted today

    new_streak = user["current_streak"] + 1 if last == yesterday else 1
    longest    = max(user["longest_streak"], new_streak)
    total      = user["total_active_days"] + 1

    conn.execute("""
        UPDATE users
        SET current_streak=?, longest_streak=?, total_active_days=?, last_login_date=?
        WHERE id=?
    """, (new_streak, longest, total, today, uid))
    conn.commit()

    user.update({
        "current_streak":    new_streak,
        "longest_streak":    longest,
        "total_active_days": total,
        "last_login_date":   today,
    })
    return user


@progress_bp.route('/progress')
def progress():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid  = session["uid"]
    conn = get_db()

    # Streak update + user profile
    user = update_streak(uid, conn)

    # Weight logs for chart
    logs = conn.execute(
        "SELECT date, weight FROM weight_logs WHERE user_id=? ORDER BY date", (uid,)
    ).fetchall()
    chart_labels  = [r["date"]   for r in logs]
    chart_weights = [r["weight"] for r in logs]

    # Most recent active goal
    goal_row = conn.execute(
        "SELECT * FROM goals WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (uid,)
    ).fetchone()
    conn.close()

    goal      = dict(goal_row) if goal_row else {}
    current_w = user["weight"] or 0
    start_w   = goal.get("start_weight", current_w)
    goal_w    = goal.get("goal_weight",  current_w)

    # Safe calculations — avoid division by zero
    kg_lost    = round(start_w - current_w, 1)
    goal_total = round(abs(start_w - goal_w), 1)

    if goal_total > 0:
        progress_pct = round(min(abs(kg_lost) / goal_total * 100, 100), 1)
    else:
        progress_pct = 0

    days_on_journey = max(len(logs), user["total_active_days"], 1)

    if days_on_journey > 0 and kg_lost != 0:
        kg_per_day = round(abs(kg_lost) / days_on_journey, 2)
    else:
        kg_per_day = 0

    if kg_per_day > 0 and current_w > goal_w:
        days_to_goal = round((current_w - goal_w) / kg_per_day)
    else:
        days_to_goal = 0

    consistency_pct = round(user["total_active_days"] / days_on_journey * 100) if days_on_journey else 0

    data = {
        "app_name":         "FUELFORGE",
        "tagline":          "AI Meal Planner",
        "nav":              ["Home", "Meal Plan", "Progress", "Goals", "Grocery", "Scanner"],
        "active_nav":       "Progress",

        # Weight stats
        "starting_weight":  start_w,
        "starting_date":    goal.get("created", "—"),
        "current_weight":   current_w,
        "weight_change":    round(current_w - start_w, 1),
        "goal_weight":      goal_w,
        "kg_to_go":         round(max(current_w - goal_w, 0), 1),

        # Journey stats
        "kg_lost":          abs(kg_lost),
        "kg_remaining":     round(max(current_w - goal_w, 0), 1),
        "days_on_journey":  days_on_journey,
        "goal_total_kg":    goal_total,
        "progress_pct":     progress_pct,

        # Streaks
        "current_streak":   user["current_streak"],
        "longest_streak":   user["longest_streak"],
        "total_active_days":user["total_active_days"],
        "consistency_pct":  consistency_pct,

        # Chart
        "chart_labels":     chart_labels,
        "chart_weights":    chart_weights,
        "goal_line":        goal_w,

        # Predictions
        "kg_per_day":       kg_per_day,
        "weeks_in":         round(days_on_journey / 7, 1),
        "days_to_goal":     days_to_goal,

        # Goal info for display
        "goal_title":       goal.get("title", "No active goal"),
        "goal_deadline":    goal.get("deadline", "—"),
    }

    return render_template('progress.html', d=data)
