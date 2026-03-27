import json
from flask import Blueprint, render_template, session, redirect, url_for
from database import get_db

meal_bp = Blueprint("meal_plan", __name__)

# Default 3-day plan — seeded into DB on a user's first visit
DEFAULT_DAYS = [
    {
        "label": "DAY 1", "name": "Monday",
        "totals": {"calories": 2850, "protein": 215, "carbs": 285, "fat": 90},
        "meals": [
            {
                "type": "Breakfast", "name": "Power Oatmeal Bowl",
                "time": 10, "calories": 520, "protein": 52, "carbs": 72, "fat": 12,
                "image": "https://www.themealdb.com/images/media/meals/c400ok1764439058.jpg",
                "ingredients": ["1 cup rolled oats", "2 scoops whey protein", "1 cup mixed berries", "2 tbsp almond butter", "1 tbsp honey", "1/2 cup almond milk"],
                "instructions": ["Bring almond milk to a simmer in a saucepan.", "Stir in rolled oats and cook for 5 minutes.", "Remove from heat and mix in whey protein.", "Top with mixed berries, almond butter, and a drizzle of honey."],
            },
            {
                "type": "Lunch", "name": "Grilled Chicken Power Bowl",
                "time": 20, "calories": 480, "protein": 58, "carbs": 65, "fat": 18,
                "image": "https://www.themealdb.com/images/media/meals/1525872624.jpg",
                "ingredients": ["200g chicken breast", "1 cup brown rice", "1/2 cup black beans", "1/2 avocado", "1/4 cup salsa", "1 tsp olive oil", "Salt, pepper, cumin to taste"],
                "instructions": ["Season chicken with salt, pepper, and cumin.", "Grill chicken 6-7 min per side until cooked through.", "Cook brown rice according to package instructions.", "Slice chicken and arrange over rice with beans, avocado, and salsa."],
            },
            {
                "type": "Snack", "name": "Greek Yogurt Protein Pack",
                "time": 5, "calories": 320, "protein": 35, "carbs": 28, "fat": 8,
                "image": "https://www.themealdb.com/images/media/meals/y2irzl1585563479.jpg",
                "ingredients": ["1 cup plain Greek yogurt (0% fat)", "1 scoop vanilla protein powder", "1/4 cup granola", "1/2 cup blueberries", "1 tsp honey"],
                "instructions": ["Stir protein powder into Greek yogurt until smooth.", "Pour into a bowl.", "Top with granola, blueberries, and a drizzle of honey."],
            },
            {
                "type": "Dinner", "name": "Herb Crusted Salmon & Sweet Potato",
                "time": 35, "calories": 760, "protein": 52, "carbs": 68, "fat": 28,
                "image": "https://www.themealdb.com/images/media/meals/1548772327.jpg",
                "ingredients": ["200g salmon fillet", "1 large sweet potato", "2 tbsp olive oil", "2 cloves garlic (minced)", "1 tbsp fresh dill", "1 tbsp fresh parsley", "Lemon juice, salt, pepper"],
                "instructions": ["Preheat oven to 200°C (400°F).", "Cube sweet potato, toss in 1 tbsp olive oil, roast for 25 min.", "Mix garlic, dill, parsley, and remaining olive oil; coat salmon.", "Bake salmon for 12-15 min until it flakes easily.", "Serve salmon over roasted sweet potato with a squeeze of lemon."],
            },
        ],
    },
    {
        "label": "DAY 2", "name": "Tuesday",
        "totals": {"calories": 2780, "protein": 210, "carbs": 270, "fat": 88},
        "meals": [
            {
                "type": "Breakfast", "name": "Egg White Veggie Omelette",
                "time": 15, "calories": 480, "protein": 48, "carbs": 20, "fat": 14,
                "image": "https://www.themealdb.com/images/media/meals/yvpuuy1511797244.jpg",
                "ingredients": ["6 egg whites", "1/2 cup spinach", "1/4 cup diced bell pepper", "1/4 cup mushrooms", "2 tbsp diced onion", "1 tsp olive oil", "Salt and pepper to taste"],
                "instructions": ["Heat olive oil in a non-stick pan over medium heat.", "Sauté vegetables for 3 minutes until softened.", "Pour egg whites over vegetables.", "Cook until edges set, then fold omelette in half.", "Slide onto plate and season with salt and pepper."],
            },
            {
                "type": "Lunch", "name": "Turkey & Quinoa Salad",
                "time": 15, "calories": 520, "protein": 55, "carbs": 62, "fat": 16,
                "image": "https://www.themealdb.com/images/media/meals/k29viq1585565980.jpg",
                "ingredients": ["150g cooked turkey breast (sliced)", "1 cup cooked quinoa", "2 cups mixed greens", "1/4 cup cherry tomatoes", "1/4 cucumber (diced)", "2 tbsp olive oil", "1 tbsp lemon juice", "Salt and pepper"],
                "instructions": ["Cook quinoa and let it cool.", "Combine greens, tomatoes, cucumber, and quinoa in a bowl.", "Slice turkey breast and place on top.", "Whisk olive oil and lemon juice for dressing.", "Drizzle dressing over salad and toss gently."],
            },
            {
                "type": "Snack", "name": "Cottage Cheese & Berries",
                "time": 3, "calories": 280, "protein": 30, "carbs": 32, "fat": 6,
                "image": "https://www.themealdb.com/images/media/meals/fqpqml1764359125.jpg",
                "ingredients": ["1 cup low-fat cottage cheese", "1/2 cup strawberries (sliced)", "1/2 cup blueberries", "1 tsp honey", "Pinch of cinnamon"],
                "instructions": ["Spoon cottage cheese into a bowl.", "Top with strawberries and blueberries.", "Drizzle with honey and sprinkle cinnamon."],
            },
            {
                "type": "Dinner", "name": "Lean Beef Stir Fry & Brown Rice",
                "time": 30, "calories": 720, "protein": 58, "carbs": 72, "fat": 22,
                "image": "https://www.themealdb.com/images/media/meals/kyuxew1763479470.jpg",
                "ingredients": ["200g lean beef strips", "1 cup brown rice", "1 cup broccoli florets", "1/2 cup snap peas", "1/2 red bell pepper", "2 tbsp soy sauce", "1 tbsp sesame oil", "2 cloves garlic", "1 tsp ginger (grated)"],
                "instructions": ["Cook brown rice according to package instructions.", "Heat sesame oil in a wok over high heat.", "Stir-fry beef strips for 3-4 minutes; set aside.", "Stir-fry vegetables with garlic and ginger for 3 minutes.", "Return beef to wok, add soy sauce, toss to combine.", "Serve over brown rice."],
            },
        ],
    },
    {
        "label": "DAY 3", "name": "Wednesday",
        "totals": {"calories": 2900, "protein": 220, "carbs": 295, "fat": 92},
        "meals": [
            {
                "type": "Breakfast", "name": "Protein Pancakes & Banana",
                "time": 20, "calories": 560, "protein": 50, "carbs": 80, "fat": 10,
                "image": "https://www.themealdb.com/images/media/meals/sywswr1511383814.jpg",
                "ingredients": ["1 cup oat flour", "2 scoops protein powder", "2 eggs", "1/2 cup almond milk", "1 tsp baking powder", "1 banana (sliced)", "1 tbsp maple syrup"],
                "instructions": ["Mix oat flour, protein powder, and baking powder in a bowl.", "Whisk in eggs and almond milk until smooth batter forms.", "Heat a non-stick pan over medium heat.", "Pour 1/4 cup batter per pancake; cook 2 min per side.", "Stack pancakes and top with banana slices and maple syrup."],
            },
            {
                "type": "Lunch", "name": "Tuna & Avocado Rice Bowl",
                "time": 10, "calories": 510, "protein": 52, "carbs": 68, "fat": 20,
                "image": "https://www.themealdb.com/images/media/meals/yypwwq1511304979.jpg",
                "ingredients": ["1 can tuna in water (drained)", "1 cup cooked white rice", "1/2 avocado (sliced)", "1/4 cucumber (sliced)", "1 tbsp soy sauce", "1 tsp sesame seeds", "1/2 tsp sriracha (optional)"],
                "instructions": ["Cook rice and let it cool slightly.", "Flake drained tuna with a fork.", "Arrange rice in a bowl; top with tuna, avocado, and cucumber.", "Drizzle with soy sauce and sriracha.", "Sprinkle sesame seeds before serving."],
            },
            {
                "type": "Snack", "name": "Protein Bar & Almonds",
                "time": 1, "calories": 340, "protein": 28, "carbs": 30, "fat": 14,
                "image": "https://www.themealdb.com/images/media/meals/si2rty1763282314.jpg",
                "ingredients": ["1 high-protein bar (20g+ protein)", "30g raw almonds", "1 cup water"],
                "instructions": ["Grab a protein bar with at least 20g protein.", "Pair with a handful of raw almonds.", "Drink plenty of water to stay hydrated."],
            },
            {
                "type": "Dinner", "name": "Baked Chicken Thighs & Vegetables",
                "time": 40, "calories": 730, "protein": 60, "carbs": 65, "fat": 26,
                "image": "https://www.themealdb.com/images/media/meals/nlxald1764112200.jpg",
                "ingredients": ["4 chicken thighs (bone-in, skin-on)", "1 cup broccoli", "1 cup carrots (chopped)", "1 zucchini (sliced)", "2 tbsp olive oil", "1 tsp garlic powder", "1 tsp paprika", "Salt, pepper, fresh thyme"],
                "instructions": ["Preheat oven to 220°C (425°F).", "Rub chicken thighs with olive oil, garlic powder, paprika, salt, and pepper.", "Arrange chicken and vegetables on a baking sheet.", "Drizzle vegetables with remaining olive oil and season.", "Bake for 35-40 min until chicken skin is crispy and internal temp reaches 75°C.", "Rest 5 minutes before serving."],
            },
        ],
    },
]


def seed_meal_plan(uid, conn):
    """Write DEFAULT_DAYS into the DB for a brand-new user."""
    for day in DEFAULT_DAYS:
        t   = day["totals"]
        cur = conn.execute("""
            INSERT INTO meal_plan_days (user_id, label, name, total_calories, total_protein, total_carbs, total_fat)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (uid, day["label"], day["name"], t["calories"], t["protein"], t["carbs"], t["fat"]))
        day_id = cur.lastrowid

        for m in day["meals"]:
            conn.execute("""
                INSERT INTO meal_plan_meals
                    (day_id, type, name, time_minutes, calories, protein, carbs, fat, image, ingredients, instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                day_id, m["type"], m["name"], m["time"],
                m["calories"], m["protein"], m["carbs"], m["fat"], m["image"],
                json.dumps(m["ingredients"]),
                json.dumps(m["instructions"]),
            ))
    conn.commit()


@meal_bp.route("/meal-plan")
def meal_plan():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid  = session["uid"]
    conn = get_db()

    day_rows = conn.execute(
        "SELECT * FROM meal_plan_days WHERE user_id=? ORDER BY label", (uid,)
    ).fetchall()

    # Seed default plan on first visit
    if not day_rows:
        seed_meal_plan(uid, conn)
        day_rows = conn.execute(
            "SELECT * FROM meal_plan_days WHERE user_id=? ORDER BY label", (uid,)
        ).fetchall()

    days = []
    for day in day_rows:
        meal_rows = conn.execute(
            "SELECT * FROM meal_plan_meals WHERE day_id=? ORDER BY id", (day["id"],)
        ).fetchall()

        meals = []
        for m in meal_rows:
            meal = dict(m)
            meal["ingredients"]  = json.loads(meal["ingredients"]  or "[]")
            meal["instructions"] = json.loads(meal["instructions"] or "[]")
            meal["time"]         = meal.pop("time_minutes")
            meals.append(meal)

        days.append({
            "label": day["label"],
            "name":  day["name"],
            "totals": {
                "calories": day["total_calories"],
                "protein":  day["total_protein"],
                "carbs":    day["total_carbs"],
                "fat":      day["total_fat"],
            },
            "meals": meals,
        })

    conn.close()

    data = {
        "app_name":   "FUELFORGE",
        "tagline":    "AI Meal Planner",
        "nav":        ["Home", "Meal Plan", "Progress", "Goals", "Grocery", "Scanner"],
        "active_nav": "Meal Plan",
        "plan_goal":  "muscle gain",
        "days":       days,
    }

    return render_template("mealPlan.html", d=data)