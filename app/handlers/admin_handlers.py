from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards import admin_keyboards as akb
from app.keyboards import user_keyboards as kb
from app.common.config import LOCATIONS, GOD_IDS
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
from app.databases.user_database import user_db
from app.databases.menu_database import menu_db
from app.utils.phone_utils import normalize_phone
from app.utils.payment_refunds import refund_telegram_payment
import re

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
    waiting_desc = State()
    waiting_volume = State()
    waiting_calories = State()
    waiting_confirm = State()
    edit_select_item = State()
    edit_waiting_field = State()
    edit_waiting_value = State()

async def get_user_role(user_id):
    if await admin_db.is_god(user_id): return "god"
    if await admin_db.is_super_admin(user_id): return "super"
    return "admin"

@admin_router.message(F.text == "📋 МЕНЮ")
async def manage_menu(message: Message):
    if not await admin_db.is_admin(message.from_user.id): return
    if await get_user_role(message.from_user.id) != "god":
        await message.answer("❌ Доступ до керування меню має тільки <b>БОГ</b>.", parse_mode="HTML")
        return
    await message.answer("📋 <b>КЕРУВАННЯ МЕНЮ</b>\nОберіть дію:", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_back")
async def back_to_menu_manage(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "god": return
    await callback.message.edit_text("📋 <b>КЕРУВАННЯ МЕНЮ</b>\nОберіть дію:", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_cats")
async def list_categories(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "god": return
    cats = await menu_db.get_categories()
    text = "📚 <b>СПИСОК КАТЕГОРІЙ:</b>\n" + "\n".join(f"▫️ {akb.get_cat_with_emoji(c)}" for c in cats)
    await callback.message.edit_text(text, reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_add")
async def add_item_start(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "god": return
    cats = await menu_db.get_categories()
    await callback.message.edit_text("📂 <b>Оберіть категорію або створіть нову:</b>", reply_markup=akb.get_category_selection_kb(cats, "m_add_cat", include_new=True), parse_mode="HTML")
    await state.set_state(MenuStates.waiting_category)

@admin_router.callback_query(F.data.startswith("m_add_cat_"), MenuStates.waiting_category)
async def add_item_cat(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "god": return
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
    if await get_user_role(message.from_user.id) != "god": return
    await state.update_data(category=message.text)
    await message.answer(f"📂 Категорія: <b>{message.text}</b>\n\n✏️ Введіть назву позиції:", parse_mode="HTML")
    await state.set_state(MenuStates.waiting_name)

@admin_router.message(MenuStates.waiting_name)
async def add_item_name(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "god": return
    await state.update_data(name=message.text)
    await message.answer("💰 Введіть ціну (наприклад: 50 або 50 ₴):")
    await state.set_state(MenuStates.waiting_price)

@admin_router.message(MenuStates.waiting_price)
async def add_item_price(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "god": return
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
    if await get_user_role(message.from_user.id) != "god": return
    desc = message.text if message.text != "-" else ""
    await state.update_data(description=desc)
    await message.answer("⚖️ Введіть об'єм/вагу (наприклад: 250 мл або 150 г) або '-' щоб пропустити:")
    await state.set_state(MenuStates.waiting_volume)

@admin_router.message(MenuStates.waiting_volume)
async def add_item_volume(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "god": return
    volume = message.text if message.text != "-" else ""
    await state.update_data(volume=volume)
    await message.answer("🔋 Введіть енергетичну цінність (ккал) або '-' щоб пропустити:")
    await state.set_state(MenuStates.waiting_calories)

@admin_router.message(MenuStates.waiting_calories)
async def add_item_calories(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "god": return
    calories = message.text if message.text != "-" else ""
    await state.update_data(calories=calories)
    data = await state.get_data()
    text = (f"🔍 <b>ПЕРЕВІРКА:</b>\n\n📂 {data['category']}\n▫️ {data['name']}\n💰 {data['price']}\n📝 {data['description'] or 'без опису'}\n⚖️ {data['volume'] or 'не вказано'}\n🔋 {data['calories'] or 'не вказано'}")
    await message.answer(text, reply_markup=akb.get_yes_no_kb("menu_save", "menu_back"), parse_mode="HTML")

@admin_router.callback_query(F.data == "menu_save")
async def save_new_item(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "god": return
    data = await state.get_data()
    await menu_db.add_item(data['category'], data['name'], data['price'], data['description'], data['volume'], data['calories'])
    await callback.message.edit_text("✅ <b>ПОЗИЦІЮ ДОДАНО!</b>", reply_markup=akb.get_menu_manage_kb(), parse_mode="HTML")
    await state.clear()

@admin_router.callback_query(F.data == "menu_del")
async def del_item_start(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "god": return
    cats = await menu_db.get_categories()
    await callback.message.edit_text("🗑 <b>Видалення:</b> Оберіть категорію:", reply_markup=akb.get_category_selection_kb(cats, "m_del_cat"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("m_del_cat_"))
async def del_item_cat_sel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "god": return
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
    if await get_user_role(callback.from_user.id) != "god": return
    item_id = callback.data.replace("m_del_it_", "")
    item = await menu_db.get_item_by_id(item_id)
    if not item: return
    await menu_db.delete_item(item_id)
    await callback.answer(f"🗑 Видалено: {item[2]}")
    await del_item_start(callback, None)

@admin_router.callback_query(F.data == "menu_edit")
async def edit_item_start(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "god": return
    cats = await menu_db.get_categories()
    await callback.message.edit_text("✏️ <b>Редагування:</b> Оберіть категорію:", reply_markup=akb.get_category_selection_kb(cats, "m_edt_cat"), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("m_edt_cat_"))
async def edit_item_cat_sel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "god": return
    try:
        idx = int(callback.data.replace("m_edt_cat_", ""))
        cats = await menu_db.get_categories()
        cat = cats[idx]
        items = await menu_db.get_items_by_category(cat)
        item_list = [(i[0], i[1]) for i in items]
        await callback.message.edit_text(f"✏️ Категорія: <b>{cat}</b>\nОберіть позицію:", reply_markup=akb.get_items_in_category_kb(item_list, "m_edt_it"), parse_mode="HTML")
    except: pass

@admin_router.callback_query(F.data.startswith("m_edt_it_"), State(None))
async def edit_item_select(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "god": return
    item_id = callback.data.replace("m_edt_it_", "")
    item = await menu_db.get_item_by_id(item_id)
    if not item: return
    await state.update_data(edit_id=item_id)
    text = (f"✏️ <b>РЕДАГУВАННЯ:</b>\n▫️ {item[2]}\n💰 {item[3]}\n📝 {item[4] or '—'}\n⚖️ {item[5] or '—'}\n🔋 {item[6] or '—'}")
    kb_edit = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назву", callback_data="edt_f_name"), InlineKeyboardButton(text="Ціну", callback_data="edt_f_price")],
        [InlineKeyboardButton(text="Опис", callback_data="edt_f_desc"), InlineKeyboardButton(text="Об'єм", callback_data="edt_f_vol")],
        [InlineKeyboardButton(text="Калорії", callback_data="edt_f_cal")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_edit")]
    ])
    await callback.message.edit_text(text, reply_markup=kb_edit, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("edt_f_"))
async def edit_field_start(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "god": return
    field = callback.data.replace("edt_f_", "")
    await state.update_data(edit_field=field)
    await callback.message.answer("✏️ Введіть нове значення:")
    await state.set_state(MenuStates.edit_waiting_value)

@admin_router.message(MenuStates.edit_waiting_value)
async def edit_field_save(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "god": return
    data = await state.get_data()
    item_id = data['edit_id']
    field_map = {"name": "name", "price": "price", "desc": "description", "vol": "volume", "cal": "calories"}
    db_field = field_map.get(data['edit_field'])
    if db_field:
        await menu_db.update_item(item_id, {db_field: message.text})
        await message.answer("✅ Зміни збережено!")
    await state.clear()
    await manage_menu(message)

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

@admin_router.message(F.text == "🆕 НОВІ ЗАПИТИ")
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
    await message.answer("👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>", reply_markup=akb.get_admin_management_kb(role in ("super", "god", "admin")), parse_mode="HTML")

@admin_router.message(F.text == "↩️ ПОВЕРНУТИСЬ ДО ГОЛОВНОЇ")
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
    userdata = b or {}
    pay_id = userdata.get("payment_id")
    provider_id = userdata.get("provider_payment_id")
    if pay_id:
        refunded, refund_error = await refund_telegram_payment(bot, pay_id, provider_id)
        if refunded:
            refund_msg = f"\\n\\n💳 <b>ОПЛАЧЕНО.</b>\\nГроші повернено автоматично."
            await booking_db.set_refund_status(bid, "refunded")
            try: await bot.send_message(userdata.get("user_id"), "❌ <b>ЗАМОВЛЕННЯ ВІДХИЛЕНО.</b>\\nГроші повернено автоматично.", parse_mode="HTML")
            except: pass
        else:
            refund_msg = f"\\n\\n⚠️ <b>Повернення не вдалося:</b> {refund_error}"
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
    await message.answer("🎭 <b>ВВЕДІТЬ РОЛЬ</b> (admin, super, god):", parse_mode="HTML")

@admin_router.message(AdminStates.adding_admin_role)
async def add_admin_role_text(message: Message, state: FSMContext):
    valid_roles = ["admin", "super", "god"]
    role_input = message.text.strip().lower()
    if role_input not in valid_roles:
        await message.answer("⚠️ Невірна роль. Введіть: <b>admin</b>, <b>super</b> або <b>god</b>", parse_mode="HTML")
        return
    
    await state.update_data(new_admin_role=role_input)
    if role_input == "admin":
        await state.set_state(AdminStates.adding_admin_location)
        loc_list = "\n".join([f"<b>{k}</b> — {v['name']}" for k, v in LOCATIONS.items()])
        await message.answer(f"🏛 <b>ВВЕДІТЬ НОМЕР ЗАКЛАДУ:</b>\n\n{loc_list}", parse_mode="HTML")
    else:
        await state.update_data(new_admin_locations=list(LOCATIONS.keys()))
        await add_admin_show_summary(message, state)

@admin_router.message(AdminStates.adding_admin_location)
async def add_admin_location_text(message: Message, state: FSMContext):
    loc_id = message.text.strip()
    if loc_id not in LOCATIONS:
        await message.answer("⚠️ Невірний номер. Оберіть номер зі списку вище:")
        return
    
    await state.update_data(new_admin_locations=[loc_id])
    await add_admin_show_summary(message, state)

async def add_admin_show_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    role_names = {"admin": "Адмін", "super": "Суперадмін", "god": "Бог"}
    locs = ", ".join([LOCATIONS[l]['name'] for l in data['new_admin_locations']])
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

@admin_router.callback_query(F.data == "adm_list")
async def manage_team_list(callback: CallbackQuery):
    if not await admin_db.is_admin(callback.from_user.id): return
    admins = await admin_db.get_admins_basic()
    text = "👥 <b>СПИСОК КОМАНДИ:</b>\n\n" + "\n".join([f"▫️ {dname or uname or uid} — <b>{role.upper()}</b>" for uid, uname, dname, role in admins])
    await callback.message.edit_text(text, reply_markup=akb.get_admin_management_kb(await admin_db.is_super_admin(callback.from_user.id)), parse_mode="HTML")

@admin_router.callback_query(F.data == "adm_remove")
async def remove_admin_list(callback: CallbackQuery):
    if not await admin_db.is_super_admin(callback.from_user.id): return
    admins = await admin_db.get_admins_basic()
    is_god = await admin_db.is_god(callback.from_user.id)
    filtered = [a for a in admins if a[0] != callback.from_user.id and (a[3] != "god" or is_god)]
    if not filtered: await callback.answer("Немає кого видаляти."); return
    await callback.message.edit_text("🗑 <b>Оберіть для видалення:</b>", reply_markup=akb.get_admins_to_remove_kb(filtered), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_delete_"))
async def delete_admin_confirm(callback: CallbackQuery):
    if not await admin_db.is_super_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2]); await admin_db.remove_admin(uid)
    await callback.answer("Видалено!"); await remove_admin_list(callback)

@admin_router.callback_query(F.data == "adm_back_to_manage")
async def back_to_team_manage(callback: CallbackQuery, state: FSMContext):
    await state.clear(); role = await get_user_role(callback.from_user.id)
    await callback.message.edit_text("👥 <b>КЕРУВАННЯ КОМАНДОЮ</b>", reply_markup=akb.get_admin_management_kb(role in ("super", "god", "admin")), parse_mode="HTML")
