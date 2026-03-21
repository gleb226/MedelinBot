import aiosqlite
from app.common.config import MENU_DB_PATH


class MenuDatabase:
    def __init__(self):
        self.db_name = MENU_DB_PATH
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_name)
        await self._init_database()

    async def close(self):
        await self.conn.close()

    async def _execute(self, query, params=(), fetchone=False, fetchall=False):
        async with self.conn.cursor() as cursor:
            await cursor.execute(query, params)
            await self.conn.commit()
            if fetchone:
                return await cursor.fetchone()
            if fetchall:
                return await cursor.fetchall()

    async def _init_database(self):
        await self._execute(
            """
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                price TEXT,
                description TEXT,
                volume TEXT,
                calories TEXT
            )
        """
        )
        await self._migrate_schema()

    async def _migrate_schema(self):
        cols = {
            row[1]
            for row in await self._execute("PRAGMA table_info(menu)", fetchall=True)
        }
        if "calories" not in cols:
            await self._execute("ALTER TABLE menu ADD COLUMN calories TEXT DEFAULT ''")

    async def add_item(
        self, category, name, price, description="", volume="", calories=""
    ):
        await self._execute(
            "INSERT INTO menu (category, name, price, description, volume, calories) VALUES (?, ?, ?, ?, ?, ?)",
            (category, name, price, description, volume, calories),
        )

    async def get_categories(self):
        return [
            r[0]
            for r in await self._execute(
                "SELECT DISTINCT category FROM menu", fetchall=True
            )
        ]

    async def get_items_by_category(self, category):
        return await self._execute(
            "SELECT id, name, price, description, volume, calories FROM menu WHERE category = ?",
            (category,),
            fetchall=True,
        )

    async def get_item_by_id(self, item_id):
        return await self._execute(
            "SELECT * FROM menu WHERE id = ?", (item_id,), fetchone=True
        )

    async def clear_menu(self):
        await self._execute("DELETE FROM menu")
        await self._execute("DELETE FROM sqlite_sequence WHERE name='menu'")


menu_db = MenuDatabase()
