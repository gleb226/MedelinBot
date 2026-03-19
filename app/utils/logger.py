import sqlite3
from datetime import datetime
from app.common.config import LOGS_DB_PATH

def log_activity(user_id: int, username: str, action: str, details: str = ""):
    with sqlite3.connect(LOGS_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER, 
                username TEXT, 
                action TEXT, 
                details TEXT,
                timestamp TEXT
            )"""
        )
        cursor.execute(
            "INSERT INTO activity_logs (user_id, username, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                username,
                action,
                details,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
        )
        conn.commit()
