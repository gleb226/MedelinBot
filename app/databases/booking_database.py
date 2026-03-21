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
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                fullname TEXT,
                phone TEXT,
                location_id TEXT,
                date_time TEXT,
                people_count TEXT,
                wishes TEXT,
                cart TEXT,
                status TEXT DEFAULT 'new',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        await self._migrate_schema()

    async def _migrate_schema(self):
        cols = {
            row[1]
            for row in await self._execute(
                "PRAGMA table_info(bookings)", fetchall=True
            )
        }
        if "phone" not in cols:
            await self._execute(
                "ALTER TABLE bookings ADD COLUMN phone TEXT DEFAULT ''"
            )

    async def add_booking(
        self,
        user_id,
        username,
        fullname,
        phone,
        location_id,
        date_time,
        people_count,
        wishes,
        cart,
    ):
        async with self.conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO bookings (user_id, username, fullname, phone, location_id, date_time, people_count, wishes, cart) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    username,
                    fullname,
                    phone,
                    location_id,
                    date_time,
                    people_count,
                    wishes,
                    cart,
                ),
            )
            await self.conn.commit()
            return cur.lastrowid

    async def get_new_bookings(self):
        return await self._execute(
            "SELECT * FROM bookings WHERE status = 'new' ORDER BY timestamp DESC",
            fetchall=True,
        )

    async def get_new_bookings_by_locations(self, location_ids):
        if not location_ids:
            return []
        placeholders = ",".join(["?"] * len(location_ids))
        query = f"SELECT * FROM bookings WHERE status = 'new' AND location_id IN ({placeholders}) ORDER BY timestamp DESC"
        return await self._execute(query, tuple(location_ids), fetchall=True)

    async def get_all_bookings(self, limit=10):
        return await self._execute(
            "SELECT * FROM bookings ORDER BY timestamp DESC LIMIT ?",
            (limit,),
            fetchall=True,
        )

    async def update_status(self, booking_id, status):
        await self._execute(
            "UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id)
        )

    async def get_booking_by_id(self, booking_id):
        return await self._execute(
            "SELECT * FROM bookings WHERE id = ?", (booking_id,), fetchone=True
        )
    
    async def get_user_by_phone(self, phone: str):
        target = normalize_phone(phone)
        if not target:
            return None
        return await self._execute(
            "SELECT user_id, fullname, username, phone FROM bookings WHERE normalize_phone(phone) = ? ORDER BY timestamp DESC",
            (target,),
            fetchone=True,
        )


booking_db = BookingDatabase()
