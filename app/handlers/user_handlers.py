from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from app.keyboards import user_keyboards as kb
from app.databases.admin_database import admin_db
from app.databases.user_database import user_db
from app.utils.logger import log_activity

user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await log_activity(message.from_user.id, message.from_user.username, "start")
    await user_db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    is_admin = await admin_db.is_admin(message.from_user.id)
    
    if is_admin:
        await message.answer("☕️ <b>ПАНЕЛЬ АДМІНІСТРАТОРА MEDELIN</b>", reply_markup=kb.get_main_menu(is_admin), parse_mode="HTML")
    else:
        await message.answer("☕️ <b>ВІТАЄМО В «MEDELIN»!</b>\n\nЦей бот зараз використовується виключно для адміністрування мережі кав'ярень.\n\nБудь ласка, оформлюйте свої замовлення та бронюйте столики безпосередньо на нашому офіційному сайті: <a href='https://medelin.ua'>medelin.ua</a>\n\n<i>Якщо у вас є питання, просто напишіть його сюди, і ми відповімо!</i>", reply_markup=kb.get_main_menu(is_admin), parse_mode="HTML")

@user_router.message(F.text == "🏠 НА ГОЛОВНУ")
async def process_back_to_main(message: Message, state: FSMContext):
    await state.clear()
    is_admin = await admin_db.is_admin(message.from_user.id)
    if is_admin:
        await message.answer("☕️ <b>ПАНЕЛЬ АДМІНІСТРАТОРА MEDELIN</b>", reply_markup=kb.get_main_menu(is_admin), parse_mode="HTML")

@user_router.message(~F.text.startswith("/"))
async def forward_to_admin(message: Message, bot: Bot):
    if await admin_db.is_admin(message.from_user.id):
        return
    
    text = f"📩 <b>ПОВІДОМЛЕННЯ ВІД ГОСТЯ</b>\n\n👤 {message.from_user.full_name} (@{message.from_user.username or 'без юзернейма'}):\n<i>{message.text}</i>"
    from app.common.config import BOSS_IDS
    kb_reply = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 ВІДПОВІСТИ", callback_data=f"adm_msg_{message.from_user.id}_none")]
    ])
    for boss_id in BOSS_IDS:
        if str(boss_id).strip():
            try:
                await bot.send_message(int(str(boss_id).strip()), text, parse_mode="HTML", reply_markup=kb_reply)
            except Exception:
                pass
    await message.answer("✅ Ваше повідомлення надіслано адміністрації.")
