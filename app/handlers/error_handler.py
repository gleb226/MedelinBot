import sqlite3
from datetime import datetime
from functools import wraps
from app.common.config import ERRORS_DB_PATH

def log_error_to_db(user_id: int, username: str, firstname: str, lastname: str, command: str, error_message: str):
    with sqlite3.connect(ERRORS_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER, 
                username TEXT, 
                firstname TEXT, 
                lastname TEXT, 
                command TEXT, 
                error_message TEXT, 
                timestamp TEXT
            )"""
        )
        cursor.execute(
            "INSERT INTO errors (user_id, username, firstname, lastname, command, error_message, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                username,
                firstname,
                lastname,
                command,
                error_message,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
        )
        conn.commit()

def error_handler(command: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            try:
                return await func(event, *args, **kwargs)
            except Exception as e:
                # Обробка як для повідомлень, так і для колбеків
                user = event.from_user
                log_error_to_db(
                    user_id=user.id,
                    username=user.username if user.username else "N/A",
                    firstname=user.first_name if user.first_name else "N/A",
                    lastname=user.last_name if user.last_name else "N/A",
                    command=command,
                    error_message=str(e)
                )
                
                error_text = "Вибачте, виникла помилка при виконанні запиту. Адміністратор вже працює над цим."
                if hasattr(event, "message"): # CallbackQuery
                    await event.message.answer(error_text)
                else: # Message
                    await event.answer(error_text)
        return wrapper
    return decorator
