import aiosqlite
from app.common.config import ADMINS_DB_PATH, GOD_IDS

class AdminDatabase:
    def __init__(self):
        self.db_name = ADMINS_DB_PATH
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_name)
        await self.conn.execute("PRAGMA foreign_keys = ON;")
        await self._init_database()

    async def close(self):
        if self.conn: await self.conn.close(); self.conn = None

    async def _ensure_conn(self):
        if not self.conn:
            self.conn = await aiosqlite.connect(self.db_name)
            await self.conn.execute("PRAGMA foreign_keys = ON;")
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
        await self._execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, username TEXT, role TEXT DEFAULT 'admin', added_by INTEGER, receive_notifications INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        await self._execute("CREATE TABLE IF NOT EXISTS admin_locations (user_id INTEGER, location_id TEXT, FOREIGN KEY(user_id) REFERENCES admins(user_id) ON DELETE CASCADE, PRIMARY KEY(user_id, location_id))")
        await self._execute("CREATE TABLE IF NOT EXISTS shift_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES admins(user_id) ON DELETE CASCADE)")
        await self._migrate_schema()

    async def _migrate_schema(self):
        cols = {row[1] for row in await self._execute("PRAGMA table_info(admins)", fetchall=True)}
        if "is_on_shift" not in cols: await self._execute("ALTER TABLE admins ADD COLUMN is_on_shift INTEGER DEFAULT 0")

    async def set_shift_status(self, user_id: int, status: bool):
        await self._execute("UPDATE admins SET is_on_shift = ? WHERE user_id = ?", (int(status), user_id))
        await self.log_shift_action(user_id, "start" if status else "end")

    async def log_shift_action(self, user_id: int, action: str):
        admin = await self._execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        if not admin:
            role = "god" if str(user_id) in GOD_IDS else "super"
            await self._execute("INSERT INTO admins (user_id, username, role) VALUES (?, ?, ?)", (user_id, "SystemAutoAdded", role))
        await self._execute("INSERT INTO shift_logs (user_id, action) VALUES (?, ?)", (user_id, action))

    async def is_on_shift(self, user_id: int) -> bool:
        res = await self._execute("SELECT is_on_shift FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        return bool(res and res[0])

    async def is_admin(self, user_id: int) -> bool:
        if str(user_id) in GOD_IDS: return True
        res = await self._execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        return bool(res)

    async def is_super_admin(self, user_id: int) -> bool:
        if str(user_id) in GOD_IDS: return True
        res = await self._execute("SELECT role FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        return res and res[0] in ('super', 'god')

    async def is_god(self, user_id: int) -> bool:
        if str(user_id) in GOD_IDS: return True
        res = await self._execute("SELECT role FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        return res and res[0] == 'god'

    async def get_locations_for_admin(self, user_id: int) -> list:
        rows = await self._execute("SELECT location_id FROM admin_locations WHERE user_id = ?", (user_id,), fetchall=True)
        return [r[0] for r in rows]

    async def add_admin(self, user_id: int, username: str, added_by: int, role: str = 'admin', receive_notifications: int = 1, locations: list = None):
        await self._execute("INSERT INTO admins (user_id, username, role, added_by, receive_notifications) VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, role=excluded.role, receive_notifications=excluded.receive_notifications", (user_id, username, role, added_by, int(receive_notifications)))
        if locations is not None:
            await self._execute("DELETE FROM admin_locations WHERE user_id = ?", (user_id,))
            for loc in locations: await self._execute("INSERT INTO admin_locations (user_id, location_id) VALUES (?, ?)", (user_id, loc))

    async def remove_admin(self, user_id: int):
        await self._execute("DELETE FROM admins WHERE user_id = ?", (user_id,))

    async def has_location_access(self, user_id: int, location_id: str) -> bool:
        if await self.is_super_admin(user_id): return True
        res = await self._execute("SELECT 1 FROM admin_locations WHERE user_id = ? AND location_id = ?", (user_id, location_id), fetchone=True)
        return bool(res)

    async def get_notification_targets(self, location_id: str) -> list:
        query = "SELECT DISTINCT a.user_id FROM admins a JOIN admin_locations al ON a.user_id = al.user_id WHERE al.location_id = ? AND a.role = 'admin' AND a.receive_notifications = 1 AND a.is_on_shift = 1"
        rows = await self._execute(query, (location_id,), fetchall=True)
        return list(set([r[0] for r in rows]))

admin_db = AdminDatabase()
