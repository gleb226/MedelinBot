import aiosqlite
from datetime import datetime

from app.common.config import USERS_DB_PATH
from app.utils.phone_utils import format_phone, normalize_phone


class UserDatabase:
    def __init__(self):
        self.db_name = USERS_DB_PATH
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_name)
        await self.conn.create_function("normalize_phone", 1, normalize_phone)
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
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                phone TEXT,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        await self._migrate_schema()

    async def _migrate_schema(self):
        cols = {
            row[1]
            for row in await self._execute(
                "PRAGMA table_info(users)", fetchall=True
            )
        }
        if "phone" not in cols:
            await self._execute("ALTER TABLE users ADD COLUMN phone TEXT")

    async def add_user(
        self, user_id: int, first_name: str, username: str, phone: str = None
    ):
        phone_value = format_phone(phone) if phone else None
        existing = await self._execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,), fetchone=True
        )
        if not existing:
            await self._execute(
                "INSERT INTO users (user_id, first_name, username, phone, joined_at) VALUES (?, ?, ?, ?, ?)",
                (
                    user_id,
                    first_name,
                    username,
                    phone_value,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
        else:
            await self._execute(
                "UPDATE users SET first_name = ?, username = ?, phone = COALESCE(?, phone) WHERE user_id = ?",
                (first_name, username, phone_value, user_id),
            )

    async def set_phone(self, user_id: int, phone: str):
        phone_value = format_phone(phone)
        await self._execute(
            "UPDATE users SET phone = ? WHERE user_id = ?", (phone_value, user_id)
        )

    async def get_phone(self, user_id: int):
        row = await self._execute(
            "SELECT phone FROM users WHERE user_id = ?", (user_id,), fetchone=True
        )
        return row[0] if row else None

    async def get_user_by_username(self, username: str):
        if not username:
            return None
        return await self._execute(
            "SELECT user_id, first_name, username, phone FROM users WHERE LOWER(username) = LOWER(?)",
            (username,),
            fetchone=True,
        )

    async def get_user_by_phone(self, phone: str):
        target = normalize_phone(phone)
        if not target:
            return None
        return await self._execute(
            "SELECT user_id, first_name, username, phone FROM users WHERE normalize_phone(phone) = ?",
            (target,),
            fetchone=True,
        )


user_db = UserDatabase()
