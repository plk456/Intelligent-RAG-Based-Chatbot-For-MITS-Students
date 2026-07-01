import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load env variables from the absolute root directory path
db_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(db_dir)
dotenv_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=dotenv_path)

# SQLite database file path at the project root
SQLITE_DB_PATH = os.path.join(root_dir, "mits_chatbot.db")

def init_db():
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        # Create users table if not exists
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mits_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    mobile_number TEXT NOT NULL,
                    verified INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.close()
        print(f"[DATABASE] Connected to SQLite database: '{SQLITE_DB_PATH}'")
        print("[DATABASE] SQLite mits_users table checked/created")
    except Exception as e:
        print(f"[DATABASE ERROR] Failed to initialize SQLite database: {e}")

# Keep alias for compatibility with main.py
init_postgres = init_db

# Save verified user details (SQLite)
def save_verified_user(user_id: str, mobile_number: str) -> dict:
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        with conn:
            conn.execute("""
                INSERT INTO mits_users (user_id, mobile_number, verified)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id)
                DO UPDATE SET mobile_number = excluded.mobile_number, verified = 1;
            """, (user_id, mobile_number))
        conn.close()
        print(f"[DATABASE] Saved verified user {user_id} with mobile {mobile_number} to SQLite")
        return {"success": True, "db": "sqlite"}
    except Exception as e:
        print(f"[DATABASE ERROR] Failed to write to SQLite: {e}")
        return {"success": False, "error": str(e)}
