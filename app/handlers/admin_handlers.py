from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards import admin_keyboards as akb
from app.keyboards import user_keyboards as kb
from app.common.config import LOCATIONS
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
from app.databases.user_database import user_db
from app.utils.phone_utils import normalize_phone
import re

admin_router = Router()

class AdminStates(StatesGroup):
    adding_admin_id = State()
    adding_admin_name = State()
    adding_admin_role = State()
    adding_admin_location = State()

async def get_user_role(user_id):
    if await admin_db.is_god(user_id): return "god"
    if await admin_db.is_super_admin(user_id): return "super"
    return "admin"

@admin_router.message(F.text.in_([kb.BTN_ADMIN, "🛰 АДМІН-ПАНЕЛЬ"]))
async def admin_panel_enter(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    role = await get_user_role(message.from_user.id)
    is_on_shift = await admin_db.is_on_shift(message.from_user.id)
    await message.answer(f"🔐 <b>ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>", reply_markup=akb.get_main_admin_menu(is_on_shift, role), parse_mode="HTML")

@admin_router.message(F.text == "🟢 ПОЧАТИ ЗМІНУ")
async def start_shift(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "admin": return
    await admin_db.set_shift_status(message.from_user.id, True)
    await message.answer("🟢 <b>ЗМІНУ РОЗПОЧАТО!</b>", reply_markup=akb.get_main_admin_menu(True, "admin"), parse_mode="HTML")

@admin_router.message(F.text == "🔴 ЗАВЕРШИТИ ЗМІНУ")
async def end_shift(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "admin": return
    await admin_db.set_shift_status(message.from_user.id, False)
    await message.answer("🔴 <b>ЗМІНУ ЗАВЕРШЕНО.</b>", reply_markup=akb.get_main_admin_menu(False, "admin"), parse_mode="HTML")

@admin_router.message(F.text == "📥 НОВІ ЗАПИТИ")
async def show_new_bookings(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    role = await get_user_role(message.from_user.id)
    if role in ("super", "god"): bookings = await booking_db.get_new_bookings()
    else:
        locations = await admin_db.get_locations_for_admin(message.from_user.id)
        bookings = await booking_db.get_new_bookings_by_locations(locations)
    if not bookings: await message.answer("📭 <b>Наразі немає нових запитів.</b>", parse_mode="HTML"); return
    for b in bookings:
        t = f"📥 <b>НОВИЙ ЗАПИТ</b>\n\n👤 <b>Клієнт:</b> {b['fullname']}\n📞 <code>{b['phone']}</code>\n🏛 <b>Заклад:</b> {LOCATIONS[b['location_id']]['name']}\n🕔 <b>Час:</b> {b['date_time']}\n👥 <b>Гостей:</b> {b['people_count']}\n🥘 <b>Замовлення:</b> {b['cart']}"
        await message.answer(t, reply_markup=akb.get_booking_manage_kb(b['id']), parse_mode="HTML")

@admin_router.message(F.text == "👥 КОМАНДА ТА ПРАВА")
async def manage_admins(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    role = await get_user_role(message.from_user.id)
    await message.answer("👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>", reply_markup=akb.get_admin_management_kb(role in ("super", "god")), parse_mode="HTML")

@admin_router.message(F.text == "🏠 ПОВЕРНУТИСЬ ДО ГОЛОВНОЇ")
async def back_to_main_from_admin(message: Message, state: FSMContext):
    from app.handlers.user_handlers import cmd_start
    await cmd_start(message, state)

@admin_router.callback_query(F.data.startswith("adm_confirm_"))
async def confirm_booking(callback: CallbackQuery, bot: Bot):
    bid = callback.data.split("_")[2]; b = await booking_db.get_booking_by_id(bid)
    await booking_db.update_status(bid, "confirmed")
    try: await bot.send_message(b["user_id"], "✅ <b>ВАШЕ ЗАМОВЛЕННЯ ПІДТВЕРДЖЕНО!</b>\nЧекаємо на вас.", parse_mode="HTML")
    except: pass
    await callback.message.edit_text(callback.message.text + "\n\n✅ <b>ПІДТВЕРДЖЕНО</b>", parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_cancel_"))
async def cancel_booking(callback: CallbackQuery, bot: Bot):
    bid = callback.data.split("_")[2]; b = await booking_db.get_booking_by_id(bid)
    await booking_db.update_status(bid, "cancelled")
    refund_msg = ""
    pay_id = b["payment_id"] if "payment_id" in b.keys() else None
    if pay_id:
        refund_msg = f"\n\n⚠️ <b>УВАГА: ЗАМОВЛЕННЯ БУЛО ОПЛАЧЕНО!</b>\nID транзакції: <code>{pay_id}</code>\nБудь ласка, здійсніть повернення коштів у кабінеті платіжної системи."
        try: await bot.send_message(b["user_id"], "❌ <b>ЗАМОВЛЕННЯ ВІДХИЛЕНО.</b>\nМи ініціювали повернення коштів. Вони надійдуть на ваш рахунок найближчим часом.", parse_mode="HTML")
        except: pass
    else:
        try: await bot.send_message(b["user_id"], "❌ <b>ЗАМОВЛЕННЯ ВІДХИЛЕНО.</b>", parse_mode="HTML")
        except: pass
    await callback.message.edit_text(callback.message.text + f"\n\n❌ <b>ВІДХИЛЕНО</b>{refund_msg}", parse_mode="HTML")

