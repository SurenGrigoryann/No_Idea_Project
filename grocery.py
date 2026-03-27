from collections import defaultdict
from flask import Blueprint, render_template, session, redirect, url_for
from database import get_db

grocery_bp = Blueprint("grocery", __name__)

CATEGORY_ORDER = ["proteins", "carbs", "vegetables_and_fruits", "pantry"]


@grocery_bp.route("/grocery")
def grocery():
    if "uid" not in session:
        return redirect(url_for("login"))

    uid  = session["uid"]
    conn = get_db()

    rows = conn.execute("""
        SELECT category, item, quantity, est_cost
        FROM grocery_items WHERE user_id = ?
        ORDER BY id
    """, (uid,)).fetchall()

    meta = conn.execute(
        "SELECT total_cost FROM grocery_meta WHERE user_id = ?", (uid,)
    ).fetchone()

    conn.close()

    # Group by category, compute per-category total
    raw = defaultdict(list)
    for row in rows:
        raw[row["category"]].append(dict(row))

    categories = []
    for key in CATEGORY_ORDER:
        items = raw.get(key, [])
        if not items:
            continue
        total = 0.0
        for item in items:
            try:
                total += float(item["est_cost"].replace("$", "").replace(",", ""))
            except (ValueError, AttributeError):
                pass
        categories.append({
            "key":   key,
            "items": items,
            "total": f"${total:.2f}",
        })

    total_cost  = meta["total_cost"] if meta else ""
    total_items = len(rows)

    return render_template("grocery.html",
                           categories=categories,
                           total_cost=total_cost,
                           total_items=total_items)
