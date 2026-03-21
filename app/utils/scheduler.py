from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.databases.booking_database import booking_db
from app.utils.logger import log_activity

async def cleanup_old_data():
    try:
        query = "DELETE FROM bookings WHERE timestamp < datetime('now', '-6 months')"
        async with booking_db.conn.cursor() as cur:
            await cur.execute(query)
            await booking_db.conn.commit()
            deleted = cur.rowcount
            if deleted > 0:
                await log_activity(0, "system", "db_cleanup", f"Deleted {deleted} old records.")
    except Exception as e:
        await log_activity(0, "system", "db_cleanup_error", str(e))

def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cleanup_old_data, 'cron', hour=3, minute=0)
    scheduler.start()
