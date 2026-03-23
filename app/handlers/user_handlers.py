from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards import user_keyboards as kb
from app.keyboards import admin_keyboards as akb
from app.common.config import LOCATIONS, WORK_START_HOUR, WORK_END_HOUR
from app.databases.menu_database import menu_db, parse_gramovka_grams, strip_gramovka
from app.databases.user_database import user_db
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
from app.handlers.order_handlers import send_beans_invoice, send_order_invoice
from app.utils.logger import log_activity
from app.utils.time_utils import is_working_hours, get_closed_message
import datetime
from urllib.parse import quote_plus

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

@user_router.message(F.text == "🏠 НА ГОЛОВНУ")
async def process_back_to_main(message: Message, state: FSMContext):
    await state.clear()
    is_admin = await admin_db.is_admin(message.from_user.id)
    await message.answer(
        "☕️ <b>ГОЛОВНЕ МЕНЮ</b>",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML",
    )

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
    sel_date = datetime.date.fromisoformat(date_str)
    time_kb = kb.get_time_kb(sel_date)
    if not getattr(time_kb, "inline_keyboard", None):
        try:
            await callback.message.edit_text(
                "Немає доступного часу на обрану дату.\nОберіть іншу дату:",
                reply_markup=kb.get_date_kb(),
                parse_mode="HTML",
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await state.set_state(BookingStates.choosing_date)
        return
    try:
        await callback.message.edit_text(
            "🕒 <b>ОБЕРІТЬ ЧАС:</b>",
            reply_markup=time_kb,
            parse_mode="HTML",
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await state.set_state(BookingStates.choosing_time)

@user_router.callback_query(F.data.startswith("book_time_"), BookingStates.choosing_time)
async def booking_time_chosen(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.replace("book_time_", "")
    data = await state.get_data()
    try:
        sel_date = datetime.date.fromisoformat(data["booking_date"])
        h, m = [int(x) for x in time_str.split(":", 1)]
        sel_dt = datetime.datetime.combine(sel_date, datetime.time(hour=h, minute=m))
        end_hour_raw = int(WORK_END_HOUR)
        if end_hour_raw == 24:
            closing = datetime.datetime.combine(sel_date, datetime.time(hour=0, minute=0)) + datetime.timedelta(days=1)
        else:
            closing = datetime.datetime.combine(sel_date, datetime.time(hour=end_hour_raw, minute=0))
        latest = (closing - datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        if sel_dt > latest:
            await callback.answer("Останній доступний час — за 1 годину до закриття.", show_alert=True)
            return
        if sel_date == datetime.date.today() and sel_dt < datetime.datetime.now().replace(second=0, microsecond=0):
            await callback.answer("Неможливо обрати час у минулому.", show_alert=True)
            return
    except Exception:
        await callback.answer("Некоректний час.", show_alert=True)
        return
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
    pay_hint = "\n\nПісля підтвердження буде сформовано рахунок для оплати." if cart else ""
    return f"""✅ <b>ПЕРЕВІРТЕ ДАНІ БРОНІ:</b>

🏛 <b>ЗАКЛАД:</b> {location_name}
🕒 <b>ЧАС:</b> {data.get('date_time') or '—'}
👥 <b>ГОСТЕЙ:</b> {data.get('people_count') or '—'}
💬 <b>ПОБАЖАННЯ:</b> {wishes_line}
🥘 <b>МЕНЮ:</b> {cart_line}

Оберіть дію нижче 👇{pay_hint}"""

def _booking_summary_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✅ ПІДТВЕРДИТИ БРОНЬ", callback_data="booking_confirm")],
        [InlineKeyboardButton(text="🛍 ДОДАТИ ПОЗИЦІЇ", callback_data="booking_go_menu")],
    ]
    rows.append([InlineKeyboardButton(text="🏠 НА ГОЛОВНУ", callback_data="back_main_menu_only")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

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

    targets = await admin_db.get_notification_targets(loc_id)
    for aid in targets:
        try:
            await bot.send_message(aid, admin_text, reply_markup=akb.get_booking_manage_kb(booking_id), parse_mode="HTML")
            await booking_db.mark_admin_notified(booking_id, aid)
        except Exception:
            pass

    is_admin = await admin_db.is_admin(user.id)
    await bot.send_message(
        chat_id,
        (
            "✅ <b>ЗАПИТ НА БРОНЮВАННЯ ВІДПРАВЛЕНО!</b>\nМи підтвердимо його найближчим часом."
            if targets
            else "🕓 <b>ЗАПИТ НА БРОНЮВАННЯ ЗБЕРЕЖЕНО.</b>\n\nНаразі немає доступних адміністраторів на зміні. Спробуйте трохи пізніше або дочекайтесь — щойно адміністратор розпочне зміну, він отримає повідомлення."
        ),
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

    await message.answer(
        "☎️ <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН:</b>\n\nНатисніть кнопку нижче або введіть вручну (+380...):",
        reply_markup=kb.get_phone_kb(),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.entering_phone)

@user_router.message(BookingStates.entering_phone)
async def booking_phone_entered(message: Message, state: FSMContext, bot: Bot):
    if message.text == "🏠 НА ГОЛОВНУ":
        await back_to_main(message, state)
        return

    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = (message.text or "").strip()
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 10:
            await message.answer("❌ <b>НЕКОРЕКТНИЙ ТЕЛЕФОН.</b>\nСпробуйте ще раз у форматі +380...", parse_mode="HTML")
            return

    await state.update_data(phone=phone)
    await user_db.set_phone(message.from_user.id, phone)
    
    # Повертаємо головне меню, щоб прибрати клавіатуру з кнопкою телефону
    is_admin = await admin_db.is_admin(message.from_user.id)
    await message.answer("✅ Телефон збережено.", reply_markup=kb.get_main_menu(is_admin))
    await _send_booking_summary(message, state)

@user_router.callback_query(F.data == "booking_confirm", BookingStates.booking_summary)
async def booking_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    cart = data.get("cart", []) or []
    if cart:
        await callback.message.answer(
            "<b>ПІДТВЕРДЖЕННЯ БРОНЮВАННЯ</b>\n\n"
            "Для завершення оформлення потрібна оплата замовлення.\n"
            "Натисніть кнопку оплати в рахунку нижче.",
            parse_mode="HTML",
        )
        await send_order_invoice(callback.from_user, callback.message.chat.id, state, bot)
        return

    await _create_table_booking_and_notify(callback.from_user, callback.message.chat.id, state, bot)

@user_router.callback_query(F.data == "booking_go_menu", BookingStates.booking_summary)
async def booking_go_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(cart=[], booking_mode=True)
    categories = await menu_db.get_categories()
    await callback.message.edit_text(
        "🍽️ <b>МЕНЮ / ЗАМОВЛЕННЯ</b>\n\nДодайте позиції до броні. Оберіть категорію:",
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

@user_router.message(F.text.in_([kb.BTN_MENU, "📜 МЕНЮ", "🍽️ МЕНЮ", "ЗАМОВИТИ"]))
async def open_menu(message: Message, state: FSMContext):
    if not is_working_hours():
        await message.answer(get_closed_message(), parse_mode="HTML"); return
    await state.clear()
    await state.update_data(cart=[], booking_mode=False)
    categories = await menu_db.get_categories()
    await message.answer(
        "🍽️ <b>МЕНЮ / ЗАМОВЛЕННЯ</b>\n\nОберіть категорію:",
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
    row = await menu_db.get_item_by_id(item_id)
    if not row:
        await callback.answer("Не знайдено."); return
    _, category, name, price, description, volume, calories = row
    parts = [f"✨ <b>{name}</b>", f"💰 <b>Ціна:</b> {price}"]
    if volume: parts.append(f"⚖️ <b>Обʼєм:</b> {volume}")
    if calories:
        cal_val = str(calories).replace("ккал", "").strip()
        parts.append(f"🔋 <b>Енерг. цінність:</b> {cal_val} ккал")
    if description: parts.append(f"\n📜 <b>Склад:</b>\n{description}")
    await callback.message.edit_text(
        "\n".join(parts),
        reply_markup=kb.get_item_actions_kb(item_id),
        parse_mode="HTML",
    )

@user_router.callback_query(F.data.startswith("add_to_cart_"))
async def menu_add_to_cart(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    item_id = data[3]
    milk_type = data[4] if len(data) > 4 else None
    
    row = await menu_db.get_item_by_id(item_id)
    if not row:
        await callback.answer("Не знайдено."); return
    
    category = row[1]
    name = row[2]
    
    # If it's coffee and milk isn't selected yet, ask for milk
    if not milk_type and category in ("Кава", "Кава На Альтернативному", "Масала", "Какао"):
        await callback.message.edit_reply_markup(reply_markup=kb.get_milk_kb(item_id))
        return

    final_name = name
    if milk_type:
        milk_map = {"std": "звичайне", "coco": "кокосове", "soy": "соєве", "almond": "мигдалеве", "lacfree": "безлактозне"}
        final_name += f" ({milk_map.get(milk_type, milk_type)})"

    state_data = await state.get_data()
    cart = list(state_data.get("cart", []))
    cart.append(final_name)
    await state.update_data(cart=cart)
    await callback.answer(f"Додано: {final_name}")

    booking_mode = bool(state_data.get("booking_mode"))
    categories = await menu_db.get_categories()
    await callback.message.edit_text(
        "🍽️ <b>МЕНЮ / ЗАМОВЛЕННЯ</b>\n\nДодано в кошик. Оберіть категорію:",
        reply_markup=kb.get_categories_kb(categories, booking_mode=booking_mode, cart_count=len(cart)),
        parse_mode="HTML",
    )

@user_router.callback_query(F.data == "back_cats")
async def menu_back_to_categories(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    booking_mode = bool(data.get("booking_mode"))
    categories = await menu_db.get_categories()
    await callback.message.edit_text(
        "🍽️ <b>МЕНЮ / ЗАМОВЛЕННЯ</b>\n\nОберіть категорію:",
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
    keyboard = _locations_list_kb()
    await message.answer(
        "📍 <b>НАШІ ЗАКЛАДИ</b>\n\nОберіть заклад:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )

def _locations_list_kb() -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for loc_id, loc in LOCATIONS.items():
        row.append(InlineKeyboardButton(text=f"📍 {loc['name']}", callback_data=f"locinfo_{loc_id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🏠 НА ГОЛОВНУ", callback_data="back_main_menu_only")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@user_router.callback_query(F.data.startswith("locinfo_"))
async def location_info(callback: CallbackQuery):
    loc_id = callback.data.replace("locinfo_", "", 1)
    if loc_id == "back":
        await location_info_back(callback)
        return
    loc = LOCATIONS.get(loc_id)
    if not loc:
        await callback.answer("Заклад не знайдено."); return

    address = loc.get("address", "—")
    maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(address + ', Uzhhorod')}"

    text = f"""📍 <b>{loc['name']}</b>

📍 <b>Адреса:</b> <code>{address}</code>
⏰ <b>Години роботи:</b> {WORK_START_HOUR:02d}:00–{WORK_END_HOUR:02d}:00
📞 <b>Телефон:</b> <code>+380503775906</code>
✉️ <b>Email:</b> <code>medelin.social@gmail.com</code>
🪑 <b>Столиків (орієнтовно):</b> до {loc.get('max_tables', '—')}"""

    kb_info = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧭 ПОБУДУВАТИ МАРШРУТ", url=maps_url)],
        [InlineKeyboardButton(text="⬅️ ДО СПИСКУ", callback_data="locinfo_back"),
         InlineKeyboardButton(text="🏠 НА ГОЛОВНУ", callback_data="back_main_menu_only")],
    ])

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=kb_info, parse_mode="HTML")

@user_router.callback_query(F.data == "locinfo_back")
async def location_info_back(callback: CallbackQuery):
    await callback.answer()
    keyboard = _locations_list_kb()
    await callback.message.edit_text(
        "📍 <b>НАШІ ЗАКЛАДИ</b>\n\nОберіть заклад:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )

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
    
    text = (
        "☕️ <b>КАВА В ЗЕРНАХ «MEDELIN»</b>\n\n"
        "Свіжообсмажена кава для дому або офісу.\n"
        "👇 Оберіть сорт для замовлення:"
    )
    await message.answer(
        text,
        reply_markup=kb.get_beans_kb(items),
        parse_mode="HTML",
    )
    await state.set_state(CoffeeBeanStates.choosing_beans)

@user_router.callback_query(F.data.startswith("bean_"), CoffeeBeanStates.choosing_beans)
async def beans_chosen(callback: CallbackQuery, state: FSMContext):
    bean_id = callback.data.replace("bean_", "", 1)
    row = await menu_db.get_item_by_id(bean_id)
    if not row:
        await callback.answer("Не знайдено."); return
    
    _, category, raw_name, price, description, volume, calories = row
    clean_name, _ = strip_gramovka(raw_name)
    
    await state.update_data(bean_name=clean_name, base_price=price)
    
    text = f"☕️ <b>{clean_name}</b>"
    if description:
        text += f"\n\n📜 <b>Опис:</b>\n{description}"
    text += "\n\n⚖️ <b>Оберіть вагу:</b>"
    
    await callback.message.edit_text(
        text,
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
    await callback.message.answer(
        "☎️ <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН:</b>\n\nНатисніть кнопку нижче або введіть вручну (+380...):",
        reply_markup=kb.get_phone_kb(),
        parse_mode="HTML"
    )
    await state.set_state(CoffeeBeanStates.entering_phone)

@user_router.message(CoffeeBeanStates.entering_phone)
async def beans_phone(message: Message, state: FSMContext, bot: Bot):
    if message.text == "🏠 НА ГОЛОВНУ":
        await back_to_main(message, state)
        return

    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = (message.text or "").strip()
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 10:
            await message.answer("❌ <b>НЕКОРЕКТНИЙ ТЕЛЕФОН.</b>\nСпробуйте ще раз у форматі +380...", parse_mode="HTML")
            return
            
    await state.update_data(phone=phone)
    await user_db.set_phone(message.from_user.id, phone)
    
    # Повертаємо головне меню, щоб прибрати клавіатуру з кнопкою телефону
    is_admin = await admin_db.is_admin(message.from_user.id)
    await message.answer("✅ Телефон збережено.", reply_markup=kb.get_main_menu(is_admin))
    await send_beans_invoice(message.from_user, message.chat.id, state, bot)

@user_router.callback_query(F.data == "back_main_menu_only")
async def back_to_main_cb(callback: CallbackQuery, state: FSMContext):
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

async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    is_admin = await admin_db.is_admin(message.from_user.id)
    await message.answer(
        "☕️ <b>ГОЛОВНЕ МЕНЮ</b>",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML",
    )

