from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards import user_keyboards as kb
from app.keyboards import admin_keyboards as akb
from app.common.config import LOCATIONS
from app.databases.menu_database import menu_db
from app.databases.user_database import user_db
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
from app.handlers.order_handlers import send_beans_invoice
from app.utils.logger import log_activity
from app.utils.time_utils import is_working_hours, get_closed_message
import datetime

user_router = Router()

class BookingStates(StatesGroup):
    choosing_location = State()
    choosing_date = State()
    choosing_time = State()
    choosing_people_count = State()
    entering_wishes = State()
    entering_phone = State()
    booking_summary = State()
    browsing_menu = State()

class CoffeeBeanStates(StatesGroup):
    choosing_beans = State()
    choosing_weight = State()
    choosing_location = State()
    entering_phone = State()

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await log_activity(message.from_user.id, message.from_user.username, "start")
    await user_db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    is_admin = await admin_db.is_admin(message.from_user.id)
    await message.answer(
        "☕️ <b>ВІТАЄМО В «MEDELIN»!</b>\n\nОберіть дію нижче 👇",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML",
    )

@user_router.message(F.text.in_([kb.BTN_BOOK_TABLE, "✨ ЗАБРОНЮВАТИ СТОЛИК"]))
async def process_booking(message: Message, state: FSMContext):
    if not is_working_hours():
        await message.answer(get_closed_message(), parse_mode="HTML"); return
    await state.clear()
    await state.update_data(booking_mode=True, fullname=message.from_user.full_name)
    await message.answer("📍 <b>ОБЕРІТЬ ЗАКЛАД ДЛЯ БРОНЮВАННЯ:</b>", reply_markup=kb.get_locations_kb(), parse_mode="HTML")
    await state.set_state(BookingStates.choosing_location)

@user_router.callback_query(F.data.startswith("loc_"), BookingStates.choosing_location)
async def booking_location_chosen(callback: CallbackQuery, state: FSMContext):
    loc_id = callback.data.split("_")[1]
    await state.update_data(location_id=loc_id)
    await callback.message.edit_text("🗓️ <b>ОБЕРІТЬ ДАТУ:</b>", reply_markup=kb.get_date_kb(), parse_mode="HTML")
    await state.set_state(BookingStates.choosing_date)

@user_router.callback_query(F.data.startswith("book_date_"), BookingStates.choosing_date)
async def booking_date_chosen(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.replace("book_date_", "")
    await state.update_data(booking_date=date_str)
    await callback.message.edit_text("🕒 <b>ОБЕРІТЬ ЧАС:</b>", reply_markup=kb.get_time_kb(), parse_mode="HTML")
    await state.set_state(BookingStates.choosing_time)

@user_router.callback_query(F.data.startswith("book_time_"), BookingStates.choosing_time)
async def booking_time_chosen(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.replace("book_time_", "")
    data = await state.get_data()
    full_date = f"{datetime.date.fromisoformat(data['booking_date']).strftime('%d.%m')} о {time_str}"
    await state.update_data(date_time=full_date)
    await callback.message.edit_text(
        f"🗓️ <b>ОБРАНО:</b> {full_date}\n\n👥 <b>КІЛЬКІСТЬ ГОСТЕЙ (1-20):</b>",
        parse_mode="HTML",
    )
    await state.set_state(BookingStates.choosing_people_count)

@user_router.message(BookingStates.choosing_people_count)
async def booking_people_count_entered(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit() or not (1 <= int(message.text) <= 20):
        await message.answer("❌ <b>ЧИСЛО ВІД 1 ДО 20.</b>", parse_mode="HTML"); return
    await state.update_data(people_count=message.text)
    await message.answer("💬 <b>ПОБАЖАННЯ АБО 'ні':</b>", parse_mode="HTML")
    await state.set_state(BookingStates.entering_wishes)

def _booking_summary_text(data: dict) -> str:
    loc_id = data.get("location_id")
    location_name = LOCATIONS.get(loc_id, {}).get("name", "—") if loc_id else "—"
    wishes = data.get("wishes") or ""
    wishes_line = wishes if wishes else "—"
    cart = data.get("cart", []) or []
    cart_line = ", ".join(cart).upper() if cart else "—"
    return f"""✅ <b>ПЕРЕВІРТЕ ДАНІ БРОНІ:</b>

🏛 <b>ЗАКЛАД:</b> {location_name}
🕒 <b>ЧАС:</b> {data.get('date_time') or '—'}
👥 <b>ГОСТЕЙ:</b> {data.get('people_count') or '—'}
💬 <b>ПОБАЖАННЯ:</b> {wishes_line}
🥘 <b>МЕНЮ:</b> {cart_line}

Оберіть дію нижче 👇"""

def _booking_summary_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ПІДТВЕРДИТИ БРОНЬ", callback_data="booking_confirm")],
        [InlineKeyboardButton(text="🍽 ДОДАТИ МЕНЮ + ОПЛАТИТИ", callback_data="booking_go_menu")],
        [InlineKeyboardButton(text="🏠 НА ГОЛОВНУ", callback_data="back_main_menu_only")],
    ])

async def _send_booking_summary(target, state: FSMContext):
    data = await state.get_data()
    text = _booking_summary_text(data)
    markup = _booking_summary_kb()
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=markup, parse_mode="HTML")
    await state.set_state(BookingStates.booking_summary)

async def _create_table_booking_and_notify(user, chat_id: int, state: FSMContext, bot: Bot):
    data = await state.get_data()
    loc_id = data.get("location_id")
    phone = data.get("phone")
    date_time = data.get("date_time")
    people_count = data.get("people_count")
    wishes = data.get("wishes") or ""

    if not loc_id or not phone or not date_time or not people_count:
        await state.clear()
        is_admin = await admin_db.is_admin(user.id)
        await bot.send_message(
            chat_id,
            "❌ <b>БРОНЮВАННЯ НЕ ВДАЛОСЯ.</b>\nСпробуйте ще раз з головного меню.",
            reply_markup=kb.get_main_menu(is_admin),
            parse_mode="HTML",
        )
        return

    booking_id = await booking_db.add_booking(
        user.id,
        user.username,
        user.full_name,
        phone,
        loc_id,
        date_time,
        str(people_count),
        wishes if wishes else "—",
        "СТОЛИК",
        "booking",
    )

    admin_text = f"""📅 <b>НОВЕ БРОНЮВАННЯ СТОЛИКА</b>

👤 <b>КЛІЄНТ:</b> {user.full_name}
📞 <b>ТЕЛЕФОН:</b> <code>{phone}</code>
🏛 <b>ЗАКЛАД:</b> {LOCATIONS[loc_id]['name']}
🕒 <b>ЧАС:</b> {date_time}
👥 <b>ГОСТЕЙ:</b> {people_count}
💬 <b>ПОБАЖАННЯ:</b> {wishes if wishes else "—"}"""

    for aid in await admin_db.get_notification_targets(loc_id):
        try:
            await bot.send_message(aid, admin_text, reply_markup=akb.get_booking_manage_kb(booking_id), parse_mode="HTML")
        except Exception:
            pass

    is_admin = await admin_db.is_admin(user.id)
    await bot.send_message(
        chat_id,
        "✅ <b>ЗАПИТ НА БРОНЮВАННЯ ВІДПРАВЛЕНО!</b>\nМи підтвердимо його найближчим часом.",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML",
    )
    await state.clear()

@user_router.message(BookingStates.entering_wishes)
async def booking_wishes_entered(message: Message, state: FSMContext, bot: Bot):
    wishes_raw = (message.text or "").strip()
    wishes = "" if wishes_raw.lower() in ("ні", "нет", "no", "-", "—") else wishes_raw
    await state.update_data(wishes=wishes)

    phone = await user_db.get_phone(message.from_user.id)
    if phone:
        await state.update_data(phone=phone)
        await _send_booking_summary(message, state)
        return

    await message.answer("☎️ <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН (+380...):</b>", parse_mode="HTML")
    await state.set_state(BookingStates.entering_phone)

@user_router.message(BookingStates.entering_phone)
async def booking_phone_entered(message: Message, state: FSMContext, bot: Bot):
    phone = (message.text or "").strip()
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10:
        await message.answer("❌ <b>НЕКОРЕКТНИЙ ТЕЛЕФОН.</b>\nСпробуйте ще раз у форматі +380...", parse_mode="HTML")
        return

    await state.update_data(phone=phone)
    await user_db.set_phone(message.from_user.id, phone)
    await _send_booking_summary(message, state)

@user_router.callback_query(F.data == "booking_confirm", BookingStates.booking_summary)
async def booking_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await _create_table_booking_and_notify(callback.from_user, callback.message.chat.id, state, bot)

@user_router.callback_query(F.data == "booking_go_menu", BookingStates.booking_summary)
async def booking_go_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(cart=[], booking_mode=True)
    categories = await menu_db.get_categories()
    await callback.message.edit_text(
        "🍽️ <b>ДОДАЙТЕ МЕНЮ ДО БРОНІ</b>\n\nОберіть категорію:",
        reply_markup=kb.get_categories_kb(categories, booking_mode=True, cart_count=0),
        parse_mode="HTML",
    )
    await state.set_state(BookingStates.browsing_menu)

@user_router.callback_query(F.data == "back_to_booking_summary")
async def booking_back_to_summary(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("booking_mode"):
        await callback.answer("Немає активної броні."); return
    await callback.answer()
    await _send_booking_summary(callback, state)

@user_router.message(F.text.in_([kb.BTN_MENU, "📜 МЕНЮ"]))
async def open_menu(message: Message, state: FSMContext):
    if not is_working_hours():
        await message.answer(get_closed_message(), parse_mode="HTML"); return
    await state.clear()
    await state.update_data(cart=[], booking_mode=False)
    categories = await menu_db.get_categories()
    await message.answer(
        "🍽️ <b>МЕНЮ</b>\n\nОберіть категорію:",
        reply_markup=kb.get_categories_kb(categories, cart_count=0),
        parse_mode="HTML",
    )
    await state.set_state(BookingStates.browsing_menu)

@user_router.callback_query(F.data.startswith("cat_"))
async def menu_category(callback: CallbackQuery, state: FSMContext):
    cat_id = callback.data.replace("cat_", "", 1)
    categories = await menu_db.get_categories()
    cat = next((c for c in categories if kb.cat_key(str(c)) == cat_id), None)
    if not cat:
        await callback.answer("Категорію не знайдено."); return
    await state.update_data(current_category=cat)
    data = await state.get_data()
    cart = data.get("cart", [])
    booking_mode = bool(data.get("booking_mode"))
    items = await menu_db.get_items_by_category(cat)
    await callback.message.edit_text(
        f"🍽️ <b>{cat}</b>\n\nОберіть позицію:",
        reply_markup=kb.get_items_kb(items, cat, cart_count=len(cart), booking_mode=booking_mode),
        parse_mode="HTML",
    )

@user_router.callback_query(F.data.startswith("item_"))
async def menu_item(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.replace("item_", "", 1)
    row = await menu_db.get_item_by_id(int(item_id))
    if not row:
        await callback.answer("Не знайдено."); return
    _, category, name, price, description, volume, calories = row
    parts = [f"🧾 <b>{name}</b>", f"💵 <b>Ціна:</b> {price}"]
    if volume: parts.append(f"📏 <b>Обʼєм:</b> {volume}")
    if calories: parts.append(f"🔥 <b>Калорійність:</b> {calories}")
    if description: parts.append(f"\n{description}")
    await callback.message.edit_text(
        "\n".join(parts),
        reply_markup=kb.get_item_actions_kb(int(item_id)),
        parse_mode="HTML",
    )

@user_router.callback_query(F.data.startswith("add_to_cart_"))
async def menu_add_to_cart(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.replace("add_to_cart_", "", 1)
    row = await menu_db.get_item_by_id(int(item_id))
    if not row:
        await callback.answer("Не знайдено."); return
    name = row[2]
    data = await state.get_data()
    cart = list(data.get("cart", []))
    cart.append(name)
    await state.update_data(cart=cart)
    await callback.answer("Додано в кошик.")

    cat = data.get("current_category") or row[1]
    booking_mode = bool(data.get("booking_mode"))
    items = await menu_db.get_items_by_category(cat)
    await callback.message.edit_text(
        f"🍽️ <b>{cat}</b>\n\nОберіть позицію:",
        reply_markup=kb.get_items_kb(items, cat, cart_count=len(cart), booking_mode=booking_mode),
        parse_mode="HTML",
    )

@user_router.callback_query(F.data == "back_cats")
async def menu_back_to_categories(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    booking_mode = bool(data.get("booking_mode"))
    categories = await menu_db.get_categories()
    await callback.message.edit_text(
        "🍽️ <b>МЕНЮ</b>\n\nОберіть категорію:",
        reply_markup=kb.get_categories_kb(categories, booking_mode=booking_mode, cart_count=len(cart)),
        parse_mode="HTML",
    )

@user_router.callback_query(F.data == "back_items")
async def menu_back_to_items(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    cat = data.get("current_category")
    booking_mode = bool(data.get("booking_mode"))
    if not cat:
        await menu_back_to_categories(callback, state); return
    items = await menu_db.get_items_by_category(cat)
    await callback.message.edit_text(
        f"🍽️ <b>{cat}</b>\n\nОберіть позицію:",
        reply_markup=kb.get_items_kb(items, cat, cart_count=len(cart), booking_mode=booking_mode),
        parse_mode="HTML",
    )

@user_router.message(F.text.in_([kb.BTN_LOCATIONS, "🏢 НАШІ ЗАКЛАДИ"]))
async def show_locations(message: Message, state: FSMContext):
    lines = ["📍 <b>НАШІ ЗАКЛАДИ</b>\n"]
    for loc in LOCATIONS.values():
        lines.append(f"🏬 <b>{loc['name']}</b>\n<code>{loc['address']}</code>\n")
    await message.answer("\n".join(lines).strip(), parse_mode="HTML")

@user_router.message(F.text.in_([kb.BTN_CONTACTS, "📞 КОНТАКТИ"]))
async def show_contacts(message: Message, state: FSMContext):
    await message.answer(
        "☎️ <b>КОНТАКТИ</b>\n\n📞 <code>+380503775906</code>\n✉️ <code>medelin.social@gmail.com</code>\n\nОберіть, куди перейти:",
        reply_markup=kb.get_contact_kb(),
        parse_mode="HTML",
    )

@user_router.callback_query(F.data == "contact_phone")
async def contact_phone(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("📞 <b>Телефон:</b> <code>+380503775906</code>", parse_mode="HTML")

@user_router.callback_query(F.data == "contact_email")
async def contact_email(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("✉️ <b>Email:</b> <code>medelin.social@gmail.com</code>", parse_mode="HTML")

@user_router.message(F.text == kb.BTN_BEANS)
async def beans_start(message: Message, state: FSMContext):
    if not is_working_hours():
        await message.answer(get_closed_message(), parse_mode="HTML"); return
    await state.clear()
    items = await menu_db.get_items_by_category("Кава в зернах")
    if not items:
        await message.answer("☕️ <b>Кава в зернах</b>\n\nПоки що немає позицій.", parse_mode="HTML")
        return
    await message.answer(
        "☕️ <b>КАВА В ЗЕРНАХ</b>\n\nОберіть сорт:",
        reply_markup=kb.get_beans_kb(items),
        parse_mode="HTML",
    )
    await state.set_state(CoffeeBeanStates.choosing_beans)

@user_router.callback_query(F.data.startswith("bean_"), CoffeeBeanStates.choosing_beans)
async def beans_chosen(callback: CallbackQuery, state: FSMContext):
    bean_id = callback.data.replace("bean_", "", 1)
    row = await menu_db.get_item_by_id(int(bean_id))
    if not row:
        await callback.answer("Не знайдено."); return
    await state.update_data(bean_name=row[2], base_price=row[3])
    await callback.message.edit_text(
        f"☕️ <b>{row[2]}</b>\n\nОберіть вагу:",
        reply_markup=kb.get_beans_weight_kb(),
        parse_mode="HTML",
    )
    await state.set_state(CoffeeBeanStates.choosing_weight)

@user_router.callback_query(F.data == "bean_back")
async def beans_back(callback: CallbackQuery, state: FSMContext):
    items = await menu_db.get_items_by_category("Кава в зернах")
    await callback.message.edit_text(
        "☕️ <b>КАВА В ЗЕРНАХ</b>\n\nОберіть сорт:",
        reply_markup=kb.get_beans_kb(items),
        parse_mode="HTML",
    )
    await state.set_state(CoffeeBeanStates.choosing_beans)

@user_router.callback_query(F.data.startswith("bean_w_"), CoffeeBeanStates.choosing_weight)
async def beans_weight(callback: CallbackQuery, state: FSMContext):
    weight = callback.data.replace("bean_w_", "", 1)
    await state.update_data(weight=weight)
    await callback.message.edit_text(
        "📍 <b>ОБЕРІТЬ ЗАКЛАД ДЛЯ САМОВИВОЗУ:</b>",
        reply_markup=kb.get_locations_kb(),
        parse_mode="HTML",
    )
    await state.set_state(CoffeeBeanStates.choosing_location)

@user_router.callback_query(F.data.startswith("loc_"), CoffeeBeanStates.choosing_location)
async def beans_location(callback: CallbackQuery, state: FSMContext, bot: Bot):
    loc_id = callback.data.split("_")[1]
    await state.update_data(location_id=loc_id)
    phone = await user_db.get_phone(callback.from_user.id)
    if phone:
        await state.update_data(phone=phone)
        await send_beans_invoice(callback.from_user, callback.message.chat.id, state, bot)
        return
    await callback.message.answer("☎️ <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН (+380...):</b>", parse_mode="HTML")
    await state.set_state(CoffeeBeanStates.entering_phone)

@user_router.message(CoffeeBeanStates.entering_phone)
async def beans_phone(message: Message, state: FSMContext, bot: Bot):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await user_db.set_phone(message.from_user.id, phone)
    await send_beans_invoice(message.from_user, message.chat.id, state, bot)

@user_router.callback_query(F.data == "back_main_menu_only")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = await admin_db.is_admin(callback.from_user.id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "☕️ <b>ГОЛОВНЕ МЕНЮ</b>",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML",
    )
