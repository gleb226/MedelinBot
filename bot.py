import asyncio
import logging
import sys
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.handlers.user_handlers import user_router
from app.handlers.admin_handlers import admin_router
from app.handlers.order_handlers import order_router
from app.handlers.error_handler import error_router
from app.common.config import BOT_TOKEN
from app.databases.user_database import user_db
from app.databases.orders_database import orders_db
from app.databases.active_bookings_database import active_bookings_db
from app.databases.active_orders_database import active_orders_db
from app.databases.admin_database import admin_db
from app.databases.menu_database import menu_db
from app.databases.sales_database import sales_db
from app.databases.location_database import location_db
from app.databases.socials_database import socials_db
from app.databases.mongo_client import close_client
from app.utils.data_cache import public_data_cache
from app.utils.logger import logger

import uvicorn
from api import app as web_app

logging.basicConfig(level=logging.WARNING)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(admin_router)
dp.include_router(user_router)
dp.include_router(order_router)
dp.include_router(error_router)

async def on_startup():
    await user_db.connect()
    await orders_db.connect()
    await active_bookings_db.connect()
    await active_orders_db.connect()
    await admin_db.connect()
    await menu_db.connect()
    await sales_db.connect()
    await location_db.connect()
    await socials_db.connect()
    await logger.connect()
    await public_data_cache.warm_all()
    from aiogram.types import BotCommand
    await bot.set_my_commands([BotCommand(command="start", description="Головне меню / Кошик")])
    from app.utils.scheduler import start_scheduler
    start_scheduler()

async def on_shutdown():
    await user_db.close()
    await orders_db.close()
    await admin_db.close()
    await menu_db.close()
    await sales_db.close()
    await location_db.close()
    await socials_db.close()
    await logger.close()
    await close_client()

async def start_bot():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    try:
        try: await bot.delete_webhook(drop_pending_updates=True)
        except TelegramNetworkError as e: logging.warning("Telegram network error on delete_webhook: %s", e)
        try: await dp.start_polling(bot)
        except TelegramNetworkError as e: logging.error("Telegram network error on polling: %s", e)
    finally:
        try: await bot.session.close()
        except: pass

async def start_api():
    config = uvicorn.Config(web_app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(
        start_bot(),
        start_api()
    )

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
