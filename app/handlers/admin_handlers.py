from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards import admin_keyboards as akb
from app.keyboards import user_keyboards as kb
from app.common.config import BOSS_IDS
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
from app.databases.user_database import user_db
from app.databases.menu_database import menu_db
from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.location_database import location_db
from app.databases.socials_database import socials_db
from app.utils.phone_utils import normalize_phone
from app.utils.payment_refunds import refund_telegram_payment
import re, time

admin_router = Router()

class AdminStates(StatesGroup):
    adding_admin_id = State()
    adding_admin_name = State()
    adding_admin_role = State()
    adding_admin_location = State()
    adding_admin_confirm = State()

class MenuStates(StatesGroup):
    waiting_category = State()
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
    waiting_confirm = State()
    edit_select = State()
    edit_field = State()
    edit_value = State()

class SocialStates(StatesGroup):
    waiting_name = State()
    waiting_url = State()

def extract_coords_from_maps(url: str) -> tuple[float, float] | None:
    regex = r"@(-?\d+\.\d+),(-?\d+\.\d+)"
    match = re.search(regex, url)
    if match: return float(match.group(1)), float(match.group(2))
    return None

async def get_user_role(user_id):
    if await admin_db.is_boss(user_id): return "boss"
    if await admin_db.is_super_admin(user_id): return "super"
    return "admin"

@admin_router.message(F.text == "↩️ НА ГОЛОВНУ")
async def back_to_main_from_admin(message: Message, state: FSMContext):
    await state.clear()
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
    bookings = await booking_db.get_new_bookings() if role in ("super", "boss") else await booking_db.get_new_bookings_by_locations(await admin_db.get_locations_for_admin(message.from_user.id))
    if not bookings:
        await message.answer("📭 <b>Наразі немає нових запитів.</b>", parse_mode="HTML")
        return
    locations_dict = await location_db.get_locations_dict()
    for b in bookings:
        loc_name = locations_dict.get(b['location_id'], {}).get('name', '—')
        t = f"📥 <b>НОВИЙ ЗАПИТ</b>\n\n👤 <b>Клієнт:</b> {b['fullname']}\n📞 <code>{b['phone']}</code>\n🏛 <b>Заклад:</b> {loc_name}\n🕔 <b>Час:</b> {b['date_time']}\n👥 <b>Гостей:</b> {b['people_count']}\n🥘 <b>Замовлення:</b> {b['cart']}"
        await message.answer(t, reply_markup=akb.get_booking_manage_kb(b['id']), parse_mode="HTML")

@admin_router.message(F.text == "👥 КОМАНДА")
async def manage_admins(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await state.clear()
    is_super = await admin_db.is_super_admin(message.from_user.id)
    await message.answer("👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>", reply_markup=akb.get_admin_management_kb(is_super), parse_mode="HTML")

@admin_router.message(F.text == "📋 МЕНЮ")
async def manage_menu(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await state.clear()
    if await get_user_role(message.from_user.id) != "boss":
        await message.answer("❌ Доступ до керування меню має тільки <b>БОСС</b>.", parse_mode="HTML")
        return
    await message.answer("📋 <b>КЕРУВАННЯ МЕНЮ</b>\nОберіть дію:", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.message(F.text == "🫘 ЗЕРНО")
async def manage_beans(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await state.clear()
    if await get_user_role(message.from_user.id) != "boss":
        await message.answer("❌ Доступ до керування зерном має тільки <b>БОСС</b>.", parse_mode="HTML")
        return
    await message.answer("🫘 <b>КЕРУВАННЯ ЗЕРНОВОЮ КАВОЮ</b>\nОберіть дію:", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")

@admin_router.message(F.text == "📍 ЛОКАЦІЇ")
async def manage_locations(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await state.clear()
    if await get_user_role(message.from_user.id) != "boss":
        await message.answer("❌ Доступ до керування локаціями має тільки <b>БОСС</b>.", parse_mode="HTML")
        return
    await message.answer("📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ</b>\nОберіть дію:", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

@admin_router.message(F.text == "📱 СОЦМЕРЕЖІ")
async def manage_socials(message: Message, state: FSMContext):
    if not await admin_db.is_admin(message.from_user.id): return
    await state.clear()
    if await get_user_role(message.from_user.id) != "boss":
        await message.answer("❌ Доступ до керування соцмережами має тільки <b>БОСС</b>.", parse_mode="HTML")
        return
    await message.answer("📱 <b>КЕРУВАННЯ СОЦМЕРЕЖАМИ</b>\nОберіть дію:", reply_markup=akb.get_socials_manage_kb(), parse_mode="HTML")

# --- SOCIALS HANDLERS ---

@admin_router.callback_query(F.data == "soc_back")
async def back_to_soc_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("📱 <b>КЕРУВАННЯ СОЦМЕРЕЖАМИ</b>\nОберіть дію:", reply_markup=akb.get_socials_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "soc_add")
async def add_soc_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Введіть <b>назву</b> (наприклад: Instagram):", parse_mode="HTML")
    await state.set_state(SocialStates.waiting_name)

@admin_router.message(SocialStates.waiting_name)
async def add_soc_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🔗 Введіть <b>посилання</b> (URL):")
    await state.set_state(SocialStates.waiting_url)

@admin_router.message(SocialStates.waiting_url)
async def add_soc_url(message: Message, state: FSMContext):
    data = await state.get_data()
    await socials_db.add_social(data['name'], message.text)
    await message.answer(f"✅ Соцмережу <b>{data['name']}</b> додано/оновлено!", reply_markup=akb.get_socials_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "soc_list")
async def list_socials_admin(callback: CallbackQuery):
    socs = await socials_db.get_all_socials()
    text = "📋 <b>СПИСОК СОЦМЕРЕЖ:</b>\n\n" + "\n".join([f"▫️ {s['name']}: {s['url']}" for s in socs]) if socs else "Список порожній."
    await callback.message.edit_text(text, reply_markup=akb.get_socials_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "soc_del")
async def del_soc_list(callback: CallbackQuery):
    socs = await socials_db.get_all_socials()
    if not socs:
        await callback.answer("Список порожній.")
        return
    await callback.message.edit_text("🗑 <b>Оберіть для видалення:</b>", reply_markup=akb.get_socials_list_kb(socs), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("soc_delete_"))
async def del_soc_confirm(callback: CallbackQuery):
    await socials_db.delete_social(callback.data.replace("soc_delete_", ""))
    await callback.answer("Видалено!")
    await del_soc_list(callback)

# --- LOCATIONS HANDLERS ---

@admin_router.callback_query(F.data == "locs_back")
async def back_to_locs_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ</b>\nОберіть дію:", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "locs_add")
async def add_loc_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Введіть <b>назву</b> закладу:", parse_mode="HTML")
    await state.set_state(LocationStates.waiting_name)

@admin_router.message(LocationStates.waiting_name)
async def add_loc_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📍 Введіть <b>адресу</b>:")
    await state.set_state(LocationStates.waiting_address)

@admin_router.message(LocationStates.waiting_address)
async def add_loc_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("⏰ Введіть <b>графік</b>:")
    await state.set_state(LocationStates.waiting_schedule)

@admin_router.message(LocationStates.waiting_schedule)
async def add_loc_schedule(message: Message, state: FSMContext):
    await state.update_data(schedule=message.text)
    await message.answer("📞 Введіть <b>телефон</b>:")
    await state.set_state(LocationStates.waiting_phone)

@admin_router.message(LocationStates.waiting_phone)
async def add_loc_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("✉️ Введіть <b>Email</b>:")
    await state.set_state(LocationStates.waiting_email)

@admin_router.message(LocationStates.waiting_email)
async def add_loc_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text)
    await message.answer("🗺 Надішліть <b>посилання на Google Maps</b>:")
    await state.set_state(LocationStates.waiting_maps_url)

@admin_router.message(LocationStates.waiting_maps_url)
async def add_loc_maps(message: Message, state: FSMContext):
    url = message.text.strip()
    coords = extract_coords_from_maps(url)
    if not coords:
        await message.answer("⚠️ Не вдалося знайти координати. Спробуйте інше посилання:")
        return
    await state.update_data(google_maps_url=url, lat=coords[0], lon=coords[1])
    data = await state.get_data()
    text = f"🔍 <b>ПЕРЕВІРКА ЛОКАЦІЇ:</b>\n\n🏛 <b>{data['name']}</b>\n📍 {data['address']}\n⏰ {data['schedule']}\n📞 {data['phone']}\n✉️ {data['email']}\n🧭 {data['lat']}, {data['lon']}"
    await message.answer(text, reply_markup=akb.get_yes_no_kb("loc_save_final", "locs_back"), parse_mode="HTML")
    await state.set_state(LocationStates.waiting_confirm)

@admin_router.callback_query(F.data == "loc_save_final", LocationStates.waiting_confirm)
async def save_new_loc(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await location_db.add_location(data['name'], data['address'], data['schedule'], data['phone'], data['email'], data['google_maps_url'], data['lat'], data['lon'])
    await callback.message.edit_text("✅ <b>ЛОКАЦІЮ ДОДАНО!</b>", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "locs_del")
async def del_loc_list(callback: CallbackQuery):
    locs = await location_db.get_all_locations()
    if not locs:
        await callback.answer("Список порожній.")
        return
    await callback.message.edit_text("🗑 <b>Оберіть локацію для видалення:</b>", reply_markup=akb.get_locations_list_kb(locs, "locs_delete"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("locs_delete_"))
async def del_loc_confirm(callback: CallbackQuery):
    await location_db.delete_location(callback.data.replace("locs_delete_", ""))
    await callback.answer("Видалено!")
    await del_loc_list(callback)

@admin_router.callback_query(F.data == "locs_list")
async def list_locs_admin(callback: CallbackQuery):
    locs = await location_db.get_all_locations()
    text = "📋 <b>СПИСОК ЛОКАЦІЙ:</b>\n\n" + "\n".join([f"▫️ {l['name']} ({l['address']})" for l in locs]) if locs else "Список порожній."
    await callback.message.edit_text(text, reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

# --- BEANS HANDLERS ---

@admin_router.callback_query(F.data == "beans_back")
async def back_to_beans_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🫘 <b>КЕРУВАННЯ ЗЕРНОВОЮ КАВОЮ</b>\nОберіть дію:", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "beans_add")
async def add_bean_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Введіть <b>назву</b> сорту:", parse_mode="HTML")
    await state.set_state(BeanStates.waiting_name)

@admin_router.message(BeanStates.waiting_name)
async def add_bean_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Введіть <b>ціну за 250г</b>:")
    await state.set_state(BeanStates.waiting_price_250)

@admin_router.message(BeanStates.waiting_price_250)
async def add_bean_price(message: Message, state: FSMContext):
    price = message.text.strip()
    if not price.isdigit():
        await message.answer("⚠️ Тільки число:")
        return
    await state.update_data(price_250=price)
    await message.answer("📝 Введіть <b>опис</b>:")
    await state.set_state(BeanStates.waiting_desc)

@admin_router.message(BeanStates.waiting_desc)
async def add_bean_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("🌱 Введіть <b>сорт</b>:")
    await state.set_state(BeanStates.waiting_sort)

@admin_router.message(BeanStates.waiting_sort)
async def add_bean_sort(message: Message, state: FSMContext):
    await state.update_data(sort=message.text)
    await message.answer("✨ Введіть <b>смак</b>:")
    await state.set_state(BeanStates.waiting_taste)

@admin_router.message(BeanStates.waiting_taste)
async def add_bean_taste(message: Message, state: FSMContext):
    await state.update_data(taste=message.text)
    await message.answer("🔥 Введіть <b>обсмаження</b>:")
    await state.set_state(BeanStates.waiting_roast)

@admin_router.message(BeanStates.waiting_roast)
async def add_bean_roast(message: Message, state: FSMContext):
    await state.update_data(roast=message.text)
    await message.answer("🖼 Надішліть <b>фото</b> або '-':")
    await state.set_state(BeanStates.waiting_image)

@admin_router.message(BeanStates.waiting_image)
async def add_bean_image(message: Message, state: FSMContext):
    img = message.text if message.text != "-" else ""
    await state.update_data(image_url=img)
    data = await state.get_data()
    prices = coffee_beans_db.calculate_prices(float(data['price_250']))
    text = f"🔍 <b>ПЕРЕВІРКА:</b>\n\n🫘 <b>{data['name']}</b>\n💰 {prices['250']}/{prices['500']}/{prices['1000']} ₴\n📝 {data['description']}\n🌱 {data['sort']}\n✨ {data['taste']}\n🔥 {data['roast']}"
    await message.answer(text, reply_markup=akb.get_yes_no_kb("bean_save_final", "beans_back"), parse_mode="HTML")
    await state.set_state(BeanStates.waiting_confirm)

@admin_router.callback_query(F.data == "bean_save_final", BeanStates.waiting_confirm)
async def save_new_bean(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await coffee_beans_db.add_bean(data['name'], data['price_250'], data['description'], data['sort'], data['taste'], data['roast'], data.get('image_url', ""))
    await callback.message.edit_text("✅ <b>ЗЕРНО ДОДАНО!</b>", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "beans_del")
async def del_bean_list(callback: CallbackQuery):
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer("Список порожній.")
        return
    await callback.message.edit_text("🗑 <b>Оберіть для видалення:</b>", reply_markup=akb.get_beans_list_kb(beans, "beans_delete"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("beans_delete_"))
async def del_bean_confirm(callback: CallbackQuery):
    await coffee_beans_db.delete_bean(callback.data.replace("beans_delete_", ""))
    await callback.answer("Видалено!")
    await del_bean_list(callback)

# --- MENU HANDLERS ---

@admin_router.callback_query(F.data == "menu_back")
async def back_to_menu_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("📋 <b>КЕРУВАННЯ МЕНЮ</b>\nОберіть дію:", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_cats")
async def list_categories(callback: CallbackQuery):
    cats = await menu_db.get_categories()
    text = "📚 <b>СПИСОК КАТЕГОРІЙ:</b>\n" + "\n".join(f"▫️ {akb.get_cat_with_emoji(c)}" for c in cats)
    await callback.message.edit_text(text, reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_add")
async def add_item_start(callback: CallbackQuery, state: FSMContext):
    cats = await menu_db.get_categories()
    await callback.message.edit_text("📂 <b>Категорія:</b>", reply_markup=akb.get_category_selection_kb(cats, "m_add_cat", include_new=True), parse_mode="HTML")
    await state.set_state(MenuStates.waiting_category)

@admin_router.callback_query(F.data.startswith("m_add_cat_"), MenuStates.waiting_category)
async def add_item_cat(callback: CallbackQuery, state: FSMContext):
    data = callback.data.replace("m_add_cat_", "")
    if data == "NEW":
        await callback.message.answer("✏️ Назва нової категорії:")
        return 
    cats = await menu_db.get_categories()
    cat = cats[int(data)]
    await state.update_data(category=cat)
    await callback.message.edit_text(f"📂 Категорія: <b>{cat}</b>\n✏️ Назва позиції:", parse_mode="HTML")
    await state.set_state(MenuStates.waiting_name)

@admin_router.message(MenuStates.waiting_category)
async def add_item_cat_text(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer(f"📂 Категорія: <b>{message.text}</b>\n✏️ Назва позиції:")
    await state.set_state(MenuStates.waiting_name)

@admin_router.message(MenuStates.waiting_name)
async def add_item_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Ціна:")
    await state.set_state(MenuStates.waiting_price)

@admin_router.message(MenuStates.waiting_price)
async def add_item_price(message: Message, state: FSMContext):
    p = message.text.strip()
    p = p if "₴" in p else p + " ₴"
    await state.update_data(price=p)
    await message.answer("📝 Опис або '-':")
    await state.set_state(MenuStates.waiting_desc)

@admin_router.message(MenuStates.waiting_desc)
async def add_item_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text if message.text != "-" else "")
    await message.answer("⚖️ Об'єм або '-':")
    await state.set_state(MenuStates.waiting_volume)

@admin_router.message(MenuStates.waiting_volume)
async def add_item_volume(message: Message, state: FSMContext):
    await state.update_data(volume=message.text if message.text != "-" else "")
    await message.answer("🔋 Калорії або '-':")
    await state.set_state(MenuStates.waiting_calories)

@admin_router.message(MenuStates.waiting_calories)
async def add_item_calories(message: Message, state: FSMContext):
    await state.update_data(calories=message.text if message.text != "-" else "")
    await message.answer("🖼 Фото або '-':")
    await state.set_state(MenuStates.waiting_image)

@admin_router.message(MenuStates.waiting_image)
async def add_item_image(message: Message, state: FSMContext):
    img = message.text if message.text != "-" else ""
    await state.update_data(image_url=img)
    data = await state.get_data()
    text = f"🔍 <b>ПЕРЕВІРКА:</b>\n\n📂 {data['category']}\n▫️ {data['name']}\n💰 {data['price']}\n📝 {data['description'] or '—'}\n⚖️ {data['volume'] or '—'}\n🔋 {data['calories'] or '—'}\n🖼 {img or '—'}"
    await message.answer(text, reply_markup=akb.get_yes_no_kb("menu_save", "menu_back"), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_save")
async def save_new_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await menu_db.add_item(data['category'], data['name'], data['price'], data['description'], data['volume'], data['calories'], data.get('image_url', ""))
    await callback.message.edit_text("✅ ПОЗИЦІЮ ДОДАНО!", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "menu_del")
async def del_item_start(callback: CallbackQuery, state: FSMContext):
    cats = await menu_db.get_categories()
    await callback.message.edit_text("🗑 Оберіть категорію:", reply_markup=akb.get_category_selection_kb(cats, "m_del_cat"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("m_del_cat_"))
async def del_item_cat_sel(callback: CallbackQuery):
    idx = int(callback.data.replace("m_del_cat_", ""))
    cats = await menu_db.get_categories()
    cat = cats[idx]
    items = await menu_db.get_items_by_category(cat)
    item_list = [(i[0], i[1]) for i in items]
    if not item_list:
        await callback.answer("Порожньо.")
        return
    await callback.message.edit_text(f"🗑 {cat}\nОберіть для видалення:", reply_markup=akb.get_items_in_category_kb(item_list, "m_del_it"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("m_del_it_"))
async def del_item_confirm(callback: CallbackQuery):
    await menu_db.delete_item(callback.data.replace("m_del_it_", ""))
    await callback.answer("Видалено!")
    await del_item_start(callback, None)

# --- GENERIC ORDER ACTIONS ---

@admin_router.callback_query(F.data.startswith("adm_confirm_"))
async def confirm_booking(callback: CallbackQuery, bot: Bot):
    bid = callback.data.split("_")[2]
    await booking_db.update_status(bid, "confirmed")
    b = await booking_db.get_booking_by_id(bid)
    if b: await bot.send_message(b["user_id"], "✅ <b>ВАШЕ ЗАМОВЛЕННЯ ПІДТВЕРДЖЕНО!</b>", parse_mode="HTML")
    await callback.message.edit_text(callback.message.text + "\n\n✅ <b>ПІДТВЕРДЖЕНО</b>", parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_cancel_"))
async def cancel_booking(callback: CallbackQuery, bot: Bot):
    bid = callback.data.split("_")[2]
    await booking_db.update_status(bid, "cancelled")
    b = await booking_db.get_booking_by_id(bid)
    if b: await bot.send_message(b["user_id"], "❌ <b>ЗАМОВЛЕННЯ ВІДХИЛЕНО.</b>", parse_mode="HTML")
    await callback.message.edit_text(callback.message.text + "\n\n❌ <b>ВІДХИЛЕНО</b>", parse_mode="HTML")
