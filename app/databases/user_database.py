import sqlite3
from datetime import datetime
from app.common.config import USERS_DB_PATH

class UserDatabase:
    def __init__(self):
        self.db_name = USERS_DB_PATH
        self._init_database()

    def _execute(self, query, params=(), fetchone=False, fetchall=False):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()

    def _init_database(self):
        self._execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                phone TEXT,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self._migrate_schema()

    def _migrate_schema(self):
        cols = {row[1] for row in self._execute("PRAGMA table_info(users)", fetchall=True)}
        if "phone" not in cols:
            self._execute("ALTER TABLE users ADD COLUMN phone TEXT")

    def add_user(self, user_id: int, first_name: str, username: str, phone: str = None):
        if not self._execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,), fetchone=True):
            self._execute(
                "INSERT INTO users (user_id, first_name, username, phone, joined_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, first_name, username, phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
        else:
            # оновлюємо ім'я/username/phone, якщо змінились
            self._execute(
                "UPDATE users SET first_name = ?, username = ?, phone = COALESCE(phone, ?) WHERE user_id = ?",
                (first_name, username, phone, user_id)
            )

    def set_phone(self, user_id: int, phone: str):
        self._execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))

    def get_phone(self, user_id: int):
        row = self._execute("SELECT phone FROM users WHERE user_id = ?", (user_id,), fetchone=True)
        return row[0] if row else None

    def get_user_by_username(self, username: str):
        if not username:
            return None
        return self._execute(
            "SELECT user_id, first_name, username, phone FROM users WHERE LOWER(username) = LOWER(?)",
            (username,),
            fetchone=True
        )

    def get_user_by_phone(self, phone: str):
        if not phone:
            return None
        normalized = phone.replace(" ", "")
        return self._execute(
            "SELECT user_id, first_name, username, phone FROM users WHERE REPLACE(phone, ' ', '') = ?",
            (normalized,),
            fetchone=True
        )

user_db = UserDatabase()
