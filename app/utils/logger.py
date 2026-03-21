import aiosqlite
from datetime import datetime
from app.common.config import LOGS_DB_PATH

class Logger:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute(
            """CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER, 
                username TEXT, 
                action TEXT, 
                details TEXT,
                timestamp TEXT
            )"""
        )
        await self.conn.commit()

    async def close(self):
        await self.conn.close()

    async def log_activity(self, user_id: int, username: str, action: str, details: str = ""):
        await self.conn.execute(
            "INSERT INTO activity_logs (user_id, username, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                username,
                action,
                details,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
        )
        await self.conn.commit()

logger = Logger(LOGS_DB_PATH)

async def log_activity(user_id: int, username: str, action: str, details: str = ""):
    await logger.log_activity(user_id, username, action, details)

