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

from app.utils.phone_utils import normalize_phone

from app.utils.payment_refunds import refund_telegram_payment

from app.utils.message_utils import safe_edit_message

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
    # @lat,lon
    match1 = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if match1: return float(match1.group(1)), float(match1.group(2))
    # !3dLat!4dLon
    match2 = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
    if match2: return float(match2.group(1)), float(match2.group(2))
    # q=lat,lon
    match3 = re.search(r"q=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if match3: return float(match3.group(1)), float(match3.group(2))
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

    bookings = await orders_db.get_new_orders() if role in ("super", "boss") else await orders_db.get_new_orders_by_locations(await admin_db.get_locations_for_admin(message.from_user.id))

    if not bookings:

        await message.answer("📭 <b>Наразі немає нових запитів.</b>", parse_mode="HTML")

        return

    locations_dict = await location_db.get_locations_dict()

    for b in bookings:

        loc_name = locations_dict.get(b['location_id'], {}).get('name', '—')

        t = f"📥 <b>НОВИЙ ЗАПИТ</b>\n\n👤 <b>Клієнт:</b> {b['fullname']}\n📞 <code>{b['phone']}</code>\n🏛 <b>Заклад:</b> {loc_name}\n🕔 <b>Час:</b> {b['date_time']}\n👥 <b>Гостей:</b> {b['people_count']}\n🥘 <b>Замовлення:</b> {b['cart']}"

        await message.answer(t, reply_markup=akb.get_booking_manage_kb(b['id']), parse_mode="HTML")



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



@admin_router.callback_query(F.data == "menu_back")

async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    role = await get_user_role(callback.from_user.id)

    is_on_shift = await admin_db.is_on_shift(callback.from_user.id)

    await safe_edit_message(callback.message, f"🔐 <b>ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>", reply_markup=akb.get_main_admin_menu(is_on_shift, role), parse_mode="HTML")



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

    await callback.answer("Видалено!")

    await del_beans_start(callback)



@admin_router.callback_query(F.data == "locs_list")

async def list_locs(callback: CallbackQuery):

    locs = await location_db.get_all_locations()

    if not locs:

        await callback.answer("Порожньо.")

        return

    text = "📍 <b>ЛОКАЦІЇ:</b>\n\n" + "\n".join([f"▫️ {l['name']} ({l['address']})" for l in locs])

    await safe_edit_message(callback.message, text, reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")



@admin_router.callback_query(F.data == "locs_del")

async def del_locs_start(callback: CallbackQuery):

    locs = await location_db.get_all_locations()

    if not locs:

        await callback.answer("Порожньо.")

        return

    await safe_edit_message(callback.message, "🗑 Оберіть локацію для ВИДАЛЕННЯ:", reply_markup=akb.get_locations_list_kb(locs, "locs_del_it"), parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("locs_del_it_"))

async def del_loc_confirm(callback: CallbackQuery):

    lid = callback.data.replace("locs_del_it_", "")

    await location_db.delete_location(lid)

    await callback.answer("Видалено!")

    await del_locs_start(callback)



@admin_router.callback_query(F.data.startswith("adm_confirm_"))

async def confirm_order(callback: CallbackQuery, bot: Bot):

    oid = callback.data.split("_")[2]

    o = await orders_db.get_order_by_id(oid)

    if not o: return

    await orders_db.update_status(oid, "confirmed")

    if o['order_type'] in ("booking", "order_with_booking"):

        await active_bookings_db.add_active_booking(oid, o['user_id'], o['fullname'], o['phone'], o['location_id'], o['date_time'], o['people_count'], o['wishes'])

    else:

        await active_orders_db.add_active_order(oid, o['user_id'], o['fullname'], o['phone'], o['location_id'], o['cart'], o['order_type'], o.get('table_number'))

    try: await bot.send_message(o["user_id"], "✅ <b>ВАШЕ ЗАМОВЛЕННЯ ПІДТВЕРДЖЕНО!</b>", parse_mode="HTML")

    except: pass

    await safe_edit_message(callback.message, callback.message.text + "\n\n✅ <b>ПІДТВЕРДЖЕНО</b>", parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("ed_m_"))
async def edit_menu_field_start(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("ed_m_", "")
    await state.update_data(edit_field=field)
    fields_map = {
        "name": "нову назву",
        "price": "нову ціну",
        "description": "новий опис",
        "volume": "новий об'єм/вагу",
        "calories": "нову калорійність",
        "image_url": "нове фото (URL або відправте файл)"
    }
    await callback.message.answer(f"Введіть {fields_map.get(field, 'значення')}:")
    await state.set_state(MenuStates.edit_waiting_value)
    await callback.answer()

@admin_router.message(MenuStates.edit_waiting_value, F.photo | F.text)
async def edit_menu_value_save(message: Message, state: FSMContext):
    data = await state.get_data()
    item_id = data.get("edit_id")
    field = data.get("edit_field")
    
    if message.photo:
        val = message.photo[-1].file_id
    else:
        val = (message.text or "").strip()
        if val == "-": val = ""

    if item_id and field:
        await menu_db.update_item(item_id, {field: val})
        await message.answer(f"✅ Поле <b>{field}</b> оновлено!", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data.startswith("ed_b_"))
async def edit_bean_field_start(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("ed_b_", "")
    await state.update_data(edit_field=field)
    await callback.message.answer(f"Введіть нове значення для {field}:")
    await state.set_state(BeanStates.edit_value)
    await callback.answer()

@admin_router.message(BeanStates.edit_value, F.photo | F.text)
async def edit_bean_value_save(message: Message, state: FSMContext):
    data = await state.get_data()
    bean_id = data.get("edit_id")
    field = data.get("edit_field")
    
    if message.photo:
        val = message.photo[-1].file_id
    else:
        val = (message.text or "").strip()

    if bean_id and field:
        update_dict = {field: val}
        if field == "price_250":
            try:
                price_float = float(val.replace(",", "."))
                prices = coffee_beans_db.calculate_prices(price_float)
                update_dict = {
                    "price_250": prices["250"],
                    "price_500": prices["500"],
                    "price_1000": prices["1000"]
                }
            except ValueError:
                await message.answer("❌ Некоректна ціна.")
                await state.clear()
                return

        await coffee_beans_db.update_bean(bean_id, update_dict)
        await message.answer(f"✅ Зерно оновлено!", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")
    await state.clear()







@admin_router.callback_query(F.data == "admin_panel_back")

async def admin_panel_back(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    role = await get_user_role(callback.from_user.id)

    is_on_shift = await admin_db.is_on_shift(callback.from_user.id)

    await safe_edit_message(callback.message, f"🔐 <b>ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ</b>\nВаша роль: <b>{role.upper()}</b>", reply_markup=akb.get_main_admin_menu(is_on_shift, role), parse_mode="HTML")



@admin_router.callback_query(F.data == "adm_back_to_manage")

async def adm_back_to_manage(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    is_super = await admin_db.is_super_admin(callback.from_user.id)

    await safe_edit_message(callback.message, "👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>", reply_markup=akb.get_admin_management_kb(is_super), parse_mode="HTML")



@admin_router.callback_query(F.data == "menu_edit")

async def edit_menu_start(callback: CallbackQuery):

    cats = await menu_db.get_categories()

    await safe_edit_message(callback.message, "✏️ <b>Оберіть категорію:</b>", reply_markup=akb.get_category_selection_kb(cats, "m_edt_cat"), parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("m_edt_cat_"))

async def edit_menu_cat_sel(callback: CallbackQuery):

    cat_id = callback.data.replace("m_edt_cat_", "")

    cats = await menu_db.get_categories()

    from app.keyboards.user_keyboards import cat_key

    cat = next((c for c in cats if cat_key(c) == cat_id), None)

    if not cat:

        await callback.answer("Категорію не знайдено.")

        return

    items = await menu_db.get_items_by_category(cat)

    item_list = [(i[0], i[1]) for i in items]

    await safe_edit_message(callback.message, f"✏️ <b>{cat}:</b>", reply_markup=akb.get_items_in_category_kb(item_list, "m_edt_it", back_cb="menu_edit"), parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("m_edt_it_"))

async def edit_menu_select(callback: CallbackQuery, state: FSMContext):

    item_id = callback.data.replace("m_edt_it_", "")

    item = await menu_db.get_item_by_id(item_id)

    await state.update_data(edit_id=item_id)

    kb_edit = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="Назву", callback_data="ed_m_name"), InlineKeyboardButton(text="Ціну", callback_data="ed_m_price")],

        [InlineKeyboardButton(text="Опис", callback_data="ed_m_description"), InlineKeyboardButton(text="Об'єм", callback_data="ed_m_volume")],

        [InlineKeyboardButton(text="Калорії", callback_data="ed_m_calories"), InlineKeyboardButton(text="Фото", callback_data="ed_m_image_url")],

        [InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="menu_edit")]

    ])

    await safe_edit_message(callback.message, f"Що змінити у <b>{item[2]}</b>?", reply_markup=kb_edit, parse_mode="HTML")



@admin_router.callback_query(F.data == "beans_edit")
async def edit_beans_start(callback: CallbackQuery):
    beans = await coffee_beans_db.get_all_beans()
    if not beans:
        await callback.answer("Порожньо.")
        return
    await safe_edit_message(callback.message, "✏️ Оберіть зерно для РЕДАГУВАННЯ:", reply_markup=akb.get_beans_list_kb(beans, "beans_edt_it"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("beans_edt_it_"))
async def edit_bean_sel(callback: CallbackQuery, state: FSMContext):
    bid = callback.data.replace("beans_edt_it_", "")
    bean = await coffee_beans_db.get_bean_by_id(bid)
    await state.update_data(edit_id=bid)
    kb_edit = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назву", callback_data="ed_b_name"), InlineKeyboardButton(text="Ціну (250г)", callback_data="ed_b_price_250")],
        [InlineKeyboardButton(text="Опис", callback_data="ed_b_description"), InlineKeyboardButton(text="Сорт", callback_data="ed_b_sort")],
        [InlineKeyboardButton(text="Смак", callback_data="ed_b_taste"), InlineKeyboardButton(text="Обсмаження", callback_data="ed_b_roast")],
        [InlineKeyboardButton(text="Фото", callback_data="ed_b_image_url")],
        [InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="beans_edit")]
    ])
    await safe_edit_message(callback.message, f"Що змінити у <b>{bean['name']}</b>?", reply_markup=kb_edit, parse_mode="HTML")



@admin_router.callback_query(F.data == "beans_add")

async def add_bean_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(BeanStates.waiting_name)

    await callback.message.answer("✏️ Назва зерна:")

    await callback.answer()



@admin_router.message(BeanStates.waiting_name)

async def add_bean_name(message: Message, state: FSMContext):

    await state.update_data(name=message.text)

    await message.answer("💰 Ціна за 250г:")

    await state.set_state(BeanStates.waiting_price_250)



@admin_router.message(BeanStates.waiting_price_250)

async def add_bean_price(message: Message, state: FSMContext):

    try:

        val = float(message.text.replace(",", ".").strip())

        await state.update_data(price_250=val)

        await message.answer("📝 Опис:")

        await state.set_state(BeanStates.waiting_desc)

    except ValueError:

        await message.answer("❌ Введіть числове значення.")



@admin_router.message(BeanStates.waiting_desc)

async def add_bean_desc(message: Message, state: FSMContext):

    await state.update_data(description=message.text)

    await message.answer("🌱 Сорт:")

    await state.set_state(BeanStates.waiting_sort)



@admin_router.message(BeanStates.waiting_sort)

async def add_bean_sort(message: Message, state: FSMContext):

    await state.update_data(sort=message.text)

    await message.answer("✨ Смак:")

    await state.set_state(BeanStates.waiting_taste)



@admin_router.message(BeanStates.waiting_taste)

async def add_bean_taste(message: Message, state: FSMContext):

    await state.update_data(taste=message.text)

    await message.answer("🔥 Обсмаження:")

    await state.set_state(BeanStates.waiting_roast)



@admin_router.message(BeanStates.waiting_roast)

async def add_bean_roast(message: Message, state: FSMContext):

    await state.update_data(roast=message.text)

    await message.answer("🖼 Фото (URL) або '-':")

    await state.set_state(BeanStates.waiting_image)



@admin_router.message(BeanStates.waiting_image, F.photo | F.text)
async def add_bean_image(message: Message, state: FSMContext):
    if message.photo:
        img = message.photo[-1].file_id
    else:
        img = (message.text or "").strip()
        if img == "-": img = ""
    await state.update_data(image_url=img)
    data = await state.get_data()
    text = f"🔍 <b>ПЕРЕВІРКА ЗЕРНА:</b>\n\n☕️ {data['name']}\n💰 {data['price_250']}₴ (250г)\n🌱 {data['sort']}\n✨ {data['taste']}\n🔥 {data['roast']}\n📝 {data['description']}"
    if img and not img.startswith('http'):
        await message.answer_photo(photo=img, caption=text, reply_markup=akb.get_yes_no_kb("bean_save", "beans_back"), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=akb.get_yes_no_kb("bean_save", "beans_back"), parse_mode="HTML")



@admin_router.callback_query(F.data == "bean_save")

async def save_new_bean(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    await coffee_beans_db.add_bean(data['name'], data['price_250'], data['description'], data['sort'], data['taste'], data['roast'], data.get('image_url', ""))

    await safe_edit_message(callback.message, "✅ ЗЕРНО ДОДАНО!", reply_markup=akb.get_beans_manage_kb(), parse_mode="HTML")

    await state.clear()



@admin_router.callback_query(F.data == "locs_add")

async def add_loc_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(LocationStates.waiting_name)

    await callback.message.answer("✏️ Назва локації (напр. Medelin на Корятовича):")

    await callback.answer()



@admin_router.message(LocationStates.waiting_name)

async def add_loc_name(message: Message, state: FSMContext):

    await state.update_data(name=message.text)

    await message.answer("📍 Адреса:")

    await state.set_state(LocationStates.waiting_address)



@admin_router.message(LocationStates.waiting_address)

async def add_loc_address(message: Message, state: FSMContext):

    await state.update_data(address=message.text)

    await message.answer("⏰ Графік роботи (напр. Пн-Нд: 08:00-20:00):")

    await state.set_state(LocationStates.waiting_schedule)



@admin_router.message(LocationStates.waiting_schedule)

async def add_loc_schedule(message: Message, state: FSMContext):

    await state.update_data(schedule=message.text)

    await message.answer("📞 Телефон:")

    await state.set_state(LocationStates.waiting_phone)



@admin_router.message(LocationStates.waiting_phone)

async def add_loc_phone(message: Message, state: FSMContext):

    await state.update_data(phone=message.text)

    await message.answer("✉️ Email:")

    await state.set_state(LocationStates.waiting_email)



@admin_router.message(LocationStates.waiting_email)

async def add_loc_email(message: Message, state: FSMContext):

    await state.update_data(email=message.text)

    await message.answer("🗺 Посилання Google Maps:")

    await state.set_state(LocationStates.waiting_maps_url)



@admin_router.message(LocationStates.waiting_maps_url)

async def add_loc_maps(message: Message, state: FSMContext):

    await state.update_data(google_maps_url=message.text)

    await message.answer("🖼 Фото (URL) або відправте файл:")

    await state.set_state(LocationStates.waiting_image)



@admin_router.message(LocationStates.waiting_image, F.photo | F.text)
async def add_loc_image(message: Message, state: FSMContext):
    if message.photo:
        img = message.photo[-1].file_id
    else:
        img = (message.text or "").strip()
        if img == "-": img = ""
    await state.update_data(image_url=img)
    await message.answer("🪑 Кількість столів:")
    await state.set_state(LocationStates.waiting_max_tables)



@admin_router.message(LocationStates.waiting_max_tables)

async def add_loc_tables(message: Message, state: FSMContext):

    try:

        val = int(message.text)

        await state.update_data(max_tables=val)

        data = await state.get_data()

        text = f"🔍 <b>ПЕРЕВІРКА ЛОКАЦІЇ:</b>\n\n📍 {data['name']}\n🏛 {data['address']}\n⏰ {data['schedule']}\n📞 {data['phone']}\n🪑 Столів: {val}"

        if data.get('image_url') and not data['image_url'].startswith('http'):
            await message.answer_photo(photo=data['image_url'], caption=text, reply_markup=akb.get_yes_no_kb("loc_save", "locs_back"), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=akb.get_yes_no_kb("loc_save", "locs_back"), parse_mode="HTML")

    except ValueError:

        await message.answer("❌ Введіть ціле число.")



@admin_router.callback_query(F.data == "loc_save")

async def save_new_loc(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    coords = extract_coords_from_maps(data['google_maps_url'])

    await location_db.add_location(data['name'], data['address'], data['schedule'], data['phone'], data['email'], data['google_maps_url'], data['max_tables'], coordinates={"lat": coords[0], "lon": coords[1]} if coords else None, image_url=data.get('image_url', ""))

    await safe_edit_message(callback.message, "✅ ЛОКАЦІЮ ДОДАНО!", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")

    await state.clear()



@admin_router.callback_query(F.data == "locs_edit")
async def edit_loc_start(callback: CallbackQuery):
    locs = await location_db.get_all_locations()
    if not locs:
        await callback.answer("Порожньо.")
        return
    await safe_edit_message(callback.message, "✏️ Оберіть локацію для РЕДАГУВАННЯ:", reply_markup=akb.get_locations_list_kb(locs, "locs_edt_it"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("locs_edt_it_"))
async def edit_loc_sel(callback: CallbackQuery, state: FSMContext):
    lid = callback.data.replace("locs_edt_it_", "")
    loc = await location_db.get_location_by_id(lid)
    await state.update_data(edit_id=lid)
    kb_edit = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назву", callback_data="ed_l_name"), InlineKeyboardButton(text="Адресу", callback_data="ed_l_address")],
        [InlineKeyboardButton(text="Графік", callback_data="ed_l_schedule"), InlineKeyboardButton(text="Телефон", callback_data="ed_l_phone")],
        [InlineKeyboardButton(text="Email", callback_data="ed_l_email"), InlineKeyboardButton(text="Maps URL", callback_data="ed_l_google_maps_url")],
        [InlineKeyboardButton(text="Фото", callback_data="ed_l_image_url"), InlineKeyboardButton(text="Столи", callback_data="ed_l_max_tables")],
        [InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="locs_edit")]
    ])
    await safe_edit_message(callback.message, f"Що змінити у <b>{loc['name']}</b>?", reply_markup=kb_edit, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("ed_l_"))
async def edit_loc_field_start(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("ed_l_", "")
    await state.update_data(edit_field=field)
    await callback.message.answer(f"Введіть нове значення для {field}:")
    await state.set_state(LocationStates.edit_value)
    await callback.answer()

@admin_router.message(LocationStates.edit_value, F.photo | F.text)
async def edit_loc_value_save(message: Message, state: FSMContext):
    data = await state.get_data()
    lid = data.get("edit_id")
    field = data.get("edit_field")
    
    if message.photo:
        val = message.photo[-1].file_id
    else:
        val = (message.text or "").strip()

    if lid and field:
        update_data = {field: val}
        if field == "google_maps_url":
            coords = extract_coords_from_maps(val)
            if coords:
                update_data["coordinates"] = {"lat": coords[0], "lon": coords[1]}
        
        await location_db.update_location(lid, update_data)
        await message.answer(f"✅ Локацію оновлено!", reply_markup=akb.get_locations_manage_kb(), parse_mode="HTML")
    await state.clear()



@admin_router.callback_query(F.data == "soc_add")

async def add_soc_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(SocialStates.waiting_name)

    await callback.message.answer("✏️ Назва (напр. Instagram):")

    await callback.answer()



@admin_router.message(SocialStates.waiting_name)

async def add_soc_name(message: Message, state: FSMContext):

    await state.update_data(name=message.text)

    await message.answer("🔗 Посилання (URL):")

    await state.set_state(SocialStates.waiting_url)



@admin_router.message(SocialStates.waiting_url)

async def add_soc_url(message: Message, state: FSMContext):

    await state.update_data(url=message.text)

    data = await state.get_data()

    await message.answer(f"🔍 <b>ПЕРЕВІРКА:</b>\n\n📱 {data['name']}\n🔗 {data['url']}", reply_markup=akb.get_yes_no_kb("soc_save", "soc_back"), parse_mode="HTML")



@admin_router.callback_query(F.data == "soc_save")

async def save_new_soc(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    await socials_db.add_social(data['name'], data['url'])

    await safe_edit_message(callback.message, "✅ СОЦМЕРЕЖУ ДОДАНО!", reply_markup=akb.get_socials_manage_kb(), parse_mode="HTML")

    await state.clear()



@admin_router.callback_query(F.data == "soc_del")

async def del_soc_start(callback: CallbackQuery):

    socs = await socials_db.get_all_socials()

    await safe_edit_message(callback.message, "🗑 Оберіть для ВИДАЛЕННЯ:", reply_markup=akb.get_socials_list_kb(socs, "soc_del_it"), parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("soc_del_it_"))

async def del_soc_confirm(callback: CallbackQuery):

    sid = callback.data.replace("soc_del_it_", "")

    await socials_db.delete_social(sid)

    await callback.answer("Видалено!")

    await del_soc_start(callback)



@admin_router.callback_query(F.data == "soc_list")

async def list_socials(callback: CallbackQuery):

    socs = await socials_db.get_all_socials()

    text = "📱 <b>СОЦМЕРЕЖІ:</b>\n\n" + "\n".join([f"▫️ <a href='{s['url']}'>{s['name']}</a>" for s in socs])

    await safe_edit_message(callback.message, text, reply_markup=akb.get_socials_manage_kb(), parse_mode="HTML", disable_web_page_preview=True)



@admin_router.callback_query(F.data == "soc_back")

async def back_to_soc_manage(callback: CallbackQuery, state: FSMContext):

    await state.clear()

    await safe_edit_message(callback.message, "📱 <b>КЕРУВАННЯ СОЦМЕРЕЖАМИ</b>", reply_markup=akb.get_socials_manage_kb(), parse_mode="HTML")



@admin_router.callback_query(F.data == "menu_cats")

async def list_categories(callback: CallbackQuery):

    cats = await menu_db.get_categories()

    text = "📚 <b>КАТЕГОРІЇ:</b>\n" + "\n".join([f"▫️ {akb.get_cat_with_emoji(c)}" for c in cats])

    await safe_edit_message(callback.message, text, reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")



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

    if not cat:

        await callback.answer("Помилка.")

        return

    await state.update_data(category=cat)

    await safe_edit_message(callback.message, f"📂 Категорія: <b>{cat}</b>\n✏️ Назва позиції:", parse_mode="HTML")

    await state.set_state(MenuStates.waiting_name)



@admin_router.message(MenuStates.waiting_new_category)

async def add_item_new_cat(message: Message, state: FSMContext):

    await state.update_data(category=message.text)

    await message.answer(f"📂 Нова категорія: <b>{message.text}</b>\n✏️ Назва позиції:", parse_mode="HTML")

    await state.set_state(MenuStates.waiting_name)



@admin_router.message(MenuStates.waiting_name)

async def add_item_name(message: Message, state: FSMContext):

    await state.update_data(name=message.text)

    await message.answer("💰 Ціна:")

    await state.set_state(MenuStates.waiting_price)



@admin_router.message(MenuStates.waiting_price)

async def add_item_price(message: Message, state: FSMContext):

    await state.update_data(price=message.text)

    await message.answer("📝 Опис:")

    await state.set_state(MenuStates.waiting_desc)



@admin_router.message(MenuStates.waiting_desc)

async def add_item_desc(message: Message, state: FSMContext):

    await state.update_data(description=message.text)

    await message.answer("📦 Об'єм/Вага:")

    await state.set_state(MenuStates.waiting_volume)



@admin_router.message(MenuStates.waiting_volume)

async def add_item_volume(message: Message, state: FSMContext):

    await state.update_data(volume=message.text)

    await message.answer("🔥 Калорії:")

    await state.set_state(MenuStates.waiting_calories)



@admin_router.message(MenuStates.waiting_calories)

async def add_item_calories(message: Message, state: FSMContext):

    await state.update_data(calories=message.text)

    await message.answer("🖼 Фото (URL) або '-':")

    await state.set_state(MenuStates.waiting_image)



@admin_router.message(MenuStates.waiting_image, F.photo | F.text)
async def add_item_image(message: Message, state: FSMContext):
    if message.photo:
        img = message.photo[-1].file_id
    else:
        img = (message.text or "").strip()
        if img == "-": img = ""
    await state.update_data(image_url=img)
    data = await state.get_data()
    text = f"🔍 <b>ПЕРЕВІРКА ПОЗИЦІЇ:</b>\n\n📂 {data['category']}\n✨ {data['name']}\n💰 {data['price']}\n📦 {data['volume']}\n🔥 {data['calories']}\n📝 {data['description']}"
    if img and not img.startswith('http'):
        await message.answer_photo(photo=img, caption=text, reply_markup=akb.get_yes_no_kb("menu_save_item", "menu_back"), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=akb.get_yes_no_kb("menu_save_item", "menu_back"), parse_mode="HTML")



@admin_router.callback_query(F.data == "menu_save_item")

async def save_new_item(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    await menu_db.add_item(data['category'], data['name'], data['price'], data['description'], data['volume'], data['calories'], data.get('image_url', ""))

    await safe_edit_message(callback.message, "✅ ПОЗИЦІЮ ДОДАНО!", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

    await state.clear()



@admin_router.callback_query(F.data == "menu_del")

async def del_item_start(callback: CallbackQuery, state: FSMContext):

    cats = await menu_db.get_categories()

    await safe_edit_message(callback.message, "🗑 Оберіть категорію:", reply_markup=akb.get_category_selection_kb(cats, "m_del_cat"), parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("m_del_cat_"))

async def del_item_cat_sel(callback: CallbackQuery):

    cat_id = callback.data.replace("m_del_cat_", "")

    cats = await menu_db.get_categories()

    from app.keyboards.user_keyboards import cat_key

    cat = next((c for c in cats if cat_key(c) == cat_id), None)

    if not cat:

        await callback.answer("Помилка.")

        return

    items = await menu_db.get_items_by_category(cat)

    item_list = [(i[0], i[1]) for i in items]

    if not item_list:

        await callback.answer("Порожньо.")

        return

    await safe_edit_message(callback.message, f"🗑 {cat}\nОберіть для видалення:", reply_markup=akb.get_items_in_category_kb(item_list, "m_del_it", back_cb="menu_del"), parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("m_del_it_"))

async def del_item_confirm(callback: CallbackQuery):

    item_id = callback.data.replace("m_del_it_", "")

    item = await menu_db.get_item_by_id(item_id)

    if not item:

        await callback.answer("Помилка.")

        return

    await menu_db.delete_item(item_id)

    await callback.answer(f"Видалено: {item[2]}")

                                                    

    cats = await menu_db.get_categories()

    from app.keyboards.user_keyboards import cat_key

    cat = next((c for c in cats if c == item[1]), None)

    if cat:

        items = await menu_db.get_items_by_category(cat)

        item_list = [(i[0], i[1]) for i in items]

        if item_list:

            await safe_edit_message(callback.message, f"🗑 {cat}\nОберіть для видалення:", reply_markup=akb.get_items_in_category_kb(item_list, "m_del_it", back_cb="menu_del"), parse_mode="HTML")

            return

    await del_item_start(callback, None)







@admin_router.callback_query(F.data == "adm_add_new")

async def add_admin_start(callback: CallbackQuery, state: FSMContext):

    await state.set_state(AdminStates.adding_admin_id)

    await callback.message.answer("👤 Введіть @username або ID:")

    await callback.answer()



@admin_router.message(AdminStates.adding_admin_id)

async def add_admin_id(message: Message, state: FSMContext):

    await state.update_data(new_admin_id=message.text)

    await message.answer("👤 Ім'я працівника:")

    await state.set_state(AdminStates.adding_admin_name)



@admin_router.message(AdminStates.adding_admin_name)

async def add_admin_name(message: Message, state: FSMContext):

    await state.update_data(new_admin_name=message.text)

    await message.answer("🎭 Роль (admin, super, boss):")

    await state.set_state(AdminStates.adding_admin_role)



@admin_router.message(AdminStates.adding_admin_role)

async def add_admin_role(message: Message, state: FSMContext):

    await state.update_data(new_admin_role=message.text.lower())

    await state.set_state(AdminStates.adding_admin_location)

    locs = await location_db.get_all_locations()

    loc_list = "\n".join([f"<code>{str(l['_id'])}</code> - {l['name']}" for l in locs])

    await message.answer(f"🏛 Введіть ID закладу:\n\n{loc_list}", parse_mode="HTML")



@admin_router.message(AdminStates.adding_admin_location)

async def add_admin_loc(message: Message, state: FSMContext):

    await state.update_data(new_admin_locations=[message.text.strip()])

    data = await state.get_data()

    await message.answer(f"✅ ПІДТВЕРДІТЬ: {data['new_admin_name']} ({data['new_admin_role']})", reply_markup=akb.get_yes_no_kb("adm_save_final", "admin_panel_back"), parse_mode="HTML")

    await state.set_state(AdminStates.adding_admin_confirm)



@admin_router.callback_query(F.data == "adm_save_final", AdminStates.adding_admin_confirm)

async def add_admin_final(callback: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    await admin_db.add_admin(data['new_admin_id'], "", data['new_admin_name'], callback.from_user.id, data['new_admin_role'], locations=data['new_admin_locations'])

    await safe_edit_message(callback.message, "✅ Працівника додано!")

    await state.clear()



@admin_router.callback_query(F.data == "adm_list")

async def list_admins(callback: CallbackQuery):

    admins = await admin_db.get_admins_with_locations()

    text = "👥 КОМАНДА:\n\n" + "\n".join([f"▫️ {a[2]} ({a[3]})" for a in admins])

    await safe_edit_message(callback.message, text, reply_markup=akb.get_admin_management_kb(True), parse_mode="HTML")



@admin_router.callback_query(F.data == "adm_remove")

async def remove_admin_start(callback: CallbackQuery):

    admins = await admin_db.get_admins_with_locations()

    await safe_edit_message(callback.message, "🗑 Виберіть для видалення:", reply_markup=akb.get_admins_to_remove_kb(admins), parse_mode="HTML")



@admin_router.callback_query(F.data.startswith("adm_delete_"))

async def remove_admin_confirm(callback: CallbackQuery):

    await admin_db.remove_admin(callback.data.replace("adm_delete_", ""))

    await callback.answer("Видалено!")

    await remove_admin_start(callback)



