from flask import Blueprint, render_template
 
home_bp = Blueprint('home', __name__)
 
@home_bp.route('/')
@home_bp.route('/home')
def home():
    # You can pass dynamic data from DB/AI here later
    stats = {
        "goal": "Muscle Gain",
        "daily_target": "2,850 cal",
        "weekly_budget": "$150"
    }
 
    meals = [
        {
            "type": "BREAKFAST",
            "name": "Power Oatmeal Bowl",
            "image": "https://images.unsplash.com/photo-1614961233913-a5113a4a34ed?w=600&q=80",
            "calories": 520, "protein": "32g", "carbs": "72g", "fat": "12g"
        },
        {
            "type": "LUNCH",
            "name": "Grilled Chicken Power Bowl",
            "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80",
            "calories": 680, "protein": "58g", "carbs": "65g", "fat": "18g"
        },
        {
            "type": "SNACK",
            "name": "Greek Yogurt Protein Pack",
            "image": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600&q=80",
            "calories": 320, "protein": "35g", "carbs": "28g", "fat": "8g"
        },
        {
            "type": "DINNER",
            "name": "Herb Crusted Salmon & Sweet Potato",
            "image": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&q=80",
            "calories": 750, "protein": "52g", "carbs": "68g", "fat": "28g"
        }
    ]
 
    return render_template('home.html', stats=stats, meals=meals)