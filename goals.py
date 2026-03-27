import json
import os
import threading

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import date
from database import get_db, upsert_weight_log

goals_bp = Blueprint("goals", __name__)

VALID_ACTIVITY_LEVELS = {"very_low", "low", "medium", "high", "very_high"}

ACTIVITY_LABELS = {
    "very_low":  "Sedentary",
    "low":       "Lightly Active",
    "medium":    "Moderately Active",
    "high":      "Very Active",
    "very_high": "Athlete",
}


def _load_gemini_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None


def _generate_meal_plan(uid):
    """Calls Gemini and saves the result. Runs in a background thread."""
    from translate import translate

    api_key = _load_gemini_key()
    if not api_key:
        print("⚠ No GEMINI_API_KEY found — skipping meal plan generation")
        return

    conn = get_db()
    user = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    goal = conn.execute(
        "SELECT * FROM goals WHERE user_id=? AND status='active' ORDER BY created DESC LIMIT 1",
        (uid,)
    ).fetchone()
    conn.close()

    if not goal:
        return

    goal = dict(goal)
    activity_text = ACTIVITY_LABELS.get(user.get("activity_level", "medium"), "Moderately Active")

    prompt = f"""You are a nutritionist AI. Generate a personalized 7-day meal plan for the user below.

USER STATS:
- Height: {user['height']} cm
- Current Weight: {user['weight']} kg
- Goal Weight: {goal['goal_weight']} kg
- Age: {user['age']} years
- Activity Level: {activity_text}

CRITICAL INSTRUCTIONS:
1. Your entire response must be a single valid JSON object.
2. Do NOT include any text before or after the JSON.
3. Do NOT use markdown, code fences, or backticks.
4. Do NOT add comments inside the JSON.
5. Use EXACTLY the key names shown below — no uppercase, no underscores changed, no extra keys.
6. "meal_plan" must be a JSON array [ ] containing exactly 7 objects, one per day.
7. Each day object must have "day" (integer 1-7) and "meals" (object with keys: breakfast, lunch, dinner, snack).
8. Each meal must have: "name" (string), "ingredients" (array of strings), "instructions" (array of strings), "macros" (object with keys: calories, protein, carbs, fat — all numbers).
9. No meal name may repeat across the 7 days.
10. "weekly_grocery_list" must have exactly these keys: "proteins", "carbs", "vegetables_and_fruits", "pantry", "total_estimated_weekly_cost".
11. Each grocery item must have exactly: "item" (string), "quantity" (string), "est_cost" (string).

OUTPUT THIS EXACT JSON STRUCTURE (replace values, keep all key names identical):

{{
  "daily_calorie_and_macro_targets": {{
    "calculation_notes": "BMR and TDEE calculation notes here",
    "targets": {{
      "calories": 2500,
      "protein_g": 150,
      "carbs_g": 300,
      "fat_g": 70
    }}
  }},
  "meal_plan": [
    {{
      "day": 1,
      "meals": {{
        "breakfast": {{
          "name": "Meal name here",
          "ingredients": ["100g oats", "1 banana"],
          "instructions": ["Step 1", "Step 2"],
          "macros": {{"calories": 500, "protein": 30, "carbs": 80, "fat": 10}}
        }},
        "lunch": {{
          "name": "Meal name here",
          "ingredients": ["200g chicken breast", "150g rice"],
          "instructions": ["Step 1", "Step 2"],
          "macros": {{"calories": 600, "protein": 50, "carbs": 70, "fat": 12}}
        }},
        "dinner": {{
          "name": "Meal name here",
          "ingredients": ["200g salmon", "400g potatoes"],
          "instructions": ["Step 1", "Step 2"],
          "macros": {{"calories": 700, "protein": 45, "carbs": 80, "fat": 22}}
        }},
        "snack": {{
          "name": "Meal name here",
          "ingredients": ["200g greek yogurt", "50g granola"],
          "instructions": ["Step 1"],
          "macros": {{"calories": 300, "protein": 20, "carbs": 40, "fat": 8}}
        }}
      }}
    }},
    {{ "day": 2, "meals": {{ "breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snack": {{}} }} }},
    {{ "day": 3, "meals": {{ "breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snack": {{}} }} }},
    {{ "day": 4, "meals": {{ "breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snack": {{}} }} }},
    {{ "day": 5, "meals": {{ "breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snack": {{}} }} }},
    {{ "day": 6, "meals": {{ "breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snack": {{}} }} }},
    {{ "day": 7, "meals": {{ "breakfast": {{}}, "lunch": {{}}, "dinner": {{}}, "snack": {{}} }} }}
  ],
  "weekly_grocery_list": {{
    "proteins": [
      {{"item": "Chicken Breast", "quantity": "700g", "est_cost": "$10.00"}}
    ],
    "carbs": [
      {{"item": "Rolled Oats", "quantity": "500g", "est_cost": "$3.00"}}
    ],
    "vegetables_and_fruits": [
      {{"item": "Bananas", "quantity": "7 pieces", "est_cost": "$2.00"}}
    ],
    "pantry": [
      {{"item": "Olive Oil", "quantity": "1 bottle", "est_cost": "$6.00"}}
    ],
    "total_estimated_weekly_cost": "$150.00"
  }}
}}

Now generate the full 7-day plan for the user stats above. Return ONLY the JSON."""

    try:
        from google import genai as new_genai
        client = new_genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"max_output_tokens": 32000, "thinking_config": {"thinking_budget": 0}},
        )

        text = response.text.strip() if hasattr(response, "text") else response.candidates[0].content.parts[0].text.strip()
        # Strip markdown code fences if Gemini adds them
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        data = json.loads(text)

        # Normalize keys in case Gemini uses different names
        normalized = {}
        for k, v in data.items():
            kl = k.lower()
            if "meal_plan" in kl or "seven" in kl or "7" in kl:
                normalized["meal_plan"] = v
            elif "calorie" in kl or "macro" in kl:
                normalized["daily_calorie_and_macro_targets"] = v
            elif "grocery" in kl:
                normalized["weekly_grocery_list"] = v
        if "meal_plan" in normalized:
            data = normalized

        translate(uid=uid, gemini_json=data)
        print(f"✓ Gemini meal plan generated and saved for user {uid}")
    except Exception as e:
        print(f"⚠ Gemini meal plan generation failed for user {uid}: {e}")


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
                upsert_weight_log(conn, uid, w)
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

        # ── Add new goal ─────────────────────────────────────────────────
        title          = request.form.get("title", "").strip()
        goal_weight    = request.form.get("goal_weight", "").strip()
        current_w      = request.form.get("current_weight", "").strip()
        deadline       = request.form.get("deadline", "").strip()
        height         = request.form.get("height", "").strip()
        age_val        = request.form.get("age", "").strip()
        budget         = request.form.get("budget", "").strip()
        activity_level = request.form.get("activity_level", "").strip()

        if not title or not goal_weight or not current_w:
            flash("Goal name, current weight, and target weight are required.", "error")
            conn.close()
            return redirect(url_for("goals.goals"))

        current_w   = float(current_w)
        goal_weight = float(goal_weight)

        # Update profile — only fields that were actually submitted
        profile = {"weight": current_w}
        if height:  profile["height"] = float(height)
        if age_val: profile["age"]    = int(age_val)
        if budget:  profile["budget"] = float(budget)
        if activity_level and activity_level in VALID_ACTIVITY_LEVELS:
            profile["activity_level"] = activity_level

        set_clause = ", ".join(f"{k}=?" for k in profile)
        conn.execute(
            f"UPDATE users SET {set_clause} WHERE id=?",
            (*profile.values(), uid)
        )

        # Save the goal
        conn.execute("""
            INSERT INTO goals (user_id, title, goal_weight, start_weight, created, deadline, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (uid, title, goal_weight, current_w, date.today().isoformat(), deadline))

        # Log today's weight
        upsert_weight_log(conn, uid, current_w)

        conn.commit()
        conn.close()

        # Fire Gemini in the background so the page redirects immediately
        threading.Thread(target=_generate_meal_plan, args=(uid,), daemon=True).start()

        flash("Goal saved! Your meal plan is being generated in the background.", "success")
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
        "activity_level": user.get("activity_level") or "medium",
        "goals":          goals_list,
    }

    return render_template("goals.html", d=data)
