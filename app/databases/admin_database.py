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
        if self.conn:
            await self.conn.close()

    async def _execute(self, query, params=(), fetchone=False, fetchall=False):
        # This is not safe if multiple coroutines are calling this on the same instance
        # without awaiting the result immediately.
        # But for this project, it seems to be the case.
        if not self.conn:
            # This should not happen if connect() is called on startup.
            # But as a fallback...
            async with aiosqlite.connect(self.db_name) as db:
                async with db.cursor() as cursor:
                    await cursor.execute(query, params)
                    if not query.strip().upper().startswith("SELECT"):
                        await db.commit()
                    if fetchone:
                        return await cursor.fetchone()
                    if fetchall:
                        return await cursor.fetchall()

        async with self.conn.cursor() as cursor:
            await cursor.execute(query, params)
            if not query.strip().upper().startswith("SELECT"):
                await self.conn.commit()
            
            if fetchone:
                return await cursor.fetchone()
            if fetchall:
                return await cursor.fetchall()

    async def _init_database(self):
        await self._execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT DEFAULT 'admin',
                added_by INTEGER,
                receive_notifications INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._execute("""
            CREATE TABLE IF NOT EXISTS admin_locations (
                user_id INTEGER,
                location_id TEXT,
                FOREIGN KEY(user_id) REFERENCES admins(user_id) ON DELETE CASCADE,
                PRIMARY KEY(user_id, location_id)
            )
        """)

    async def is_admin(self, user_id: int) -> bool:
        if str(user_id) in GOD_IDS:
            return True
        res = await self._execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        return bool(res)

    async def is_super_admin(self, user_id: int) -> bool:
        if str(user_id) in GOD_IDS:
            return True
        res = await self._execute("SELECT role FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        return res and res[0] in ('super', 'god')

    async def is_god(self, user_id: int) -> bool:
        if str(user_id) in GOD_IDS:
            return True
        res = await self._execute("SELECT role FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        return res and res[0] == 'god'

    async def get_locations_for_admin(self, user_id: int) -> list:
        rows = await self._execute("SELECT location_id FROM admin_locations WHERE user_id = ?", (user_id,), fetchall=True)
        return [r[0] for r in rows]

    async def add_admin(self, user_id: int, username: str, added_by: int, role: str = 'admin', receive_notifications: int = 1, locations: list = None):
        await self._execute("""
            INSERT INTO admins (user_id, username, role, added_by, receive_notifications)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                role=excluded.role,
                receive_notifications=excluded.receive_notifications
        """, (user_id, username, role, added_by, int(receive_notifications)))

        if locations is not None:
            await self._execute("DELETE FROM admin_locations WHERE user_id = ?", (user_id,))
            if locations:
                for loc in locations:
                    await self._execute("INSERT INTO admin_locations (user_id, location_id) VALUES (?, ?)", (user_id, loc))

    async def remove_admin(self, user_id: int):
        await self._execute("DELETE FROM admins WHERE user_id = ?", (user_id,))

    async def has_location_access(self, user_id: int, location_id: str) -> bool:
        if await self.is_super_admin(user_id):
            return True
        res = await self._execute("SELECT 1 FROM admin_locations WHERE user_id = ? AND location_id = ?", (user_id, location_id), fetchone=True)
        return bool(res)

    async def get_notification_targets(self, location_id: str) -> list:
        query = """
            SELECT DISTINCT a.user_id 
            FROM admins a
            LEFT JOIN admin_locations al ON a.user_id = al.user_id
            WHERE (al.location_id = ? OR a.role IN ('super', 'god')) AND a.receive_notifications = 1
        """
        rows = await self._execute(query, (location_id,), fetchall=True)
        targets = set([r[0] for r in rows])
        for gid in GOD_IDS:
            try:
                targets.add(int(gid))
            except:
                pass
        return list(targets)

admin_db = AdminDatabase()
