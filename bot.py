import asyncio
from aiogram import Bot, Dispatcher
from app.handlers.user_handlers import user_router
from app.handlers.admin_handlers import admin_router
from app.common.config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(user_router)
dp.include_router(admin_router)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
