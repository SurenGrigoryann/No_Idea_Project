from flask import Blueprint, render_template, session, redirect, url_for
from datetime import date, timedelta
from collections import OrderedDict
from database import get_db

progress_bp = Blueprint('progress', __name__)

ACTIVITY_MULTIPLIERS = {
    "very_low":  1.2,
    "low":       1.375,
    "medium":    1.55,
    "high":      1.725,
    "very_high": 1.9,
}


def update_streak(uid, conn):
    """Increment streak on new day, reset if a day was missed, no-op if same day."""
    user      = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last      = user.get("last_login_date") or ""

    if last == today:
        return user

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


def _predicted_weights(start_weight, height, age, activity_level, meal_calories):
    """
    Formula: W(t+1) = W(t) + (Ct - α × (10×W(t) + 6.25×H - 5×A)) / 7700
    Returns list of weights: [day0, day1, ..., day_n] (len = len(meal_calories) + 1)
    """
    alpha  = ACTIVITY_MULTIPLIERS.get(activity_level or "medium", 1.55)
    result = [round(start_weight, 2)]
    w      = start_weight
    for ct in meal_calories:
        tdee = alpha * (15 * w + 6.25 * height - 5 * age)
        w    = w + (ct - tdee) / 7700
        result.append(round(w, 2))
    return result


@progress_bp.route('/progress')
def progress():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid  = session["uid"]
    conn = get_db()

    user = update_streak(uid, conn)

    # Actual weight logs
    logs = conn.execute(
        "SELECT date, weight FROM weight_logs WHERE user_id=? ORDER BY date", (uid,)
    ).fetchall()
    actual_labels  = [r["date"]   for r in logs]
    actual_weights = [r["weight"] for r in logs]

    # Most recent active goal
    goal_row = conn.execute(
        "SELECT * FROM goals WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (uid,)
    ).fetchone()

    # Meal plan calories per day (ordered DAY 1 → DAY 7)
    plan_rows = conn.execute(
        "SELECT total_calories FROM meal_plan_days WHERE user_id=? ORDER BY label",
        (uid,)
    ).fetchall()
    conn.close()

    goal      = dict(goal_row) if goal_row else {}
    current_w = user["weight"] or 0
    start_w   = goal.get("start_weight", current_w)
    goal_w    = goal.get("goal_weight",  current_w)

    # ── Predicted weights ────────────────────────────────────────────
    pred_labels  = []
    pred_weights = []
    kg_per_day_pred  = 0
    days_to_goal_pred = 0

    if plan_rows and current_w and user.get("height") and user.get("age"):
        meal_cals = [r["total_calories"] for r in plan_rows]
        pw = _predicted_weights(
            start_weight   = current_w,
            height         = user["height"],
            age            = user["age"],
            activity_level = user.get("activity_level", "medium"),
            meal_calories  = meal_cals,
        )
        today = date.today()
        for i, w in enumerate(pw):
            pred_labels.append((today + timedelta(days=i)).isoformat())
            pred_weights.append(w)

        # Predicted daily change (average over 7 days)
        total_change     = pw[-1] - pw[0]
        kg_per_day_pred  = round(abs(total_change) / len(meal_cals), 3)

        # Days to goal based on predicted rate
        if kg_per_day_pred > 0:
            days_to_goal_pred = round(abs(goal_w - current_w) / kg_per_day_pred)

    # ── Merge actual + predicted labels for chart ────────────────────
    date_map = OrderedDict()
    for lbl, w in zip(actual_labels, actual_weights):
        date_map[lbl] = [w, None]
    for lbl, w in zip(pred_labels, pred_weights):
        if lbl not in date_map:
            date_map[lbl] = [None, None]
        date_map[lbl][1] = w

    sorted_dates     = sorted(date_map.keys())
    chart_labels     = sorted_dates
    chart_weights    = [date_map[d][0] for d in sorted_dates]
    chart_predicted  = [date_map[d][1] for d in sorted_dates]

    # ── Stats ────────────────────────────────────────────────────────
    kg_lost    = round(start_w - current_w, 1)
    goal_total = round(abs(start_w - goal_w), 1)

    progress_pct = round(min(abs(kg_lost) / goal_total * 100, 100), 1) if goal_total > 0 else 0

    days_on_journey = max(len(logs), user["total_active_days"], 1)
    consistency_pct = round(user["total_active_days"] / days_on_journey * 100) if days_on_journey else 0

    # Use predicted rate if available, else fall back to actual
    kg_per_day   = kg_per_day_pred if kg_per_day_pred > 0 else (
        round(abs(kg_lost) / days_on_journey, 3) if kg_lost != 0 else 0
    )
    days_to_goal = days_to_goal_pred if days_to_goal_pred > 0 else (
        round((current_w - goal_w) / kg_per_day) if kg_per_day > 0 and current_w > goal_w else 0
    )

    data = {
        "app_name":         "FUELFORGE",
        "tagline":          "AI Meal Planner",
        "nav":              ["Home", "Meal Plan", "Progress", "Goals", "Grocery", "Scanner"],
        "active_nav":       "Progress",

        "starting_weight":  start_w,
        "starting_date":    goal.get("created", "—"),
        "current_weight":   current_w,
        "weight_change":    round(current_w - start_w, 1),
        "goal_weight":      goal_w,
        "kg_to_go":         round(abs(goal_w - current_w), 1),

        "kg_lost":          abs(kg_lost),
        "kg_remaining":     round(abs(goal_w - current_w), 1),
        "days_on_journey":  days_on_journey,
        "goal_total_kg":    goal_total,
        "progress_pct":     progress_pct,

        "current_streak":   user["current_streak"],
        "longest_streak":   user["longest_streak"],
        "total_active_days":user["total_active_days"],
        "consistency_pct":  consistency_pct,

        "chart_labels":     chart_labels,
        "chart_weights":    chart_weights,
        "chart_predicted":  chart_predicted,
        "goal_line":        goal_w,

        "kg_per_day":       kg_per_day,
        "weeks_in":         round(days_on_journey / 7, 1),
        "days_to_goal":     days_to_goal,

        "goal_title":       goal.get("title", "No active goal"),
        "goal_deadline":    goal.get("deadline", "—"),
    }

    return render_template('progress.html', d=data)
