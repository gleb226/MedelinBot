import aiosqlite
from app.common.config import BOOKINGS_DB_PATH
from app.utils.phone_utils import normalize_phone

class BookingDatabase:
    def __init__(self):
        self.db_name = BOOKINGS_DB_PATH
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_name)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.create_function("normalize_phone", 1, normalize_phone)
        await self._init_database()

    async def close(self):
        if self.conn: await self.conn.close(); self.conn = None

    async def _ensure_conn(self):
        if not self.conn:
            self.conn = await aiosqlite.connect(self.db_name)
            self.conn.row_factory = aiosqlite.Row
            await self.conn.create_function("normalize_phone", 1, normalize_phone)
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
        await self._execute("CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, fullname TEXT, phone TEXT, location_id TEXT, date_time TEXT, people_count TEXT, wishes TEXT, cart TEXT, status TEXT DEFAULT 'new', order_type TEXT DEFAULT 'booking', table_number TEXT DEFAULT '', timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
        await self._migrate_schema()

    async def _migrate_schema(self):
        cols = {row[1] for row in await self._execute("PRAGMA table_info(bookings)", fetchall=True)}
        if "order_type" not in cols: await self._execute("ALTER TABLE bookings ADD COLUMN order_type TEXT DEFAULT 'booking'")
        if "table_number" not in cols: await self._execute("ALTER TABLE bookings ADD COLUMN table_number TEXT DEFAULT ''")

    async def add_booking(self, user_id, username, fullname, phone, location_id, date_time, people_count, wishes, cart, order_type="booking", table_number=""):
        await self._ensure_conn()
        async with self.conn.cursor() as cur:
            await cur.execute("INSERT INTO bookings (user_id, username, fullname, phone, location_id, date_time, people_count, wishes, cart, order_type, table_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (user_id, username, fullname, phone, location_id, date_time, people_count, wishes, cart, order_type, table_number))
            await self.conn.commit()
            return cur.lastrowid

    async def get_new_bookings(self):
        return await self._execute("SELECT * FROM bookings WHERE status = 'new' ORDER BY timestamp DESC", fetchall=True)

    async def get_new_bookings_by_locations(self, location_ids):
        if not location_ids: return []
        ps = ",".join(["?"] * len(location_ids))
        return await self._execute(f"SELECT * FROM bookings WHERE status = 'new' AND location_id IN ({ps}) ORDER BY timestamp DESC", tuple(location_ids), fetchall=True)

    async def update_status(self, booking_id, status):
        await self._execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))

    async def get_booking_by_id(self, booking_id):
        return await self._execute("SELECT * FROM bookings WHERE id = ?", (booking_id,), fetchone=True)

    async def get_user_by_phone(self, phone: str):
        t = normalize_phone(phone)
        if not t: return None
        return await self._execute("SELECT user_id, fullname, username, phone FROM bookings WHERE normalize_phone(phone) = ? ORDER BY timestamp DESC", (t,), fetchone=True)

booking_db = BookingDatabase()
