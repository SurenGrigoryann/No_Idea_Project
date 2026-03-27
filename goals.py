from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# --- Dummy data (replace with DB queries later) ---
data = {
    "app_name": "FUELFORGE",
    "tagline": "AI Meal Planner",
    "nav": ["Home", "Meal Plan", "Progress", "Goals", "Grocery", "Scanner"],
    "active_nav": "Goals",

    # User profile
    "current_weight": 85,
    "height": 178,
    "age": 28,
    "budget": 150,

    # Goals list
    "goals": [
        {
            "id": 1,
            "title": "Lose Weight",
            "goal_weight": 80,
            "current_weight": 85,
            "start_weight": 92,
            "created": "February 14, 2026",
            "deadline": "April 30, 2026",
            "status": "active",
        },
        {
            "id": 2,
            "title": "Build Muscle",
            "goal_weight": 88,
            "current_weight": 85,
            "start_weight": 83,
            "created": "January 1, 2026",
            "deadline": "June 1, 2026",
            "status": "completed",
        },
    ],
}


@app.route("/", methods=["GET", "POST"])
def goals():
    if request.method == "POST":
        new_goal = {
            "id": len(data["goals"]) + 1,
            "title": request.form.get("title", "New Goal"),
            "goal_weight": float(request.form.get("goal_weight", 0)),
            "current_weight": float(request.form.get("current_weight", data["current_weight"])),
            "start_weight": float(request.form.get("current_weight", data["current_weight"])),
            "created": "March 26, 2026",
            "deadline": request.form.get("deadline", ""),
            "status": "active",
        }
        # Also update profile from form
        data["current_weight"] = float(request.form.get("current_weight", data["current_weight"]))
        data["height"] = int(request.form.get("height", data["height"]))
        data["age"] = int(request.form.get("age", data["age"]))
        data["budget"] = int(request.form.get("budget", data["budget"]))
        data["goals"].append(new_goal)
        return redirect(url_for("goals"))
    return render_template("goals.html", d=data)


if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True)
