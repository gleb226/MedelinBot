import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.handlers.user_handlers import user_router
from app.handlers.admin_handlers import admin_router
from app.handlers.error_handler import error_router
from app.common.config import BOT_TOKEN
from app.databases.user_database import user_db
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
from app.databases.menu_database import menu_db
from app.utils.logger import logger

logging.basicConfig(level=logging.WARNING)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(user_router)
dp.include_router(admin_router)
dp.include_router(error_router)

async def on_startup():
    await user_db.connect()
    await booking_db.connect()
    await admin_db.connect()
    await menu_db.connect()
    await logger.connect()

async def on_shutdown():
    await user_db.close()
    await booking_db.close()
    await admin_db.close()
    await menu_db.close()
    await logger.close()

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
