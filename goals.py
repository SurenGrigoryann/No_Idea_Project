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

    prompt = f"""You are an expert nutritionist and meal planning AI. Your job is to create a complete, personalized 7-day meal plan based on the user's physical stats and goals.
User Stats:

Height: {user['height']} cm
Current Weight: {user['weight']} kg
Goal Weight: {goal['goal_weight']} kg
Age: {user['age']}
Activity Level: {activity_text} (Sedentary / Lightly Active / Moderately Active / Very Active / Athlete)

Your task — return ALL of the following:
DAILY CALORIE & MACRO TARGETS
Calculate TDEE based on the stats above, then adjust calories for the goal (cut/bulk/maintain). Return daily targets for: Calories, Protein (g), Carbs (g), Fat (g).
7-DAY MEAL PLAN
For each day (Day 1 through Day 7), provide exactly 4 meals: Breakfast, Lunch, Dinner, and a Snack. For each meal include:

Meal name
Ingredients with exact quantities
Step-by-step cooking instructions
Full macro breakdown (calories, protein, carbs, fat)
WEEKLY GROCERY LIST
Combine all ingredients from all 7 days. Group them into categories: Proteins, Carbs, Vegetables, Fruits, Pantry. For each item include the total quantity needed for the week and estimated cost. Show the total estimated weekly cost at the end.
RULES YOU MUST FOLLOW:

Every meal must hit close to the daily macro targets
No meal should repeat more than once across the 7 days
Meals must be realistic, easy to cook, and use affordable whole foods

Return everything as clean structured JSON so it can be parsed by a web app

Return the entire response as valid JSON only. No extra text, no markdown, no explanation outside the JSON."""

    try:
        import time
        from google import genai as new_genai
        client = new_genai.Client(api_key=api_key)

        # Retry up to 3 times on rate limit (429)
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config={"max_output_tokens": 8200},
                )
                break
            except Exception as retry_err:
                if "429" in str(retry_err) and attempt < 2:
                    wait = 30 * (attempt + 1)
                    print(f"⚠ Rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise

        text = response.text.strip() if hasattr(response, "text") else response.candidates[0].content.parts[0].text.strip()
        # Strip markdown code fences if Gemini adds them
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        data = json.loads(text)
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
