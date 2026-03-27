from flask import Flask, render_template

app = Flask(__name__)

# --- Dummy data (replace with DB queries later) ---
data = {
    "app_name": "FUELFORGE",
    "tagline": "AI Meal Planner",
    "nav": ["Home", "Meal Plan", "Progress", "Grocery", "Scanner"],
    "active_nav": "Progress",

    "starting_weight": 92,
    "starting_date": "February 14, 2026",
    "current_weight": 85,
    "weight_change": -7,
    "goal_weight": 80,
    "kg_to_go": 5.0,

    "kg_lost": 7,
    "kg_remaining": 5.0,
    "days_on_journey": 40,
    "goal_total_kg": 12,
    "progress_pct": 20,

    "current_streak": 12,
    "longest_streak": 15,
    "total_active_days": 38,
    "consistency_pct": 95,

    "chart_labels": ["Feb 14", "Feb 21", "Feb 28", "Mar 7", "Mar 14", "Mar 21", "Mar 26"],
    "chart_weights": [92, 91, 90, 88.5, 87, 86, 85],
    "goal_line": 80,

    "kg_per_day": 0.17,
    "weeks_in": 3.5,
    "days_to_goal": 29,
}


@app.route("/")
def progress():
    return render_template("progress.html", d=data)

if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True)
