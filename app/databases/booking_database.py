import sqlite3
from app.common.config import BOOKINGS_DB_PATH

class BookingDatabase:
    def __init__(self):
        self.db_name = BOOKINGS_DB_PATH
        self._init_database()

    def _execute(self, query, params=(), fetchone=False, fetchall=False):
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()

    def _init_database(self):
        self._execute(
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
        self._migrate_schema()

    def _migrate_schema(self):
        cols = {row[1] for row in self._execute("PRAGMA table_info(bookings)", fetchall=True)}
        if "phone" not in cols:
            self._execute("ALTER TABLE bookings ADD COLUMN phone TEXT DEFAULT ''")

    def add_booking(self, user_id, username, fullname, phone, location_id, date_time, people_count, wishes, cart):
        with sqlite3.connect(self.db_name) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO bookings (user_id, username, fullname, phone, location_id, date_time, people_count, wishes, cart) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, fullname, phone, location_id, date_time, people_count, wishes, cart)
            )
            booking_id = cur.lastrowid
            if not booking_id:
                booking_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            return booking_id

    def get_new_bookings(self):
        return self._execute("SELECT * FROM bookings WHERE status = 'new' ORDER BY timestamp DESC", fetchall=True)

    def get_new_bookings_by_locations(self, location_ids):
        if not location_ids:
            return []
        placeholders = ",".join(["?"] * len(location_ids))
        query = f"SELECT * FROM bookings WHERE status = 'new' AND location_id IN ({placeholders}) ORDER BY timestamp DESC"
        return self._execute(query, tuple(location_ids), fetchall=True)

    def get_all_bookings(self, limit=10):
        return self._execute("SELECT * FROM bookings ORDER BY timestamp DESC LIMIT ?", (limit,), fetchall=True)

    def update_status(self, booking_id, status):
        self._execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))

    def get_booking_by_id(self, booking_id):
        return self._execute("SELECT * FROM bookings WHERE id = ?", (booking_id,), fetchone=True)

booking_db = BookingDatabase()
