"""
database.py
-----------
Single source of truth for the FuelForge database.

Creates fuelforge.db automatically on first run via init_db().
Safe to call init_db() on every startup — uses IF NOT EXISTS + migrations
so existing data is NEVER wiped.

Tables:
  users            — login credentials + profile (weight, height, age, budget, activity_level)
  goals            — per-user goals with deadline, status, weights
  weight_logs      — daily weight entries (used for progress chart)
  meal_plan_days   — per-user meal plan days
  meal_plan_meals  — individual meals inside a plan day
  recipes          — global shared recipe library
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuelforge.db")


# ─────────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────────
def get_db():
    """Return an open SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────────────────────
# Schema creation
# ─────────────────────────────────────────────────────────────
def init_db():
    first_run = not os.path.exists(DB_PATH)
    conn = get_db()
    c = conn.cursor()

    # ── Users ────────────────────────────────────────────────
    # Stores login info AND the user's physical profile.
    # activity_level drives calorie calculations in the meal planner.
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            email             TEXT    NOT NULL UNIQUE,
            password_hash     TEXT    NOT NULL,
            weight            REAL    DEFAULT 0,       -- kg
            height            REAL    DEFAULT 0,       -- cm
            age               INTEGER DEFAULT 0,
            budget            REAL    DEFAULT 0,       -- $ per week
            activity_level    TEXT    DEFAULT 'medium',
            current_streak    INTEGER DEFAULT 0,
            longest_streak    INTEGER DEFAULT 0,
            total_active_days INTEGER DEFAULT 0,
            last_login_date   TEXT    DEFAULT '',
            created_at        TEXT    DEFAULT (date('now'))
        )
    """)

    # ── Goals ────────────────────────────────────────────────
    # Each goal tracks a weight target with a deadline.
    # status: 'active' | 'completed' | 'abandoned'
    c.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title        TEXT    NOT NULL,
            goal_weight  REAL    NOT NULL,  -- kg
            start_weight REAL    NOT NULL,  -- kg at time of creation
            created      TEXT    DEFAULT (date('now')),
            deadline     TEXT    DEFAULT '',
            status       TEXT    DEFAULT 'active'
        )
    """)

    # ── Weight logs ──────────────────────────────────────────
    # One entry per day per user — used to draw the progress chart.
    # Upserted (not duplicated) by goals.py helper.
    c.execute("""
        CREATE TABLE IF NOT EXISTS weight_logs (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date    TEXT    NOT NULL,
            weight  REAL    NOT NULL,
            UNIQUE(user_id, date)   -- enforces one entry per day
        )
    """)

    # ── Recipes ──────────────────────────────────────────────
    # Global recipe library shared across all users.
    # ingredients / instructions stored as JSON arrays.
    c.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            type         TEXT    NOT NULL,  -- Breakfast | Lunch | Snack | Dinner
            time_minutes INTEGER DEFAULT 0,
            calories     REAL    DEFAULT 0,
            protein      REAL    DEFAULT 0,
            carbs        REAL    DEFAULT 0,
            fat          REAL    DEFAULT 0,
            image        TEXT    DEFAULT '',
            ingredients  TEXT    DEFAULT '[]',
            instructions TEXT    DEFAULT '[]'
        )
    """)

    # ── Meal plan days ───────────────────────────────────────
    # Per-user plan days (DAY 1, DAY 2 …) with daily macro totals.
    c.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_days (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            label          TEXT    NOT NULL,  -- "DAY 1"
            name           TEXT    NOT NULL,  -- "Monday"
            total_calories REAL    DEFAULT 0,
            total_protein  REAL    DEFAULT 0,
            total_carbs    REAL    DEFAULT 0,
            total_fat      REAL    DEFAULT 0
        )
    """)

    # ── Meal plan meals ──────────────────────────────────────
    # Individual meals inside a plan day.
    # ingredients / instructions stored as JSON arrays.
    c.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_meals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id       INTEGER NOT NULL REFERENCES meal_plan_days(id) ON DELETE CASCADE,
            type         TEXT    NOT NULL,  -- Breakfast | Lunch | Snack | Dinner
            name         TEXT    NOT NULL,
            time_minutes INTEGER DEFAULT 0,
            calories     REAL    DEFAULT 0,
            protein      REAL    DEFAULT 0,
            carbs        REAL    DEFAULT 0,
            fat          REAL    DEFAULT 0,
            image        TEXT    DEFAULT '',
            ingredients  TEXT    DEFAULT '[]',
            instructions TEXT    DEFAULT '[]'
        )
    """)

    conn.commit()

    # ── Safe migrations (won't fail on fresh DB) ─────────────
    _migrate(c, conn)

    conn.close()
    if first_run:
        print("✓ fuelforge.db created with all tables.")


def _migrate(c, conn):
    """
    Add any columns that were introduced after the initial schema.
    ALTER TABLE only runs if the column doesn't already exist,
    so this is completely safe to call on every startup.
    """
    migrations = {
        "users": [
            ("activity_level",    "TEXT    DEFAULT 'medium'"),
        ],
        "weight_logs": [
            # The UNIQUE constraint can't be added via ALTER TABLE,
            # but duplicates are prevented in goals.py via INSERT OR REPLACE.
        ],
    }

    for table, columns in migrations.items():
        existing = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
        for col_name, col_def in columns:
            if col_name not in existing:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                conn.commit()
                print(f"  ✓ Migration: added {table}.{col_name}")


# ─────────────────────────────────────────────────────────────
# Convenience query helpers
# (import these in blueprints instead of repeating SQL)
# ─────────────────────────────────────────────────────────────

def get_user(uid):
    """Return the user row as a dict, or None."""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_goal(uid):
    """Return the most recent active goal as a dict, or {}."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM goals WHERE user_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (uid,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_weight_logs(uid):
    """Return all weight log rows as a list of dicts, ordered by date."""
    conn = get_db()
    rows = conn.execute(
        "SELECT date, weight FROM weight_logs WHERE user_id=? ORDER BY date", (uid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_weight_log(conn, uid, weight, log_date=None):
    """
    Insert or replace today's (or given date's) weight log.
    Uses INSERT OR REPLACE so duplicates are automatically handled.
    Pass an open `conn` so the caller controls the transaction.
    """
    from datetime import date as _date
    d = log_date or _date.today().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO weight_logs (user_id, date, weight) VALUES (?, ?, ?)",
        (uid, d, weight)
    )


# ─────────────────────────────────────────────────────────────
# Standalone runner
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
