import aiosqlite
import traceback
from aiogram import Router, Bot
from aiogram.types import ErrorEvent
from app.common.config import ERRORS_DB_PATH, GOD_IDS

error_router = Router()

async def log_error_to_db(user_id, username, command, error_message, traceback_text):
    try:
        async with aiosqlite.connect(ERRORS_DB_PATH) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    command TEXT,
                    error_message TEXT,
                    traceback TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute(
                "INSERT INTO errors (user_id, username, command, error_message, traceback) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, command, error_message, traceback_text)
            )
            await conn.commit()
    except Exception as e:
        print(f"CRITICAL: Failed to log error to DB: {e}")

@error_router.error()
async def global_error_handler(event: ErrorEvent, bot: Bot):
    error = event.exception
    etype = type(error).__name__
    emsg = str(error)
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    
    user_id = None
    username = None
    command = "Unknown"
    
    if event.update.message:
        user_id = event.update.message.from_user.id
        username = event.update.message.from_user.username
        command = event.update.message.text
    elif event.update.callback_query:
        user_id = event.update.callback_query.from_user.id
        username = event.update.callback_query.from_user.username
        command = event.update.callback_query.data

    await log_error_to_db(user_id, username, command, f"{etype}: {emsg}", tb)
    
    error_text = "⚠️ Вибачте, виникла помилка. Ми вже працюємо над її виправленням!"
    
    try:
        if event.update.message:
            await event.update.message.answer(error_text)
        elif event.update.callback_query:
            await event.update.callback_query.message.answer(error_text)
    except:
        pass
        
    for god_id in GOD_IDS:
        try:
            await bot.send_message(god_id, f"🚨 **ERROR REPORT**\nUser: {user_id} (@{username})\nType: {etype}\nMsg: {emsg}")
        except:
            pass
