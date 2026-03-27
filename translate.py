import json
from database import get_db

def translate(uid, gemini_json):
    """
    Parses Gemini's JSON response and saves:
    - Meal plan days + meals  → meal_plan_days, meal_plan_meals
    - Grocery list            → used by grocery.py automatically (reads from meals)
    """

    conn = get_db()

    # ── Wipe old meal plan for this user ────────────────────────────────
    conn.execute("""
        DELETE FROM meal_plan_meals WHERE day_id IN (
            SELECT id FROM meal_plan_days WHERE user_id = ?
        )
    """, (uid,))
    conn.execute("DELETE FROM meal_plan_days WHERE user_id = ?", (uid,))
    conn.commit()

    # ── Save each day + its meals ────────────────────────────────────────
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for day_obj in gemini_json["meal_plan"]:
        day_num   = day_obj["day"]
        day_label = f"DAY {day_num}"
        day_name  = day_names[day_num - 1]
        meals     = day_obj["meals"]

        # Calculate daily totals from all 4 meals
        total_calories = sum(meals[m]["macros"]["calories"] for m in meals)
        total_protein  = sum(meals[m]["macros"]["protein"]  for m in meals)
        total_carbs    = sum(meals[m]["macros"]["carbs"]    for m in meals)
        total_fat      = sum(meals[m]["macros"]["fat"]      for m in meals)

        # Insert the day row
        cursor = conn.execute("""
            INSERT INTO meal_plan_days (user_id, label, name, total_calories, total_protein, total_carbs, total_fat)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (uid, day_label, day_name, total_calories, total_protein, total_carbs, total_fat))

        day_id = cursor.lastrowid

        # Insert each meal (breakfast, lunch, dinner, snack)
        for meal_type, meal_data in meals.items():
            conn.execute("""
                INSERT INTO meal_plan_meals 
                    (day_id, type, name, calories, protein, carbs, fat, ingredients, instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                day_id,
                meal_type.capitalize(),
                meal_data["name"],
                meal_data["macros"]["calories"],
                meal_data["macros"]["protein"],
                meal_data["macros"]["carbs"],
                meal_data["macros"]["fat"],
                json.dumps(meal_data["ingredients"]),
                json.dumps(meal_data["instructions"]),
            ))

    conn.commit()

    # ── Save grocery list ────────────────────────────────────────────
    grocery = gemini_json.get("weekly_grocery_list", {})

    conn.execute("DELETE FROM grocery_items WHERE user_id = ?", (uid,))
    conn.execute("DELETE FROM grocery_meta WHERE user_id = ?", (uid,))

    for category, items in grocery.items():
        if category == "total_estimated_weekly_cost" or not isinstance(items, list):
            continue
        for item_obj in items:
            conn.execute("""
                INSERT INTO grocery_items (user_id, category, item, quantity, est_cost)
                VALUES (?, ?, ?, ?, ?)
            """, (uid, category, item_obj.get("item", ""), item_obj.get("quantity", ""), item_obj.get("est_cost", "")))

    total_cost = grocery.get("total_estimated_weekly_cost", "")
    conn.execute("INSERT INTO grocery_meta (user_id, total_cost) VALUES (?, ?)", (uid, total_cost))

    conn.commit()
    conn.close()
    print(f"✓ Meal plan saved for user {uid} — {len(gemini_json['meal_plan'])} days")


# ── Test runner ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    with open("message.txt", "r") as f:
        data = json.load(f)

    translate(uid=1, gemini_json=data)