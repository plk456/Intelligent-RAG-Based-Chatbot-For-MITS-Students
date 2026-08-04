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
        # Create users and conversations tables if not exists
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mits_conversations (
                    user_id TEXT PRIMARY KEY,
                    conversation_data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.close()
        print(f"[DATABASE] Connected to SQLite database: '{SQLITE_DB_PATH}'")
        print("[DATABASE] SQLite tables checked/created")
    except Exception as e:
        print(f"[DATABASE ERROR] Failed to initialize SQLite database: {e}")

# Keep alias for compatibility with main.py
init_postgres = init_db

# Save verified user details
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

# Save conversation history to SQLite
def save_conversation(user_id: str, conversation: list) -> dict:
    import json
    conversation_str = json.dumps(conversation)
    
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        with conn:
            conn.execute("""
                INSERT INTO mits_conversations (user_id, conversation_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id)
                DO UPDATE SET conversation_data = excluded.conversation_data, updated_at = CURRENT_TIMESTAMP;
            """, (user_id, conversation_str))
        conn.close()
        print(f"[DATABASE] Saved conversation for {user_id} to SQLite")
        return {"success": True, "db": "sqlite"}
    except Exception as e:
        print(f"[DATABASE ERROR] Failed to write conversation to SQLite: {e}")
        return {"success": False, "error": str(e)}

# Load conversation history from SQLite
def load_conversation(user_id: str) -> list:
    try:
        import json
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT conversation_data FROM mits_conversations WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return []
    except Exception as e:
        print(f"[DATABASE ERROR] Failed to load conversation from SQLite: {e}")
        return []
