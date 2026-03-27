from flask import Blueprint, render_template, session, redirect, url_for
import json
from database import get_db

home_bp = Blueprint('home', __name__)


@home_bp.route('/')
@home_bp.route('/home')
def home():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid  = session["uid"]
    conn = get_db()

    # Load user profile for stats
    user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())

    # Active goal for goal label
    goal = conn.execute(
        "SELECT * FROM goals WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (uid,)
    ).fetchone()

    # Today's meals — pull from the first day of the user's meal plan
    first_day = conn.execute(
        "SELECT * FROM meal_plan_days WHERE user_id=? ORDER BY label LIMIT 1", (uid,)
    ).fetchone()

    meals = []
    if first_day:
        meal_rows = conn.execute(
            "SELECT * FROM meal_plan_meals WHERE day_id=? ORDER BY id", (first_day["id"],)
        ).fetchall()
        for m in meal_rows:
            meals.append({
                "type":     m["type"].upper(),
                "name":     m["name"],
                "image":    m["image"],
                "calories": m["calories"],
                "protein":  f"{int(m['protein'])}g",
                "carbs":    f"{int(m['carbs'])}g",
                "fat":      f"{int(m['fat'])}g",
            })
    conn.close()

    # Fallback meals if no plan seeded yet
    if not meals:
        meals = [
            {
                "type": "BREAKFAST", "name": "Power Oatmeal Bowl",
                "image": "https://images.unsplash.com/photo-1614961233913-a5113a4a34ed?w=600&q=80",
                "calories": 520, "protein": "32g", "carbs": "72g", "fat": "12g"
            },
            {
                "type": "LUNCH", "name": "Grilled Chicken Power Bowl",
                "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80",
                "calories": 680, "protein": "58g", "carbs": "65g", "fat": "18g"
            },
            {
                "type": "SNACK", "name": "Greek Yogurt Protein Pack",
                "image": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600&q=80",
                "calories": 320, "protein": "35g", "carbs": "28g", "fat": "8g"
            },
            {
                "type": "DINNER", "name": "Herb Crusted Salmon & Sweet Potato",
                "image": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&q=80",
                "calories": 750, "protein": "52g", "carbs": "68g", "fat": "28g"
            }
        ]

    goal_label = goal["title"] if goal else "No Active Goal"
    daily_target = f"{int(sum(m['calories'] if isinstance(m['calories'], (int, float)) else 0 for m in meals))} cal"

    stats = {
        "goal":          goal_label,
        "daily_target":  daily_target,
        "weekly_budget": f"${int(user['budget'])}",
    }

    return render_template('home.html', stats=stats, meals=meals)