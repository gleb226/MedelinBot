import sqlite3
from app.common.config import MENU_DB_PATH

class MenuDatabase:
    def __init__(self):
        self.db_name = MENU_DB_PATH
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
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                price TEXT,
                description TEXT,
                volume TEXT
            )
        ''')

    def add_item(self, category, name, price, description="", volume=""):
        self._execute(
            "INSERT INTO menu (category, name, price, description, volume) VALUES (?, ?, ?, ?, ?)",
            (category, name, price, description, volume)
        )

    def get_categories(self):
        return [r[0] for r in self._execute("SELECT DISTINCT category FROM menu", fetchall=True)]

    def get_items_by_category(self, category):
        return self._execute("SELECT id, name, price, description, volume FROM menu WHERE category = ?", (category,), fetchall=True)

    def get_item_by_id(self, item_id):
        return self._execute("SELECT * FROM menu WHERE id = ?", (item_id,), fetchone=True)

menu_db = MenuDatabase()
