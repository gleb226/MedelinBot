import aiosqlite
from app.common.config import SALES_DB_PATH
from datetime import datetime

class SalesDatabase:
    def __init__(self):
        self.db_name = SALES_DB_PATH
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_name)
        await self._init_database()

    async def close(self):
        if self.conn: await self.conn.close(); self.conn = None

    async def _ensure_conn(self):
        if not self.conn:
            self.conn = await aiosqlite.connect(self.db_name)
            await self._init_database()

    async def _execute(self, query, params=(), fetchone=False, fetchall=False):
        await self._ensure_conn()
        async with self.conn.cursor() as cursor:
            await cursor.execute(query, params)
            if not query.strip().upper().startswith("SELECT"):
                await self.conn.commit()
            if fetchone: return await cursor.fetchone()
            if fetchall: return await cursor.fetchall()

    async def _init_database(self):
        await self._execute("CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT NOT NULL, price INTEGER NOT NULL, quantity INTEGER DEFAULT 1, item_type TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
        await self._execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, currency TEXT, payload TEXT, telegram_payment_charge_id TEXT, provider_payment_charge_id TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")

    async def record_sale(self, user_id: int, item_name: str, price: int, quantity: int = 1, item_type: str = "menu_item"):
        await self._execute("INSERT INTO sales (user_id, item_name, price, quantity, item_type, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (user_id, item_name, price, quantity, item_type, datetime.now().isoformat()))

    async def record_payment(self, user_id: int, amount: int, currency: str, payload: str, telegram_id: str, provider_id: str):
        await self._execute("INSERT INTO payments (user_id, amount, currency, payload, telegram_payment_charge_id, provider_payment_charge_id) VALUES (?, ?, ?, ?, ?, ?)", (user_id, amount, currency, payload, telegram_id, provider_id))

    async def get_user_sales(self, user_id: int):
        return await self._execute("SELECT * FROM sales WHERE user_id = ? ORDER BY timestamp DESC", (user_id,), fetchall=True)

    async def get_all_sales(self):
        return await self._execute("SELECT * FROM sales ORDER BY timestamp DESC", fetchall=True)

sales_db = SalesDatabase()
