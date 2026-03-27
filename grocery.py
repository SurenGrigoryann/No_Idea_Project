import json
from flask import Blueprint, render_template, session, redirect, url_for
from database import get_db

grocery_bp = Blueprint("grocery", __name__)


@grocery_bp.route("/grocery")
def grocery():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid  = session["uid"]
    conn = get_db()

    # Pull all meal ingredients from the user's meal plan
    meals = conn.execute("""
        SELECT m.ingredients
        FROM meal_plan_meals m
        JOIN meal_plan_days d ON m.day_id = d.id
        WHERE d.user_id = ?
    """, (uid,)).fetchall()
    conn.close()

    # Flatten + deduplicate
    ingredient_set = set()
    for row in meals:
        try:
            for item in json.loads(row["ingredients"] or "[]"):
                ingredient_set.add(item.strip())
        except (json.JSONDecodeError, TypeError):
            pass

    grocery_list = sorted(ingredient_set)

    return render_template("grocery.html", grocery_list=grocery_list)