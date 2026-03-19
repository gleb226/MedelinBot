import sqlite3
from typing import Iterable, List, Optional

from app.common.config import ADMINS_DB_PATH, ADMIN_IDS, LOCATIONS, LOCATION_ADMINS


class AdminDatabase:
    def __init__(self):
        self.db_name = ADMINS_DB_PATH
        self._init_database()
        self._seed_from_env()

    # ---------- internal helpers ----------
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
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT DEFAULT 'admin', -- admin | super | god
                receive_notifications INTEGER DEFAULT 1,
                added_by INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS admin_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                location_id TEXT,
                UNIQUE(user_id, location_id)
            )
        """
        )
        self._migrate_schema()

    def _migrate_schema(self):
        cols = {row[1] for row in self._execute("PRAGMA table_info(admins)", fetchall=True)}
        if "role" not in cols:
            self._execute("ALTER TABLE admins ADD COLUMN role TEXT DEFAULT 'admin'")
        if "receive_notifications" not in cols:
            self._execute("ALTER TABLE admins ADD COLUMN receive_notifications INTEGER DEFAULT 1")
        if "added_by" not in cols:
            self._execute("ALTER TABLE admins ADD COLUMN added_by INTEGER")

    def _seed_from_env(self):
        """
        Sync super-admins and location bindings from .env on startup.
        """
        env_admins = [int(aid) for aid in ADMIN_IDS if aid.isdigit()]
        for admin_id in env_admins:
            # super admins from env do NOT get notifications by default
            self._execute(
                "INSERT OR IGNORE INTO admins (user_id, role, receive_notifications, added_by) VALUES (?, 'super', 0, NULL)",
                (admin_id,),
            )
        for loc_id, admins in LOCATION_ADMINS.items():
            for admin_id in admins:
                if str(admin_id).isdigit():
                    self._execute(
                        "INSERT OR IGNORE INTO admin_locations (user_id, location_id) VALUES (?, ?)",
                        (int(admin_id), loc_id),
                    )

    # ---------- mutations ----------
    def add_admin(
        self,
        user_id: int,
        username: Optional[str],
        added_by: Optional[int],
        role: str = "admin",
        locations: Optional[Iterable[str]] = None,
        receive_notifications: Optional[bool] = None,
    ):
        role = role if role in ("admin", "super", "god") else "admin"
        if receive_notifications is None:
            receive_notifications = 0 if role == "super" else 1

        self._execute(
            "INSERT OR REPLACE INTO admins (user_id, username, role, receive_notifications, added_by) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, role, int(receive_notifications), added_by),
        )

        if locations is not None:
            self.set_locations(user_id, locations)

    def remove_admin(self, user_id: int):
        self._execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        self._execute("DELETE FROM admin_locations WHERE user_id = ?", (user_id,))

    def set_locations(self, user_id: int, locations: Iterable[str]):
        self._execute("DELETE FROM admin_locations WHERE user_id = ?", (user_id,))
        for loc in set(locations):
            if loc in LOCATIONS:
                self._execute(
                    "INSERT OR IGNORE INTO admin_locations (user_id, location_id) VALUES (?, ?)",
                    (user_id, loc),
                )

    def set_role(self, user_id: int, role: str, receive_notifications: Optional[bool] = None):
        if role not in ("admin", "super", "god"):
            return
        if receive_notifications is None:
            receive_notifications = 0 if role == "super" else 1
        self._execute(
            "UPDATE admins SET role = ?, receive_notifications = ? WHERE user_id = ?",
            (role, int(receive_notifications), user_id),
        )

    # ---------- queries ----------
    def get_all_admins(self) -> List[int]:
        """All admins (any role) that should have panel access."""
        db_admins = [r[0] for r in self._execute("SELECT user_id FROM admins", fetchall=True)]
        env_admins = [int(aid) for aid in ADMIN_IDS if aid.isdigit()]
        return list(set(db_admins + env_admins))

    def get_locations_for_admin(self, user_id: int) -> List[str]:
        rows = self._execute(
            "SELECT location_id FROM admin_locations WHERE user_id = ?",
            (user_id,),
            fetchall=True,
        )
        return [r[0] for r in rows]

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.get_all_admins()

    def is_super_admin(self, user_id: int) -> bool:
        row = self._execute(
            "SELECT role FROM admins WHERE user_id = ?",
            (user_id,),
            fetchone=True,
        )
        role = row[0] if row else None
        env_admins = [int(aid) for aid in ADMIN_IDS if aid.isdigit()]
        return role in ("super", "god") or user_id in env_admins

    def is_god(self, user_id: int) -> bool:
        row = self._execute(
            "SELECT role FROM admins WHERE user_id = ?",
            (user_id,),
            fetchone=True,
        )
        return bool(row and row[0] == "god")

    def has_location_access(self, user_id: int, location_id: str) -> bool:
        if self.is_super_admin(user_id):
            return True
        return location_id in self.get_locations_for_admin(user_id)

    def get_notification_targets(self, location_id: str) -> List[int]:
        """
        Admins who should receive booking notifications for a location:
        - admins assigned to that location with notifications enabled
        - god users (role == god) with notifications enabled
        - super admins only if receive_notifications = 1
        """
        rows = self._execute(
            """
            SELECT a.user_id
            FROM admins a
            LEFT JOIN admin_locations l ON a.user_id = l.user_id
            WHERE a.receive_notifications = 1
              AND (a.role = 'god' OR l.location_id = ? OR (a.role = 'super' AND l.location_id IS NULL))
            """,
            (location_id,),
            fetchall=True,
        )
        return list({r[0] for r in rows})


admin_db = AdminDatabase()
