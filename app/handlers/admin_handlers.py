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

def extract_coords_from_maps(url: str) -> tuple[float, float] | None:
    regex = r"@(-?\d+\.\d+),(-?\d+\.\d+)"
    match = re.search(regex, url)
    if match:
        return float(match.group(1)), float(match.group(2))
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
    if role in ("super", "boss"): 
        bookings = await booking_db.get_new_bookings()
    else:
        locations = await admin_db.get_locations_for_admin(message.from_user.id)
        bookings = await booking_db.get_new_bookings_by_locations(locations)
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

# --- LOCATIONS HANDLERS ---

@admin_router.callback_query(F.data == "locs_back")
async def back_to_locs_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if await get_user_role(callback.from_user.id) != "boss": return
    await callback.message.edit_text("📍 <b>КЕРУВАННЯ ЛОКАЦІЯМИ</b>\nОберіть дію:", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "locs_add")
async def add_loc_start(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    await callback.message.edit_text("✏️ Введіть <b>назву</b> закладу (наприклад: Medelin на Корятовича):", parse_mode="HTML")
    await state.set_state(LocationStates.waiting_name)

@admin_router.message(LocationStates.waiting_name)
async def add_loc_name(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(name=message.text)
    await message.answer("📍 Введіть <b>адресу</b>:")
    await state.set_state(LocationStates.waiting_address)

@admin_router.message(LocationStates.waiting_address)
async def add_loc_address(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(address=message.text)
    await message.answer("⏰ Введіть <b>графік роботи</b> (наприклад: Пн–Нд: 08:00 – 20:00):")
    await state.set_state(LocationStates.waiting_schedule)

@admin_router.message(LocationStates.waiting_schedule)
async def add_loc_schedule(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(schedule=message.text)
    await message.answer("📞 Введіть <b>номер телефону</b>:")
    await state.set_state(LocationStates.waiting_phone)

@admin_router.message(LocationStates.waiting_phone)
async def add_loc_phone(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(phone=message.text)
    await message.answer("✉️ Введіть <b>Email</b>:")
    await state.set_state(LocationStates.waiting_email)

@admin_router.message(LocationStates.waiting_email)
async def add_loc_email(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(email=message.text)
    await message.answer("🗺 Надішліть <b>посилання на Google Maps</b> (з нього будуть витягнуті координати):")
    await state.set_state(LocationStates.waiting_maps_url)

@admin_router.message(LocationStates.waiting_maps_url)
async def add_loc_maps(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    url = message.text.strip()
    coords = extract_coords_from_maps(url)
    if not coords:
        await message.answer("⚠️ Не вдалося знайти координати у посиланні. Переконайтеся, що посилання містить координати (символ @ та цифри через кому). Спробуйте ще раз або надішліть інше посилання:")
        return
    await state.update_data(google_maps_url=url, lat=coords[0], lon=coords[1])
    data = await state.get_data()
    text = (f"🔍 <b>ПЕРЕВІРКА ЛОКАЦІЇ:</b>\n\n"
            f"🏛 <b>{data['name']}</b>\n"
            f"📍 Адреса: {data['address']}\n"
            f"⏰ Графік: {data['schedule']}\n"
            f"📞 Тел: {data['phone']}\n"
            f"✉️ Email: {data['email']}\n"
            f"🧭 Координати: {data['lat']}, {data['lon']}")
    await message.answer(text, reply_markup=akb.get_yes_no_kb("loc_save_final", "locs_back"), parse_mode="HTML")
    await state.set_state(LocationStates.waiting_confirm)

@admin_router.callback_query(F.data == "loc_save_final", LocationStates.waiting_confirm)
async def save_new_loc(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    data = await state.get_data()
    await location_db.add_location(
        name=data['name'],
        address=data['address'],
        schedule=data['schedule'],
        phone=data['phone'],
        email=data['email'],
        google_maps_url=data['google_maps_url'],
        lat=data['lat'],
        lon=data['lon']
    )
    await callback.message.edit_text("✅ <b>ЛОКАЦІЮ ДОДАНО!</b>", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "locs_del")
async def del_loc_list(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    locs = await location_db.get_all_locations()
    if not locs:
        await callback.answer("Список порожній.")
        return
    await callback.message.edit_text("🗑 <b>Оберіть локацію для видалення:</b>", reply_markup=akb.get_locations_list_kb(locs, "locs_delete"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("locs_delete_"))
async def del_loc_confirm(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    loc_id = callback.data.replace("locs_delete_", "")
    await location_db.delete_location(loc_id)
    await callback.answer("Видалено!")
    await del_loc_list(callback)

@admin_router.callback_query(F.data == "locs_list")
async def list_locs_admin(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    locs = await location_db.get_all_locations()
    if not locs:
        await callback.answer("Список порожній.")
        return
    text = "📋 <b>СПИСОК ЛОКАЦІЙ В БАЗІ:</b>\n\n"
    for l in locs:
        text += f"▫️ <b>{l['name']}</b> ({l['address']})\n"
    await callback.message.edit_text(text, reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

# --- BEANS HANDLERS ---

@admin_router.callback_query(F.data == "beans_back")
async def back_to_beans_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if await get_user_role(callback.from_user.id) != "boss": return
    await callback.message.edit_text("🫘 <b>КЕРУВАННЯ ЗЕРНОВОЮ КАВОЮ</b>\nОберіть дію:", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "beans_add")
async def add_bean_start(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    await callback.message.edit_text("✏️ Введіть <b>назву</b> сорту (наприклад: Індія Монсун Малабар):", parse_mode="HTML")
    await state.set_state(BeanStates.waiting_name)

@admin_router.message(BeanStates.waiting_name)
async def add_bean_name(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(name=message.text)
    await message.answer("💰 Введіть <b>ціну за 250г</b> (тільки цифри):")
    await state.set_state(BeanStates.waiting_price_250)

@admin_router.message(BeanStates.waiting_price_250)
async def add_bean_price(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    price = message.text.strip()
    if not price.isdigit():
        await message.answer("⚠️ Введіть тільки число (наприклад: 271):")
        return
    await state.update_data(price_250=price)
    await message.answer("📝 Введіть <b>короткий опис</b> сорту:")
    await state.set_state(BeanStates.waiting_desc)

@admin_router.message(BeanStates.waiting_desc)
async def add_bean_desc(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(description=message.text)
    await message.answer("🌱 Введіть <b>склад/сорт</b> (наприклад: 100% Арабіка):")
    await state.set_state(BeanStates.waiting_sort)

@admin_router.message(BeanStates.waiting_sort)
async def add_bean_sort(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(sort=message.text)
    await message.answer("✨ Введіть <b>смакові ноти</b>:")
    await state.set_state(BeanStates.waiting_taste)

@admin_router.message(BeanStates.waiting_taste)
async def add_bean_taste(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(taste=message.text)
    await message.answer("🔥 Введіть <b>ступінь обсмаження</b>:")
    await state.set_state(BeanStates.waiting_roast)

@admin_router.message(BeanStates.waiting_roast)
async def add_bean_roast(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(roast=message.text)
    await message.answer("🖼 Надішліть <b>посилання на фото</b> або '-' щоб пропустити:")
    await state.set_state(BeanStates.waiting_image)

@admin_router.message(BeanStates.waiting_image)
async def add_bean_image(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    image_url = message.text if message.text != "-" else ""
    await state.update_data(image_url=image_url)
    data = await state.get_data()
    prices = coffee_beans_db.calculate_prices(float(data['price_250']))
    text = (f"🔍 <b>ПЕРЕВІРКА ЗЕРНА:</b>\n\n"
            f"🫘 <b>{data['name']}</b>\n"
            f"💰 Ціни: {prices['250']} / {prices['500']} / {prices['1000']} ₴\n"
            f"📝 {data['description']}\n"
            f"🌱 Сорт: {data['sort']}\n"
            f"✨ Смак: {data['taste']}\n"
            f"🔥 Обсмаження: {data['roast']}\n"
            f"🖼 Фото: {image_url or 'немає'}")
    await message.answer(text, reply_markup=akb.get_yes_no_kb("bean_save_final", "beans_back"), parse_mode="HTML")
    await state.set_state(BeanStates.waiting_confirm)

@admin_router.callback_query(F.data == "bean_save_final", BeanStates.waiting_confirm)
async def save_new_bean(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    data = await state.get_data()
    await coffee_beans_db.add_bean(
        name=data['name'],
        price_250=data['price_250'],
        description=data['description'],
        sort=data['sort'],
        taste=data['taste'],
        roast=data['roast'],
        image_url=data.get('image_url', "")
    )
    await callback.message.edit_text("✅ <b>ЗЕРНО ДОДАНО!</b>", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "beans_del")
async def del_bean_list(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer("Список порожній.")
        return
    await callback.message.edit_text("🗑 <b>Оберіть зерно для видалення:</b>", reply_markup=akb.get_beans_list_kb(beans, "beans_delete"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("beans_delete_"))
async def del_bean_confirm(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    bean_id = callback.data.replace("beans_delete_", "")
    await coffee_beans_db.delete_bean(bean_id)
    await callback.answer("Видалено!")
    await del_bean_list(callback)

@admin_router.callback_query(F.data == "beans_list")
async def list_beans_admin(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer("Список порожній.")
        return
    text = "📋 <b>СПИСОК ЗЕРНА В БАЗІ:</b>\n\n"
    for b in beans:
        text += f"▫️ <b>{b['name']}</b> ({b['price_250']} ₴)\n"
    await callback.message.edit_text(text, reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")

# --- MENU HANDLERS ---

@admin_router.callback_query(F.data == "menu_back")
async def back_to_menu_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if await get_user_role(callback.from_user.id) != "boss": return
    await callback.message.edit_text("📋 <b>КЕРУВАННЯ МЕНЮ</b>\nОберіть дію:", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_cats")
async def list_categories(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    cats = await menu_db.get_categories()
    text = "📚 <b>СПИСОК КАТЕГОРІЙ:</b>\n" + "\n".join(f"▫️ {akb.get_cat_with_emoji(c)}" for c in cats)
    await callback.message.edit_text(text, reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_add")
async def add_item_start(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    cats = await menu_db.get_categories()
    await callback.message.edit_text("📂 <b>Оберіть категорію або створіть нову:</b>", reply_markup=akb.get_category_selection_kb(cats, "m_add_cat", include_new=True), parse_mode="HTML")
    await state.set_state(MenuStates.waiting_category)

@admin_router.callback_query(F.data.startswith("m_add_cat_"), MenuStates.waiting_category)
async def add_item_cat(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    data = callback.data.replace("m_add_cat_", "")
    if data == "NEW":
        await callback.message.answer("✏️ Введіть назву нової категорії:")
        return 
    cats = await menu_db.get_categories()
    try:
        cat_name = cats[int(data)]
        await state.update_data(category=cat_name)
        await callback.message.edit_text(f"📂 Категорія: <b>{cat_name}</b>\n\n✏️ Введіть назву позиції:", parse_mode="HTML")
        await state.set_state(MenuStates.waiting_name)
    except: pass

@admin_router.message(MenuStates.waiting_category)
async def add_item_cat_text(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(category=message.text)
    await message.answer(f"📂 Категорія: <b>{message.text}</b>\n\n✏️ Введіть назву позиції:", parse_mode="HTML")
    await state.set_state(MenuStates.waiting_name)

@admin_router.message(MenuStates.waiting_name)
async def add_item_name(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    await state.update_data(name=message.text)
    data = await state.get_data()
    if data.get("category") == "Кава в зернах":
        await message.answer("💰 Введіть ціну за 250г:")
        await state.set_state(MenuStates.waiting_price_250)
    else:
        await message.answer("💰 Введіть ціну (наприклад: 50 або 50 ₴):")
        await state.set_state(MenuStates.waiting_price)

@admin_router.message(MenuStates.waiting_price_250)
async def add_item_price_250(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    price = message.text.strip()
    if not any(char.isdigit() for char in price):
        await message.answer("⚠️ Ціна має містити цифри.")
        return
    await state.update_data(price_250=price)
    await message.answer("💰 Введіть ціну за 500г:")
    await state.set_state(MenuStates.waiting_price_500)

@admin_router.message(MenuStates.waiting_price_500)
async def add_item_price_500(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    price = message.text.strip()
    if not any(char.isdigit() for char in price):
        await message.answer("⚠️ Ціна має містити цифри.")
        return
    await state.update_data(price_500=price)
    await message.answer("💰 Введіть ціну за 1кг:")
    await state.set_state(MenuStates.waiting_price_1000)

@admin_router.message(MenuStates.waiting_price_1000)
async def add_item_price_1000(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    price = message.text.strip()
    if not any(char.isdigit() for char in price):
        await message.answer("⚠️ Ціна має містити цифри.")
        return
    await state.update_data(price_1000=price)
    await message.answer("📝 Введіть опис або надішліть '-' щоб пропустити:")
    await state.set_state(MenuStates.waiting_desc)

@admin_router.message(MenuStates.waiting_price)
async def add_item_price(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    data = await state.get_data()
    if data.get("category") == "Кава в зернах":
        await message.answer("💰 Введіть ціну за 250г:")
        await state.set_state(MenuStates.waiting_price_250)
        return
    price = message.text.strip()
    if not any(char.isdigit() for char in price):
        await message.answer("⚠️ Ціна має містити цифри.")
        return
    if "₴" not in price and "грн" not in price.lower(): price += " ₴"
    await state.update_data(price=price)
    await message.answer("📝 Введіть опис або надішліть '-' щоб пропустити:")
    await state.set_state(MenuStates.waiting_desc)

@admin_router.message(MenuStates.waiting_desc)
async def add_item_desc(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    desc = message.text if message.text != "-" else ""
    await state.update_data(description=desc)
    await message.answer("⚖️ Введіть об'єм/вагу (наприклад: 250 мл або 150 г) або '-' щоб пропустити:")
    await state.set_state(MenuStates.waiting_volume)

@admin_router.message(MenuStates.waiting_volume)
async def add_item_volume(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    volume = message.text if message.text != "-" else ""
    await state.update_data(volume=volume)
    await message.answer("🔋 Введіть енергетичну цінність (ккал) або '-' щоб пропустити:")
    await state.set_state(MenuStates.waiting_calories)

@admin_router.message(MenuStates.waiting_calories)
async def add_item_calories(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    calories = message.text if message.text != "-" else ""
    await state.update_data(calories=calories)
    await message.answer("🖼 <b>НАДІШЛІТЬ ПОСИЛАННЯ НА ФОТО</b> (Unsplash або інше) або '-' щоб пропустити:")
    await state.set_state(MenuStates.waiting_image)

@admin_router.message(MenuStates.waiting_image)
async def add_item_image(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    image_url = message.text if message.text != "-" else ""
    await state.update_data(image_url=image_url)
    data = await state.get_data()
    price_str = f"💰 250г: {data['price_250']} ₴\n💰 500г: {data['price_500']} ₴\n💰 1кг: {data['price_1000']} ₴" if data.get("category") == "Кава в зернах" else f"💰 {data['price']}"
    text = (f"🔍 <b>ПЕРЕВІРКА:</b>\n\n📂 {data['category']}\n▫️ {data['name']}\n{price_str}\n📝 {data['description'] or 'без опису'}\n⚖️ {data['volume'] or 'не вказано'}\n🔋 {data['calories'] or 'не вказано'}\n🖼 Фото: {image_url or 'немає'}")
    await message.answer(text, reply_markup=akb.get_yes_no_kb("menu_save", "menu_back"), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_save")
async def save_new_item(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    data = await state.get_data()
    price = {"250": data['price_250'], "500": data['price_500'], "1000": data['price_1000']} if data.get("category") == "Кава в зернах" else data['price']
    await menu_db.add_item(data['category'], data['name'], price, data['description'], data['volume'], data['calories'], data.get('image_url', ""))
    await callback.message.edit_text("✅ <b>ПОЗИЦІЮ ДОДАНО!</b>", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "menu_del")
async def del_item_start(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    cats = await menu_db.get_categories()
    await callback.message.edit_text("🗑 <b>Видалення:</b> Оберіть категорію:", reply_markup=akb.get_category_selection_kb(cats, "m_del_cat"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("m_del_cat_"))
async def del_item_cat_sel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    try:
        idx = int(callback.data.replace("m_del_cat_", ""))
        cats = await menu_db.get_categories()
        cat = cats[idx]
        items = await menu_db.get_items_by_category(cat)
        item_list = [(i[0], i[1]) for i in items]
        if not item_list:
            await callback.answer("Категорія порожня.")
            return
        await callback.message.edit_text(f"🗑 Категорія: <b>{cat}</b>\nОберіть позицію:", reply_markup=akb.get_items_in_category_kb(item_list, "m_del_it"), parse_mode="HTML")
    except: pass

@admin_router.callback_query(F.data.startswith("m_del_it_"))
async def del_item_confirm(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    item_id = callback.data.replace("m_del_it_", "")
    item = await menu_db.get_item_by_id(item_id)
    if not item: return
    await menu_db.delete_item(item_id)
    await callback.answer(f"🗑 Видалено: {item[2]}")
    await del_item_start(callback, None)

@admin_router.callback_query(F.data == "menu_edit")
async def edit_item_start(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    cats = await menu_db.get_categories()
    await callback.message.edit_text("✏️ <b>Редагування:</b> Оберіть категорію:", reply_markup=akb.get_category_selection_kb(cats, "m_edt_cat"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("m_edt_cat_"))
async def edit_item_cat_sel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "boss": return
    try:
        idx = int(callback.data.replace("m_edt_cat_", ""))
        cats = await menu_db.get_categories()
        cat = cats[idx]
        items = await menu_db.get_items_by_category(cat)
        item_list = [(i[0], i[1]) for i in items]
        await callback.message.edit_text(f"✏️ Категорія: <b>{cat}</b>\nОберіть позицію:", reply_markup=akb.get_items_in_category_kb(item_list, "m_edt_it"), parse_mode="HTML")
    except: pass

@admin_router.callback_query(F.data.startswith("m_edt_it_"))
async def edit_item_select(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    item_id = callback.data.replace("m_edt_it_", "")
    item = await menu_db.get_item_by_id(item_id)
    if not item: return
    await state.update_data(edit_id=item_id, current_item=item)
    price_str = f"{item[3].get('250', 'n/a')} / {item[3].get('500', 'n/a')} / {item[3].get('1000', 'n/a')} ₴" if item[1] == "Кава в зернах" and isinstance(item[3], dict) else str(item[3])
    text = (f"✏️ <b>РЕДАГУВАННЯ:</b>\n▫️ {item[2]}\n💰 {price_str}\n📝 {item[4] or '—'}\n⚖️ {item[5] or '—'}\n🔋 {item[6] or '—'}\n🖼 Фото: {item[7] or 'немає'}")
    kb_edit = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назву", callback_data="edt_f_name"), InlineKeyboardButton(text="Ціну", callback_data="edt_f_price")],
        [InlineKeyboardButton(text="Опис", callback_data="edt_f_desc"), InlineKeyboardButton(text="Об'єм", callback_data="edt_f_vol")],
        [InlineKeyboardButton(text="Калорії", callback_data="edt_f_cal"), InlineKeyboardButton(text="Фото", callback_data="edt_f_img")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_edit")]
    ])
    await callback.message.edit_text(text, reply_markup=kb_edit, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("edt_f_"))
async def edit_field_start(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "boss": return
    field = callback.data.replace("edt_f_", "")
    await state.update_data(edit_field=field)
    data = await state.get_data()
    current_item = data.get("current_item")
    prompt_text = "✏️ Введіть нове значення:"
    if field == 'price' and current_item and current_item[1] == "Кава в зернах":
        prompt_text = "✏️ Введіть 3 ціни через / (250г / 500г / 1кг):"
    elif field == 'img':
        prompt_text = "🖼 Надішліть нове посилання на фото:"
    await callback.message.answer(prompt_text)
    await state.set_state(MenuStates.edit_waiting_value)

@admin_router.message(MenuStates.edit_waiting_value)
async def edit_field_save(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "boss": return
    data = await state.get_data()
    item_id = data.get('edit_id')
    if not item_id:
        await state.clear()
        return
    field = data.get('edit_field')
    current_item = data.get('current_item')
    update_value = message.text
    if field == 'price' and current_item and current_item[1] == "Кава в зернах":
        try:
            p250, p500, p1000 = [p.strip() for p in message.text.split('/')]
            update_value = {"250": p250, "500": p500, "1000": p1000}
        except ValueError:
            await message.answer("⚠️ Невірний формат. Введіть 3 ціни через / (напр. 100 / 180 / 350)")
            return
    field_map = {"name": "name", "price": "price", "desc": "description", "vol": "volume", "cal": "calories", "img": "image_url"}
    db_field = field_map.get(field)
    if db_field:
        await menu_db.update_item(item_id, {db_field: update_value})
        await message.answer("✅ Зміни збережено!")
    await state.clear()
    await manage_menu(message, state)

@admin_router.callback_query(F.data.startswith("adm_confirm_"))
async def confirm_booking(callback: CallbackQuery, bot: Bot):
    bid = callback.data.split("_")[2]
    b = await booking_db.get_booking_by_id(bid)
    if not b: return
    await booking_db.update_status(bid, "confirmed")
    try: await bot.send_message(b["user_id"], "✅ <b>ВАШЕ ЗАМОВЛЕННЯ ПІДТВЕРДЖЕНО!</b>\nЧекаємо на вас.", parse_mode="HTML")
    except: pass
    await callback.message.edit_text(callback.message.text + "\n\n✅ <b>ПІДТВЕРДЖЕНО</b>", parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_cancel_"))
async def cancel_booking(callback: CallbackQuery, bot: Bot):
    bid = callback.data.split("_")[2]
    b = await booking_db.get_booking_by_id(bid)
    if not b: return
    await booking_db.update_status(bid, "cancelled")
    refund_msg = ""
    userdata = b
    pay_id = userdata.get("payment_id")
    provider_id = userdata.get("provider_payment_id")
    if pay_id:
        refunded, refund_error = await refund_telegram_payment(bot, pay_id, provider_id)
        if refunded:
            refund_msg = "\n\n💳 <b>ОПЛАЧЕНО.</b>\nГроші повернено автоматично."
            await booking_db.set_refund_status(bid, "refunded")
            try: await bot.send_message(userdata.get("user_id"), "❌ <b>ЗАМОВЛЕННЯ ВІДХИЛЕНО.</b>\nГроші повернено автоматично.", parse_mode="HTML")
            except: pass
        else:
            refund_msg = f"\n\n⚠️ <b>Повернення не вдалося:</b> {refund_error}"
            await booking_db.set_refund_status(bid, f"refund_failed:{refund_error}")
    else:
        try: await bot.send_message(userdata.get("user_id"), "❌ <b>ЗАМОВЛЕННЯ ВІДХИЛЕНО.</b>", parse_mode="HTML")
        except: pass
    await callback.message.edit_text(callback.message.text + f"\n\n❌ <b>ВІДХИЛЕНО</b>{refund_msg}", parse_mode="HTML")

@admin_router.callback_query(F.data == "adm_add_new")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_db.is_admin(callback.from_user.id): return
    await state.set_state(AdminStates.adding_admin_id)
    await callback.message.answer("👤 <b>ВВЕДІТЬ ДАНІ ПРАЦІВНИКА</b> (@username, телефон або ID):", parse_mode="HTML")
    await callback.answer()

@admin_router.message(AdminStates.adding_admin_id)
async def add_admin_identifier(message: Message, state: FSMContext):
    text = message.text.strip()
    user_info = None
    if text.startswith("@"): user_info = await user_db.get_user_by_username(text.lstrip("@"))
    elif text.startswith("+") or (text.isdigit() and len(text) >= 10): user_info = await user_db.get_user_by_phone(text)
    elif text.isdigit():
        uid = int(text); user_info = await user_db.get_user_by_id(uid)
        if not user_info: user_info = (uid, "Невідомий", "N/A", None)
    else: user_info = await user_db.get_user_by_username(text)
    if not user_info:
        await message.answer("❌ Користувача не знайдено. Перевірте дані.")
        return
    await state.update_data(new_admin_id=user_info[0], candidate_name=user_info[1], new_admin_username=user_info[2] or "")
    await state.set_state(AdminStates.adding_admin_name)
    await message.answer("👤 <b>ВВЕДІТЬ ВІДОБРАЖУВАЛЬНЕ ІМ'Я ПРАЦІВНИКА:</b>", parse_mode="HTML")

@admin_router.message(AdminStates.adding_admin_name)
async def add_admin_name(message: Message, state: FSMContext):
    await state.update_data(new_admin_name=message.text)
    await state.set_state(AdminStates.adding_admin_role)
    await message.answer("🎭 <b>ВВЕДІТЬ РОЛЬ</b> (admin, super, boss):", parse_mode="HTML")

@admin_router.message(AdminStates.adding_admin_role)
async def add_admin_role_text(message: Message, state: FSMContext):
    user_role = await get_user_role(message.from_user.id)
    valid_roles = ["admin", "super", "boss"] if user_role == "boss" else ["admin", "super"]
    role_input = message.text.strip().lower()
    if role_input not in valid_roles:
        await message.answer(f"⚠️ Невірна роль або недостатньо прав. Дозволені: <b>{', '.join(valid_roles)}</b>", parse_mode="HTML")
        return
    await state.update_data(new_admin_role=role_input)
    if role_input == "admin":
        await state.set_state(AdminStates.adding_admin_location)
        locations = await location_db.get_all_locations()
        loc_list = "\n".join([f"<b>{str(l['_id'])}</b> — {l['name']}" for l in locations])
        await message.answer(f"🏛 <b>ВВЕДІТЬ ID ЗАКЛАДУ:</b>\n\n{loc_list}", parse_mode="HTML")
    else:
        locations = await location_db.get_all_locations()
        await state.update_data(new_admin_locations=[str(l['_id']) for l in locations])
        await add_admin_show_summary(message, state)

@admin_router.message(AdminStates.adding_admin_location)
async def add_admin_location_text(message: Message, state: FSMContext):
    loc_id = message.text.strip()
    loc = await location_db.get_location_by_id(loc_id)
    if not loc:
        await message.answer("⚠️ Невірний ID. Оберіть ID зі списку вище:")
        return
    await state.update_data(new_admin_locations=[loc_id])
    await add_admin_show_summary(message, state)

async def add_admin_show_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    role_names = {"admin": "Адмін", "super": "Суперадмін", "boss": "Босс"}
    locations_dict = await location_db.get_locations_dict()
    locs = ", ".join([locations_dict.get(l, {}).get('name', '—') for l in data['new_admin_locations']])
    text = (f"✅ <b>ПІДТВЕРДІТЬ ДАНІ:</b>\n\n👤 Ім'я: <b>{data['new_admin_name']}</b>\n🎭 Роль: <b>{role_names[data['new_admin_role']]}</b>\n🏛 Заклад: <b>{locs}</b>\n🆔 ID: <code>{data['new_admin_id']}</code>")
    await message.answer(text, reply_markup=akb.get_yes_no_kb("adm_save_final", "adm_back_to_manage"), parse_mode="HTML")
    await state.set_state(AdminStates.adding_admin_confirm)

@admin_router.callback_query(F.data == "adm_save_final", AdminStates.adding_admin_confirm)
async def add_admin_final_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await admin_db.add_admin(user_id=data['new_admin_id'], username=data.get('new_admin_username', ""), display_name=data['new_admin_name'], added_by=callback.from_user.id, role=data['new_admin_role'], locations=data['new_admin_locations'])
    await state.clear()
    await callback.message.edit_text(f"✅ Працівника <b>{data['new_admin_name']}</b> додано!", parse_mode="HTML")
    await callback.answer()

async def get_visible_admins_for_user(user_id: int):
    all_admins = await admin_db.get_admins_with_locations()
    role = await get_user_role(user_id)
    if role == "boss": return all_admins
    elif role == "super": return [a for a in all_admins if a[3] != "boss"]
    else:
        my_locs = set(await admin_db.get_locations_for_admin(user_id))
        return [a for a in all_admins if a[3] not in ("super", "boss") and set(a[6]).intersection(my_locs)]

@admin_router.callback_query(F.data == "adm_list")
async def manage_team_list(callback: CallbackQuery):
    if not await admin_db.is_admin(callback.from_user.id): return
    admins = await get_visible_admins_for_user(callback.from_user.id)
    text = "👥 <b>СПИСОК КОМАНДИ:</b>\n\n" + "\n".join([f"▫️ {a[2] or a[1] or a[0]} — <b>{a[3].upper()}</b>" for a in admins])
    try: await callback.message.edit_text(text, reply_markup=akb.get_admin_management_kb(await admin_db.is_super_admin(callback.from_user.id)), parse_mode="HTML")
    except TelegramBadRequest: await callback.answer()

@admin_router.callback_query(F.data == "adm_remove")
async def remove_admin_list(callback: CallbackQuery):
    if not await admin_db.is_super_admin(callback.from_user.id): return
    admins = await get_visible_admins_for_user(callback.from_user.id)
    filtered = [a[:4] for a in admins if a[0] != callback.from_user.id]
    if not filtered: await callback.answer("Немає кого видаляти."); return
    try: await callback.message.edit_text("🗑 <b>Оберіть для видалення:</b>", reply_markup=akb.get_admins_to_remove_kb(filtered), parse_mode="HTML")
    except TelegramBadRequest: await callback.answer()

@admin_router.callback_query(F.data.startswith("adm_delete_"))
async def delete_admin_confirm(callback: CallbackQuery):
    if not await admin_db.is_super_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    user_role = await get_user_role(callback.from_user.id)
    target_admin = await admin_db.get_admin_by_id(uid)
    if target_admin and target_admin.get("role") == "boss" and user_role != "boss":
        await callback.answer("❌ Ви не можете видалити Босса!", show_alert=True)
        return
    await admin_db.remove_admin(uid)
    await callback.answer("Видалено!")
    await remove_admin_list(callback)

@admin_router.callback_query(F.data == "adm_back_to_manage")
async def back_to_team_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_super = await admin_db.is_super_admin(callback.from_user.id)
    await callback.message.edit_text("👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>", reply_markup=akb.get_admin_management_kb(is_super), parse_mode="HTML")
