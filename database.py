"""
database.py
-----------
Run this file once to create fuelforge.db and all tables:
    python database.py

Then import get_db() anywhere you need a DB connection.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "fuelforge.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row        # access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users — login info + profile
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            email             TEXT    NOT NULL UNIQUE,
            password_hash     TEXT    NOT NULL,
            weight            REAL    DEFAULT 0,
            height            REAL    DEFAULT 0,
            age               INTEGER DEFAULT 0,
            budget            REAL    DEFAULT 0,
            current_streak    INTEGER DEFAULT 0,
            longest_streak    INTEGER DEFAULT 0,
            total_active_days INTEGER DEFAULT 0,
            last_login_date   TEXT    DEFAULT '',
            created_at        TEXT    DEFAULT (date('now'))
        )
    """)

    # Goals
    c.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id),
            title        TEXT    NOT NULL,
            goal_weight  REAL    NOT NULL,
            start_weight REAL    NOT NULL,
            created      TEXT    DEFAULT (date('now')),
            deadline     TEXT    DEFAULT '',
            status       TEXT    DEFAULT 'active'
        )
    """)

    # Daily weight logs (used for chart)
    c.execute("""
        CREATE TABLE IF NOT EXISTS weight_logs (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date    TEXT    NOT NULL,
            weight  REAL    NOT NULL
        )
    """)

    # Recipes — global, shared across all users
    c.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            type         TEXT NOT NULL,
            time_minutes INTEGER DEFAULT 0,
            calories     REAL DEFAULT 0,
            protein      REAL DEFAULT 0,
            carbs        REAL DEFAULT 0,
            fat          REAL DEFAULT 0,
            image        TEXT DEFAULT '',
            ingredients  TEXT DEFAULT '',    -- stored as JSON
            instructions TEXT DEFAULT ''     -- stored as JSON
        )
    """)

    # Meal plan days (per user)
    c.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_days (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(id),
            label          TEXT NOT NULL,
            name           TEXT NOT NULL,
            total_calories REAL DEFAULT 0,
            total_protein  REAL DEFAULT 0,
            total_carbs    REAL DEFAULT 0,
            total_fat      REAL DEFAULT 0
        )
    """)

    # Individual meals inside a plan day
    c.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_meals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id       INTEGER NOT NULL REFERENCES meal_plan_days(id),
            type         TEXT NOT NULL,
            name         TEXT NOT NULL,
            time_minutes INTEGER DEFAULT 0,
            calories     REAL DEFAULT 0,
            protein      REAL DEFAULT 0,
            carbs        REAL DEFAULT 0,
            fat          REAL DEFAULT 0,
            image        TEXT DEFAULT '',
            ingredients  TEXT DEFAULT '',   -- stored as JSON
            instructions TEXT DEFAULT ''    -- stored as JSON
        )
    """)

    conn.commit()
    conn.close()
    print("fuelforge.db created and all tables ready.")


if __name__ == "__main__":
    init_db()
#wff