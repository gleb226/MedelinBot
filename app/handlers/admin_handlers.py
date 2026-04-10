from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards import admin_keyboards as akb
from app.keyboards import user_keyboards as kb
from app.common.config import BOSS_IDS
from app.databases.orders_database import orders_db
from app.databases.active_bookings_database import active_bookings_db
from app.databases.active_orders_database import active_orders_db
from app.databases.admin_database import admin_db
from app.databases.user_database import user_db
from app.databases.menu_database import menu_db
from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.location_database import location_db
from app.databases.socials_database import socials_db
from app.databases.guest_messages_database import guest_messages_db
from app.utils.phone_utils import normalize_phone
from app.utils.data_cache import public_data_cache
from app.utils.payment_refunds import refund_telegram_payment
from app.utils.message_utils import safe_edit_message
import re, time
from aiogram.filters import CommandStart

admin_router = Router()

@admin_router.message(CommandStart())
async def admin_start_cmd(message: Message, state: FSMContext):
    await state.clear()
    from app.handlers.user_handlers import cmd_start
    await cmd_start(message, state)

@admin_router.message(F.text.startswith("/"))
async def other_commands_admin(message: Message, state: FSMContext):
    await state.clear()

class AdminStates(StatesGroup):
    adding_admin_id = State()
    adding_admin_name = State()
    adding_admin_role = State()
    adding_admin_location = State()
    adding_admin_confirm = State()
    messaging_guest = State()

class MenuStates(StatesGroup):
    waiting_category = State()
    waiting_new_category = State()
    waiting_name = State()
    waiting_price = State()
    waiting_price_250 = State()
    waiting_price_500 = State()
    waiting_price_1000 = State()
    waiting_desc = State()
    waiting_volume = State()
    waiting_calories = State()
    waiting_image = State()
    waiting_confirm = State()
    edit_select_item = State()
    edit_waiting_field = State()
    edit_waiting_value = State()

class BeanStates(StatesGroup):
    waiting_name = State()
    waiting_price_250 = State()
    waiting_desc = State()
    waiting_sort = State()
    waiting_taste = State()
    waiting_roast = State()
    waiting_country = State()
    waiting_altitude = State()
    waiting_processing = State()
    waiting_acidity = State()
    waiting_bitterness = State()
    waiting_body = State()
    waiting_image = State()
    waiting_confirm = State()
    edit_select = State()
    edit_field = State()
    edit_value = State()

class LocationStates(StatesGroup):
    waiting_name = State()
    waiting_address = State()
    waiting_schedule = State()
    waiting_phone = State()
    waiting_email = State()
    waiting_maps_url = State()
    waiting_atmosphere = State()
    waiting_amenities = State()
    waiting_image = State()
    waiting_max_tables = State()
    waiting_confirm = State()
    edit_select = State()
    edit_field = State()
    edit_value = State()

class SocialStates(StatesGroup):
    waiting_name = State()
    waiting_url = State()
    edit_select = State()
    edit_field = State()
    edit_value = State()

def extract_coords_from_maps(url: str) -> tuple[float, float] | None:
    if not url: return None
    match1 = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if match1: return float(match1.group(1)), float(match1.group(2))
    match2 = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
    if match2: return float(match2.group(1)), float(match2.group(2))
    match3 = re.search(r"q=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if match3: return float(match3.group(1)), float(match3.group(2))
    return None

async def get_user_role(user_id):
    if await admin_db.is_boss(user_id): return "boss"
    if await admin_db.is_super_admin(user_id): return "super"
    return "admin"

async def restart_fsm_on_command(message: Message, state: FSMContext) -> bool:
    text = (message.text or "").strip()
    if not text.startswith("/"): return False
    await state.clear()
    if text.split()[0].lower() == "/start":
        from app.handlers.user_handlers import cmd_start
        await cmd_start(message, state)
    return True

async def deliver_guest_message(bot: Bot, order: dict | None, text_html: str, site_text: str, reply_callback_data: str | None = None) -> str:
    if not order: return "missing_order"
    telegram_target = None
    if order.get("user_id"):
        try: telegram_target = int(order["user_id"])
        except Exception: telegram_target = None
    if telegram_target is None and order.get("username"):
        tg_username = str(order.get("username") or "").lstrip("@").strip()
        found_user = await user_db.get_user_by_username(tg_username) if tg_username else None
        if found_user: telegram_target = int(found_user[0])
    if telegram_target is not None:
        reply_markup = None
        if reply_callback_data:
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 ВІДПОВІСТИ", callback_data=reply_callback_data)]
            ])
        try:
            await bot.send_message(telegram_target, text_html, parse_mode="HTML", reply_markup=reply_markup)
            return "telegram"
        except Exception: pass
    await guest_messages_db.add_message(order_id=order.get("id"), phone=order.get("phone"), source="admin", text=site_text)
    return "site"

@admin_router.message(F.text == "↩️ НА ГОЛОВНУ")
async def back_to_main_from_admin(message: Message, state: FSMContext):
    await state.clear()
    is_admin = await admin_db.is_admin(message.from_user.id)
    if is_admin:
        role = await get_user_role(message.from_user.id)
        is_on_shift = await admin_db.is_on_shift(message.from_user.id)
        await message.answer(f"🔐 <b>АДМІН-ПАНЕЛЬ</b>\nРоль: <b>{role.upper()}</b>", reply_markup=akb.get_main_admin_menu(is_on_shift, role), parse_mode="HTML")
    else:
        from app.handlers.user_handlers import cmd_start
        await cmd_start(message, state)

@admin_router.message(F.text.in_([kb.BTN_ADMIN, "🔐 АДМІН-ПАНЕЛЬ", "🛰 АДМІН-ПАНЕЛЬ"]))
async def admin_panel_enter(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await state.clear()
    role = await get_user_role(message.from_user.id)
    is_on_shift = await admin_db.is_on_shift(message.from_user.id)
    await message.answer(f"🔐 <b>ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>", reply_markup=akb.get_main_admin_menu(is_on_shift, role), parse_mode="HTML")

@admin_router.message(F.text == "🟢 ПОЧАТИ ЗМІНУ")
async def start_shift(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "admin": return
    await state.clear()
    await admin_db.set_shift_status(message.from_user.id, True)
    await message.answer("🟢 <b>ЗМІНУ РОЗПОЧАТО!</b>", reply_markup=akb.get_main_admin_menu(True, "admin"), parse_mode="HTML")

@admin_router.message(F.text == "🔴 ЗАВЕРШИТИ ЗМІНУ")
async def end_shift(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "admin": return
    await state.clear()
    await admin_db.set_shift_status(message.from_user.id, False)
    await message.answer("🔴 <b>ЗМІНУ ЗАВЕРШЕНО.</b>", reply_markup=akb.get_main_admin_menu(False, "admin"), parse_mode="HTML")

@admin_router.message(F.text == "🆕 НОВІ ЗАПИТИ")
async def show_new_bookings(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await state.clear()
    role = await get_user_role(message.from_user.id)
    bookings = await orders_db.get_new_orders() if role in ("super", "boss") else await orders_db.get_new_orders_by_locations(await admin_db.get_locations_for_admin(message.from_user.id))
    if not bookings:
        await message.answer("📭 <b>Наразі немає нових запитів.</b>", parse_mode="HTML")
        return
    locations_dict = await location_db.get_locations_dict()
    for b in bookings:
        loc_name = locations_dict.get(b['location_id'], {}).get('name', '—')
        t = f"📥 <b>НОВИЙ ЗАПИТ</b>\n\n👤 <b>Клієнт:</b> {b['fullname']}\n📞 <code>{b['phone']}</code>\n🏛 <b>Заклад:</b> {loc_name}\n🕔 <b>Час:</b> {b['date_time']}\n👥 <b>Гостей:</b> {b['people_count']}\n🥘 <b>Замовлення:</b> {b['cart']}"
        await message.answer(t, reply_markup=akb.get_booking_manage_kb(b['id'], b.get('user_id')), parse_mode="HTML")

@admin_router.message(F.text == "⚡️ АКТИВНІ")
async def show_active_panel(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await message.answer("⚡️ <b>АКТИВНІ ЗАПИСИ</b>\nОберіть розділ:", reply_markup=akb.get_active_types_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "active_panel")
async def show_active_panel_cb(callback: CallbackQuery):
    await safe_edit_message(callback.message, "⚡️ <b>АКТИВНІ ЗАПИСИ</b>\nОберіть розділ:", reply_markup=akb.get_active_types_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "active_bookings")
async def list_active_bookings(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    locs = None if role in ("super", "boss") else await admin_db.get_locations_for_admin(callback.from_user.id)
    bookings = await active_bookings_db.get_active_bookings(locs)
    if not bookings:
        await callback.answer("Немає активних броней.")
        return
    await safe_edit_message(callback.message, "📅 <b>АКТИВНІ БРОНІ:</b>\nНатисніть для завершення:", reply_markup=akb.get_active_bookings_list_kb(bookings), parse_mode="HTML")

@admin_router.callback_query(F.data == "active_orders")
async def list_active_orders(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    locs = None if role in ("super", "boss") else await admin_db.get_locations_for_admin(callback.from_user.id)
    orders = await active_orders_db.get_active_orders(locs)
    if not orders:
        await callback.answer("Немає активних замовлень.")
        return
    await safe_edit_message(callback.message, "🛍 <b>АКТИВНІ ЗАМОВЛЕННЯ:</b>\nНатисніть для завершення:", reply_markup=akb.get_active_orders_list_kb(orders), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("finish_book_"))
async def finish_booking(callback: CallbackQuery):
    bid = callback.data.replace("finish_book_", "")
    await active_bookings_db.remove_booking(bid)
    await callback.answer("Бронь завершена!")
    await list_active_bookings(callback)

@admin_router.callback_query(F.data.startswith("finish_order_"))
async def finish_order(callback: CallbackQuery):
    oid = callback.data.replace("finish_order_", "")
    await active_orders_db.remove_order(oid)
    await callback.answer("Замовлення виконано!")
    await list_active_orders(callback)

@admin_router.message(F.text == "📋 МЕНЮ")
async def show_menu_panel(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "boss": return
    await state.clear()
    await message.answer("📋 <b>КЕРУВАННЯ МЕНЮ</b>", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.message(F.text == "☕ ЗЕРНО")
async def show_beans_panel(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "boss": return
    await state.clear()
    await message.answer("☕ <b>КЕРУВАННЯ ЗЕРНОМ</b>", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")

@admin_router.message(F.text == "📍 ЛОКАЦІЇ")
async def show_locs_panel(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "boss": return
    await state.clear()
    await message.answer("📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ</b>", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

@admin_router.message(F.text == "📱 СОЦМЕРЕЖІ")
async def show_socs_panel(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "boss": return
    await state.clear()
    await message.answer("📱 <b>КЕРУВАННЯ СОЦМЕРЕЖАМИ</b>", reply_markup=akb.get_socials_manage_kb(), parse_mode="HTML")

@admin_router.message(F.text == "👥 КОМАНДА")
async def show_team_panel(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await state.clear()
    is_super = await admin_db.is_super_admin(message.from_user.id) or await admin_db.is_boss(message.from_user.id)
    await message.answer("👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>", reply_markup=akb.get_admin_management_kb(is_super), parse_mode="HTML")

@admin_router.callback_query(F.data == "admin_panel_back")
async def admin_panel_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    role = await get_user_role(callback.from_user.id)
    is_on_shift = await admin_db.is_on_shift(callback.from_user.id)
    try: await callback.message.delete()
    except Exception: pass
    await callback.message.answer(f"🔐 <b>ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>", reply_markup=akb.get_main_admin_menu(is_on_shift, role), parse_mode="HTML")

@admin_router.callback_query(F.data == "beans_back")
async def back_to_beans_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_message(callback.message, "☕ <b>КЕРУВАННЯ ЗЕРНОМ</b>", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "locs_back")
async def back_to_locs_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit_message(callback.message, "📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ</b>", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "beans_list")
async def list_beans(callback: CallbackQuery):
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer("Порожньо.")
        return
    text = "☕ <b>ЗЕРНО В НАЯВНОСТІ:</b>\n\n" + "\n".join([f"▫️ {b['name']} ({b['price_250']}₴)" for b in beans])
    await safe_edit_message(callback.message, text, reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "beans_del")
async def del_beans_start(callback: CallbackQuery):
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer("Порожньо.")
        return
    await safe_edit_message(callback.message, "🗑 Оберіть зерно для ВИДАЛЕННЯ:", reply_markup=akb.get_beans_list_kb(beans, "beans_del_it"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("beans_del_it_"))
async def del_bean_confirm(callback: CallbackQuery):
    bid = callback.data.replace("beans_del_it_", "")
    await coffee_beans_db.delete_bean(bid)
    await public_data_cache.refresh("coffee")
    await callback.answer("Видалено!")
    await del_beans_start(callback)

@admin_router.callback_query(F.data == "beans_add")
async def add_bean_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BeanStates.waiting_name)
    await callback.message.answer("✏️ Назва зерна:")
    await callback.answer()

@admin_router.message(BeanStates.waiting_name)
async def add_bean_name(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(name=message.text)
    await message.answer("💰 Ціна за 250г:")
    await state.set_state(BeanStates.waiting_price_250)

@admin_router.message(BeanStates.waiting_price_250)
async def add_bean_price(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    try:
        val = float(message.text.replace(",", ".").strip())
        await state.update_data(price_250=val)
        await message.answer("📝 Опис:")
        await state.set_state(BeanStates.waiting_desc)
    except ValueError:
        await message.answer("❌ Введіть числове значення.")

@admin_router.message(BeanStates.waiting_desc)
async def add_bean_desc(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(description=message.text)
    await message.answer("🌱 Сорт:")
    await state.set_state(BeanStates.waiting_sort)

@admin_router.message(BeanStates.waiting_sort)
async def add_bean_sort(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(sort=message.text)
    await message.answer("✨ Смак:")
    await state.set_state(BeanStates.waiting_taste)

@admin_router.message(BeanStates.waiting_taste)
async def add_bean_taste(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(taste=message.text)
    await message.answer("🔥 Обсмаження:")
    await state.set_state(BeanStates.waiting_roast)

@admin_router.message(BeanStates.waiting_roast)
async def add_bean_roast(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(roast=message.text)
    await message.answer("🌍 Країна:")
    await state.set_state(BeanStates.waiting_country)

@admin_router.message(BeanStates.waiting_country)
async def add_bean_country(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(country=message.text)
    await message.answer("🏔 Висота:")
    await state.set_state(BeanStates.waiting_altitude)

@admin_router.message(BeanStates.waiting_altitude)
async def add_bean_altitude(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(altitude=message.text)
    await message.answer("⚙️ Обробка:")
    await state.set_state(BeanStates.waiting_processing)

@admin_router.message(BeanStates.waiting_processing)
async def add_bean_processing(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(processing=message.text)
    await message.answer("🍋 Кислинка (0-5):")
    await state.set_state(BeanStates.waiting_acidity)

@admin_router.message(BeanStates.waiting_acidity)
async def add_bean_acidity(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(acidity=message.text)
    await message.answer("🍫 Гірчинка (0-5):")
    await state.set_state(BeanStates.waiting_bitterness)

@admin_router.message(BeanStates.waiting_bitterness)
async def add_bean_bitterness(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(bitterness=message.text)
    await message.answer("☕️ Тіло (Body) (0-5):")
    await state.set_state(BeanStates.waiting_body)

@admin_router.message(BeanStates.waiting_body)
async def add_bean_body(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(body=message.text)
    await message.answer("🖼 Фото (URL) або надішліть файл:")
    await state.set_state(BeanStates.waiting_image)

@admin_router.message(BeanStates.waiting_image, F.photo | F.text)
async def add_bean_image(message: Message, state: FSMContext, bot: Bot):
    if await restart_fsm_on_command(message, state): return
    from app.utils.photo_utils import process_photo
    img = await process_photo(message, bot)
    await state.update_data(image_url=img)
    data = await state.get_data()
    text = f"🔍 <b>ПЕРЕВІРКА:</b>\n\n☕️ {data['name']}\n🌍 {data.get('country', '-')}"
    await message.answer(text, reply_markup=akb.get_yes_no_kb("bean_save", "beans_back"), parse_mode="HTML")

@admin_router.callback_query(F.data == "bean_save")
async def save_new_bean(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await coffee_beans_db.add_bean(
        data['name'], data['price_250'], data['description'], data['sort'], data['taste'], data['roast'], 
        image_url=data.get('image_url', ""), country=data.get('country', ""), 
        altitude=data.get('altitude', ""), processing=data.get('processing', ""), 
        acidity=data.get('acidity', 0), bitterness=data.get('bitterness', 0), body=data.get('body', 0)
    )
    await public_data_cache.refresh("coffee")
    await safe_edit_message(callback.message, "✅ ДОДАНО!", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "beans_edit")
async def edit_beans_start(callback: CallbackQuery):
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer("Порожньо.")
        return
    await safe_edit_message(callback.message, "✏️ Редагування:", reply_markup=akb.get_beans_list_kb(beans, "beans_edt_it"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("beans_edt_it_"))
async def edit_bean_sel(callback: CallbackQuery, state: FSMContext):
    bid = callback.data.replace("beans_edt_it_", "")
    bean = await coffee_beans_db.get_bean_by_id(bid)
    await state.update_data(edit_id=bid)
    kb_edit = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назву", callback_data="ed_b_name"), InlineKeyboardButton(text="Ціну", callback_data="ed_b_price_250")],
        [InlineKeyboardButton(text="Опис", callback_data="ed_b_description"), InlineKeyboardButton(text="Сорт", callback_data="ed_b_sort")],
        [InlineKeyboardButton(text="🌍 Країна", callback_data="ed_b_country"), InlineKeyboardButton(text="🖼 Фото", callback_data="ed_b_image_url")],
        [InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="beans_edit")]
    ])
    await safe_edit_message(callback.message, f"Редагування <b>{bean['name']}</b>", reply_markup=kb_edit, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("ed_b_"))
async def edit_bean_field_start(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("ed_b_", "")
    await state.update_data(edit_field=field)
    await callback.message.answer(f"✏️ Введіть нове значення:")
    await state.set_state(BeanStates.edit_value)
    await callback.answer()

@admin_router.message(BeanStates.edit_value, F.photo | F.text)
async def edit_bean_value_save(message: Message, state: FSMContext, bot: Bot):
    if await restart_fsm_on_command(message, state): return
    data = await state.get_data()
    if data.get("edit_field") == "image_url":
        from app.utils.photo_utils import process_photo
        val = await process_photo(message, bot)
    else: val = (message.text or "").strip()
    await coffee_beans_db.update_bean(data.get("edit_id"), {data.get("edit_field"): val})
    await public_data_cache.refresh("coffee")
    await message.answer(f"✅ Оновлено!", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "menu_add")
async def add_item_start(callback: CallbackQuery, state: FSMContext):
    cats = await menu_db.get_categories()
    await safe_edit_message(callback.message, "📂 <b>Категорія:</b>", reply_markup=akb.get_category_selection_kb(cats, "m_add_cat", include_new=True), parse_mode="HTML")
    await state.set_state(MenuStates.waiting_category)

@admin_router.callback_query(F.data.startswith("m_add_cat_"), MenuStates.waiting_category)
async def add_item_cat(callback: CallbackQuery, state: FSMContext):
    cat_id = callback.data.replace("m_add_cat_", "")
    if cat_id == "NEW":
        await callback.message.answer("✏️ Назва нової категорії:")
        await state.set_state(MenuStates.waiting_new_category)
        return 
    cats = await menu_db.get_categories()
    from app.keyboards.user_keyboards import cat_key
    cat = next((c for c in cats if cat_key(c) == cat_id), None)
    await state.update_data(category=cat)
    await callback.message.answer("✏️ Назва позиції:")
    await state.set_state(MenuStates.waiting_name)

@admin_router.message(MenuStates.waiting_name)
async def add_item_name(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(name=message.text)
    await message.answer("💰 Ціна:")
    await state.set_state(MenuStates.waiting_price)

@admin_router.message(MenuStates.waiting_price)
async def add_item_price(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(price=message.text)
    await message.answer("📝 Опис:")
    await state.set_state(MenuStates.waiting_desc)

@admin_router.message(MenuStates.waiting_desc)
async def add_item_desc(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(description=message.text)
    await message.answer("🖼 Фото або надішліть файл:")
    await state.set_state(MenuStates.waiting_image)

@admin_router.message(MenuStates.waiting_image, F.photo | F.text)
async def add_item_image(message: Message, state: FSMContext, bot: Bot):
    if await restart_fsm_on_command(message, state): return
    from app.utils.photo_utils import process_photo
    img = await process_photo(message, bot)
    await state.update_data(image_url=img)
    data = await state.get_data()
    await message.answer(f"✨ {data['name']}\n💰 {data['price']}₴", reply_markup=akb.get_yes_no_kb("menu_save_item", "menu_back"), parse_mode="HTML")

@admin_router.callback_query(F.data == "locs_list")
async def list_locations(callback: CallbackQuery):
    locs = await location_db.get_all_locations()
    if not locs:
        await callback.answer("Локацій поки немає.")
        return
    text = "📍 <b>СПИСОК ЛОКАЦІЙ:</b>\n\n" + "\n".join([f"▫️ {l['name']} ({l['address']})" for l in locs])
    await safe_edit_message(callback.message, text, reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "locs_del")
async def del_locations_start(callback: CallbackQuery):
    locs = await location_db.get_all_locations()
    if not locs:
        await callback.answer("Локацій поки немає.")
        return
    await safe_edit_message(callback.message, "🗑 Оберіть локацію для ВИДАЛЕННЯ:", reply_markup=akb.get_locations_list_kb(locs, "locs_del_it"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("locs_del_it_"))
async def del_location_confirm(callback: CallbackQuery):
    lid = callback.data.replace("locs_del_it_", "")
    await location_db.delete_location(lid)
    await public_data_cache.refresh("locations")
    await callback.answer("Видалено!")
    await del_locations_start(callback)

@admin_router.callback_query(F.data == "locs_add")
async def add_location_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LocationStates.waiting_name)
    await callback.message.answer("✏️ Назва локації (н-р: Medelin на Закарпатській):")
    await callback.answer()

@admin_router.message(LocationStates.waiting_name)
async def add_loc_name(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(name=message.text)
    await message.answer("📍 Адреса:")
    await state.set_state(LocationStates.waiting_address)

@admin_router.message(LocationStates.waiting_address)
async def add_loc_address(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(address=message.text)
    await message.answer("🕒 Графік роботи (н-р: Пн-Нд: 08:00 - 21:00):")
    await state.set_state(LocationStates.waiting_schedule)

@admin_router.message(LocationStates.waiting_schedule)
async def add_loc_schedule(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(schedule=message.text)
    await message.answer("📞 Телефон:")
    await state.set_state(LocationStates.waiting_phone)

@admin_router.message(LocationStates.waiting_phone)
async def add_loc_phone(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(phone=message.text)
    await message.answer("📧 Email:")
    await state.set_state(LocationStates.waiting_email)

@admin_router.message(LocationStates.waiting_email)
async def add_loc_email(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(email=message.text)
    await message.answer("🗺 Google Maps URL:")
    await state.set_state(LocationStates.waiting_maps_url)

@admin_router.message(LocationStates.waiting_maps_url)
async def add_loc_maps(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(google_maps_url=message.text)
    await message.answer("✨ Атмосфера (короткий опис):")
    await state.set_state(LocationStates.waiting_atmosphere)

@admin_router.message(LocationStates.waiting_atmosphere)
async def add_loc_atmosphere(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    await state.update_data(atmosphere=message.text)
    await message.answer("🛋 Зручності (через кому, н-р: Wi-Fi, Робоча зона, Тераса):")
    await state.set_state(LocationStates.waiting_amenities)

@admin_router.message(LocationStates.waiting_amenities)
async def add_loc_amenities(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    amenities = [a.strip() for a in message.text.split(",") if a.strip()]
    await state.update_data(amenities=amenities)
    await message.answer("🖼 Фото (URL) або надішліть файл:")
    await state.set_state(LocationStates.waiting_image)

@admin_router.message(LocationStates.waiting_image, F.photo | F.text)
async def add_loc_image(message: Message, state: FSMContext, bot: Bot):
    if await restart_fsm_on_command(message, state): return
    from app.utils.photo_utils import process_photo
    img = await process_photo(message, bot)
    await state.update_data(image_url=img)
    await message.answer("🔢 Кількість столиків для бронювання:")
    await state.set_state(LocationStates.waiting_max_tables)

@admin_router.message(LocationStates.waiting_max_tables)
async def add_loc_tables(message: Message, state: FSMContext):
    if await restart_fsm_on_command(message, state): return
    try:
        val = int(message.text)
        await state.update_data(max_tables=val)
        data = await state.get_data()
        text = f"🔍 <b>ПЕРЕВІРКА:</b>\n\n📍 {data['name']}\n🏠 {data['address']}\n🛋 Зручності: {', '.join(data['amenities'])}"
        await message.answer(text, reply_markup=akb.get_yes_no_kb("loc_save", "locs_back"), parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Введіть ціле число.")

@admin_router.callback_query(F.data == "loc_save")
async def save_new_location(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    coords = extract_coords_from_maps(data.get('google_maps_url', ""))
    await location_db.add_location(
        name=data['name'], address=data['address'], schedule=data['schedule'], 
        phone=data['phone'], email=data['email'], google_maps_url=data['google_maps_url'],
        max_tables=data['max_tables'], coordinates={"lat": coords[0], "lon": coords[1]} if coords else None,
        image_url=data.get('image_url', ""), amenities=data.get('amenities', []), 
        atmosphere=data.get('atmosphere', "")
    )
    await public_data_cache.refresh("locations")
    await safe_edit_message(callback.message, "✅ ДОДАНО!", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "locs_edit")
async def edit_locations_start(callback: CallbackQuery):
    locs = await location_db.get_all_locations()
    if not locs:
        await callback.answer("Порожньо.")
        return
    await safe_edit_message(callback.message, "✏️ Редагування локації:", reply_markup=akb.get_locations_list_kb(locs, "locs_edt_it"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("locs_edt_it_"))
async def edit_location_sel(callback: CallbackQuery, state: FSMContext):
    lid = callback.data.replace("locs_edt_it_", "")
    loc = await location_db.get_location_by_id(lid)
    await state.update_data(edit_id=lid)
    kb_edit = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назву", callback_data="ed_l_name"), InlineKeyboardButton(text="Адресу", callback_data="ed_l_address")],
        [InlineKeyboardButton(text="Графік", callback_data="ed_l_schedule"), InlineKeyboardButton(text="Телефон", callback_data="ed_l_phone")],
        [InlineKeyboardButton(text="Атмосферу", callback_data="ed_l_atmosphere"), InlineKeyboardButton(text="Зручності", callback_data="ed_l_amenities")],
        [InlineKeyboardButton(text="🖼 Фото", callback_data="ed_l_image_url"), InlineKeyboardButton(text="🗺 Maps URL", callback_data="ed_l_google_maps_url")],
        [InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="locs_edit")]
    ])
    await safe_edit_message(callback.message, f"Редагування <b>{loc['name']}</b>", reply_markup=kb_edit, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("ed_l_"))
async def edit_location_field_start(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("ed_l_", "")
    await state.update_data(edit_field=field)
    if field == "amenities":
        await callback.message.answer("✏️ Введіть зручності через кому:")
    else:
        await callback.message.answer("✏️ Введіть нове значення:")
    await state.set_state(LocationStates.edit_value)
    await callback.answer()

@admin_router.message(LocationStates.edit_value, F.photo | F.text)
async def edit_location_value_save(message: Message, state: FSMContext, bot: Bot):
    if await restart_fsm_on_command(message, state): return
    data = await state.get_data()
    field = data.get("edit_field")
    if field == "image_url":
        from app.utils.photo_utils import process_photo
        val = await process_photo(message, bot)
    elif field == "amenities":
        val = [a.strip() for a in message.text.split(",") if a.strip()]
    else: val = (message.text or "").strip()
    
    update_data = {field: val}
    if field == "google_maps_url":
        coords = extract_coords_from_maps(val)
        if coords:
            update_data["coordinates"] = {"lat": coords[0], "lon": coords[1]}
            
    await location_db.update_location(data.get("edit_id"), update_data)
    await public_data_cache.refresh("locations")
    await message.answer(f"✅ Оновлено!", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")
    await state.clear()
