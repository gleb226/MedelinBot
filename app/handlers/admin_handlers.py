from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards import admin_keyboards as akb
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

async def find_user_by_phone(phone: str):
    target = normalize_phone(phone)
    if not target:
        return None

    row = await user_db.get_user_by_phone(phone)
    if row:
        return {
            "user_id": row[0],
            "name": row[1],
            "username": row[2],
            "phone": row[3],
        }

    row = await booking_db.get_user_by_phone(phone)
    if row:
        return {
            "user_id": row[0],
            "name": row[1],
            "username": row[2],
            "phone": row[3],
        }
    return None

@admin_router.message(F.text == "🛰 АДМІН-ПАНЕЛЬ")
async def admin_panel_enter(message: Message):
    if not await admin_db.is_admin(message.from_user.id):
        return

    role = "admin"
    if await admin_db.is_god(message.from_user.id):
        role = "god"
    elif await admin_db.is_super_admin(message.from_user.id):
        role = "super"

    await message.answer(
        f"🔐 **ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ**\n"
        f"Ваша роль: **{role.upper()}**\n\n"
        "Виберіть розділ керування:",
        reply_markup=akb.main_admin_menu,
        parse_mode="Markdown"
    )

@admin_router.message(F.text == "📥 НОВІ ЗАПИТИ")
async def show_new_bookings(message: Message):
    if not await admin_db.is_admin(message.from_user.id):
        return

    if await admin_db.is_super_admin(message.from_user.id):
        bookings = await booking_db.get_new_bookings()
    else:
        locations = await admin_db.get_locations_for_admin(message.from_user.id)
        bookings = await booking_db.get_new_bookings_by_locations(locations)

    if not bookings:
        await message.answer("📭 **Наразі немає нових запитів.**", parse_mode="Markdown")
        return

    for b in bookings:
        text = (
            f"📥 **НОВИЙ ЗАПИТ №{b['id']}**\n\n"
            f"👤 **Клієнт:** {b['fullname']} (@{b['username']})\n"
            f"📞 **Телефон:** `{b['phone'] or 'не вказано'}`\n"
            f"🏛 **Заклад:** {LOCATIONS[b['location_id']]['name']}\n"
            f"🕔 **Час:** {b['date_time']}\n"
            f"👥 **Гостей:** {b['people_count']}\n"
            f"💬 **Побажання:** {b['wishes']}\n"
            f"🥘 **Замовлення:** {b['cart']}"
        )
        await message.answer(text, reply_markup=akb.get_booking_manage_kb(b['id']), parse_mode="Markdown")

@admin_router.message(F.text == "👥 КОМАНДА ТА ПРАВА")
async def manage_admins(message: Message):
    if not await admin_db.is_admin(message.from_user.id):
        return

    is_super = await admin_db.is_super_admin(message.from_user.id)
    is_god = await admin_db.is_god(message.from_user.id)
    accessible_locations = await admin_db.get_locations_for_admin(message.from_user.id)

    if not is_super and not accessible_locations:
        await message.answer("ℹ️ **У вас ще немає закладів для керування.**\nЗверніться до власника.", parse_mode="Markdown")
        return

    await message.answer(
        "👥 **КЕРУВАННЯ КОМАНДОЮ**\n\n"
        "Тут можна додавати співробітників або змінювати рівні доступу.",
        reply_markup=akb.get_admin_management_kb(is_super or is_god),
        parse_mode="Markdown"
    )

@admin_router.message(F.text == "🏠 ПОВЕРНУТИСЬ ДО ГОЛОВНОЇ")
async def back_to_main_from_admin(message: Message):
    from app.handlers.user_handlers import cmd_start
    await cmd_start(message)

@admin_router.callback_query(F.data == "adm_add_new")
async def start_add_admin(callback: CallbackQuery, state: FSMContext):
    if not await admin_db.is_admin(callback.from_user.id):
        return

    await callback.message.answer(
        "✳️ **ДОДАВАННЯ АДМІНІСТРАТОРА**\n\n"
        "Введіть один з варіантів:\n"
        "• числовий Telegram ID\n"
        "• @username\n"
        "• номер телефону (+380...)\n\n"
        "Кого хочете зробити адміном?",
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.adding_admin_id)
    await callback.answer()

@admin_router.message(AdminStates.adding_admin_id)
async def add_admin_id(message: Message, state: FSMContext):
    raw = message.text.strip()
    found_user = None
    new_id = None

    if raw.isdigit():
        new_id = int(raw)
    elif raw.startswith("@"):
        row = await user_db.get_user_by_username(raw.lstrip("@"))
        if row:
            new_id = row[0]
            found_user = {"user_id": row[0], "name": row[1], "username": row[2]}
    elif raw.startswith("+") and any(ch.isdigit() for ch in raw):
        found_user = await find_user_by_phone(raw)
        if found_user:
            new_id = found_user["user_id"]
    elif re.fullmatch(r"\d{9,15}", raw):
        phone_norm = "+" + raw
        found_user = await find_user_by_phone(phone_norm)
        if found_user:
            new_id = found_user["user_id"]

    if not new_id:
        await message.answer(
            "❌ **КОРИСТУВАЧА НЕ ЗНАЙДЕНО**\n\n"
            "Людина має хоч раз написати боту /start.\n"
            "Спробуйте знову або надішліть числовий ID:",
            parse_mode="Markdown"
        )
        return

    await state.update_data(new_admin_id=new_id)
    if found_user:
        await state.update_data(prefill_name=found_user.get("name"), prefill_username=found_user.get("username"))
        uname = f"@{found_user['username']}" if found_user.get("username") else (found_user.get("name") or "")
        await message.answer(f"✅ **ЗНАЙШОВ:** {uname} (ID: `{new_id}`)\nПідтвердіть або змініть відображуване ім'я:", parse_mode="Markdown")
    else:
        await message.answer("📝 **ВВЕДІТЬ ІМ'Я** для цього адміна:", parse_mode="Markdown")
    await state.set_state(AdminStates.adding_admin_name)

@admin_router.message(AdminStates.adding_admin_name)
async def add_admin_name(message: Message, state: FSMContext):
    data = await state.get_data()
    name_to_save = message.text if message.text else data.get("prefill_name")
    await state.update_data(new_admin_name=name_to_save)

    if await admin_db.is_super_admin(message.from_user.id):
        roles = "admin або super"
        if await admin_db.is_god(message.from_user.id):
            roles += " або god"
        await message.answer(f"🔧 **ВКАЖІТЬ РОЛЬ:**\nНапишіть: `{roles}`", parse_mode="Markdown")
        await state.set_state(AdminStates.adding_admin_role)
    else:
        await state.update_data(new_admin_role="admin")
        await ask_for_location(message, state)

@admin_router.message(AdminStates.adding_admin_role)
async def add_admin_role(message: Message, state: FSMContext):
    role = message.text.strip().lower()
    allowed_roles = ["admin", "super"]
    if await admin_db.is_god(message.from_user.id):
        allowed_roles.append("god")

    if role not in allowed_roles:
        await message.answer(f"❌ **ПОМИЛКА:** Доступні ролі: `{', '.join(allowed_roles)}`. Спробуйте ще раз:", parse_mode="Markdown")
        return

    await state.update_data(new_admin_role=role)

    if role in ("super", "god"):
        data = await state.get_data()
        await admin_db.add_admin(
            data["new_admin_id"],
            data.get("new_admin_name"),
            added_by=message.from_user.id,
            role=role,
            receive_notifications=0 if role == "god" else 1,
        )
        await message.answer(
            f"✅ **УСПІХ:** {data.get('new_admin_name')} (ID: `{data['new_admin_id']}`) тепер **{role.upper()}**.",
            reply_markup=akb.main_admin_menu,
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        await ask_for_location(message, state)

async def ask_for_location(message: Message, state: FSMContext):
    allowed_locations = (
        list(LOCATIONS.keys()) if await admin_db.is_super_admin(message.from_user.id) else await admin_db.get_locations_for_admin(message.from_user.id)
    )
    if not allowed_locations:
        await message.answer("ℹ️ **Немає доступних локацій для призначення.**", parse_mode="Markdown")
        await state.clear()
        return

    options = "\n".join([f"• `{loc_id}` — {LOCATIONS[loc_id]['name']}" for loc_id in allowed_locations])
    await message.answer(
        "🏢 **ОБЕРІТЬ ЛОКАЦІЮ**\n\n"
        "Введіть ID закладу зі списку:\n\n" + options,
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.adding_admin_location)

@admin_router.message(AdminStates.adding_admin_location)
async def add_admin_location(message: Message, state: FSMContext):
    loc_id = message.text.strip()
    allowed_locations = (
        list(LOCATIONS.keys()) if await admin_db.is_super_admin(message.from_user.id) else await admin_db.get_locations_for_admin(message.from_user.id)
    )
    if loc_id not in allowed_locations:
        await message.answer("❌ **ID НЕВІРНИЙ:** Введіть ID із запропонованого списку:", parse_mode="Markdown")
        return

    data = await state.get_data()
    await admin_db.add_admin(
        data["new_admin_id"],
        data.get("new_admin_name"),
        added_by=message.from_user.id,
        role=data.get("new_admin_role", "admin"),
        locations=[loc_id],
        receive_notifications=True,
    )

    await message.answer(
        f"✅ **ДОДАНО:** {data.get('new_admin_name')} (ID: `{data['new_admin_id']}`) тепер адмін закладу **{LOCATIONS[loc_id]['name']}**.",
        reply_markup=akb.main_admin_menu,
        parse_mode="Markdown"
    )
    await state.clear()

@admin_router.callback_query(F.data == "adm_list")
async def list_admins(callback: CallbackQuery):
    if not await admin_db.is_admin(callback.from_user.id):
        return

    current_user_id = callback.from_user.id
    is_god = await admin_db.is_god(current_user_id)

    if await admin_db.is_super_admin(current_user_id):
        rows = await admin_db._execute(
            """
            SELECT a.user_id, a.username, a.role, GROUP_CONCAT(l.location_id)
            FROM admins a
            LEFT JOIN admin_locations l ON a.user_id = l.user_id
            WHERE a.user_id != ?
            GROUP BY a.user_id
            """,
            (current_user_id,),
            fetchall=True
        )
    else:
        allowed = await admin_db.get_locations_for_admin(current_user_id)
        if not allowed:
            rows = []
        else:
            placeholders = ",".join(["?"] * len(allowed))
            rows = await admin_db._execute(
                f"""
                SELECT a.user_id, a.username, a.role, GROUP_CONCAT(l.location_id)
                FROM admins a
                JOIN admin_locations l ON a.user_id = l.user_id
                WHERE l.location_id IN ({placeholders}) AND a.role = 'admin' AND a.user_id != ?
                GROUP BY a.user_id
                """,
                (*allowed, current_user_id),
                fetchall=True
            )

    text = "📋 **СПИСОК АДМІНІСТРАТОРІВ**\n\n"
    if not rows:
        text += "— Поки що порожньо."
    else:
        for user_id, username, role, locs in rows:
            if not is_god and await admin_db.is_god(user_id):
                continue
            loc_names = ""
            if locs:
                loc_names = ", ".join([LOCATIONS[l]["name"] for l in locs.split(",") if l in LOCATIONS])
            text += f"👤 **{username or 'N/A'}** (`{user_id}`) \n   🏷 Role: `{role}`\n   📍 Locations: {loc_names or 'All'}\n\n"

    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@admin_router.callback_query(F.data == "adm_back_to_manage")
async def back_to_manage_admins(callback: CallbackQuery):
    if not await admin_db.is_admin(callback.from_user.id):
        return

    is_super = await admin_db.is_super_admin(callback.from_user.id)
    await callback.message.edit_text(
        "👥 **КЕРУВАННЯ ПЕРСОНАЛОМ**\n\n"
        "Тут можна додавати / забирати доступ до адмін-панелі.",
        reply_markup=akb.get_admin_management_kb(is_super),
        parse_mode="Markdown"
    )

@admin_router.callback_query(F.data == "adm_remove")
async def start_remove_admin(callback: CallbackQuery):
    if not await admin_db.is_admin(callback.from_user.id):
        return

    rows = []
    if await admin_db.is_god(callback.from_user.id):
        rows = await admin_db._execute("SELECT user_id, username, role FROM admins WHERE user_id != ?", (callback.from_user.id,), fetchall=True)
    elif await admin_db.is_super_admin(callback.from_user.id):
        rows = await admin_db._execute("SELECT user_id, username, role FROM admins WHERE role = 'admin' AND user_id != ?", (callback.from_user.id,), fetchall=True)

    if not rows:
        await callback.answer("ℹ️ Немає адмінів, яких ви можете видалити.")
        return

    await callback.message.edit_text(
        "🗑 **ВИДАЛЕННЯ ДОСТУПУ**\n\n"
        "Оберіть адміна для видалення:",
        reply_markup=akb.get_admins_to_remove_kb(rows),
        parse_mode="Markdown"
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("adm_delete_"))
async def confirm_remove_admin(callback: CallbackQuery):
    if not await admin_db.is_admin(callback.from_user.id):
        return

    user_id_to_remove = int(callback.data.split("_")[2])
    
    if user_id_to_remove == callback.from_user.id:
        await callback.answer("🚫 Ви не можете видалити самі себе.", show_alert=True)
        return

    current_admin_role = await admin_db._execute("SELECT role FROM admins WHERE user_id = ?", (callback.from_user.id,), fetchone=True)
    target_admin_role = await admin_db._execute("SELECT role FROM admins WHERE user_id = ?", (user_id_to_remove,), fetchone=True)
    
    if not current_admin_role or not target_admin_role:
        await callback.answer("❌ Помилка: користувача не знайдено.")
        return
        
    c_role = current_admin_role[0]
    t_role = target_admin_role[0]
    
    can_delete = False
    if c_role == "god":
        can_delete = True
    elif c_role == "super" and t_role == "admin":
        can_delete = True
        
    if not can_delete:
        await callback.answer("🚫 У вас недостатньо прав для видалення цього адміністратора.")
        return

    await admin_db.remove_admin(user_id_to_remove)
    await callback.answer("✅ Адміна видалено.")
    await callback.message.edit_text("✅ **АДМІНА ВИДАЛЕНО**", parse_mode="Markdown")

@admin_router.callback_query(F.data.startswith("adm_confirm_"))
async def confirm_booking(callback: CallbackQuery, bot: Bot):
    if not await admin_db.is_admin(callback.from_user.id):
        return

    booking_id = callback.data.split("_")[2]
    booking = await booking_db.get_booking_by_id(booking_id)

    if not booking:
        await callback.answer("❌ Бронювання не знайдено.")
        return

    if not await admin_db.has_location_access(callback.from_user.id, booking["location_id"]):
        await callback.answer("🚫 Немає доступу до цього закладу.")
        return

    await booking_db.update_status(booking_id, "confirmed")

    try:
        user_id = booking["user_id"]
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ **ВАШЕ БРОНЮВАННЯ №{booking_id} ПІДТВЕРДЖЕНО!**\n\n"
                "Будемо чекати на вас у «MEDELIN» ❤️"
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ **ПІДТВЕРДЖЕНО**",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await callback.answer("Бронювання підтверджено!")

@admin_router.callback_query(F.data.startswith("adm_cancel_"))
async def cancel_booking(callback: CallbackQuery, bot: Bot):
    if not await admin_db.is_admin(callback.from_user.id):
        return

    booking_id = callback.data.split("_")[2]
    booking = await booking_db.get_booking_by_id(booking_id)

    if not booking:
        await callback.answer("❌ Бронювання не знайдено.")
        return

    if not await admin_db.has_location_access(callback.from_user.id, booking["location_id"]):
        await callback.answer("🚫 Немає доступу до цього закладу.")
        return

    await booking_db.update_status(booking_id, "cancelled")

    try:
        user_id = booking["user_id"]
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ **БРОНЮВАННЯ №{booking_id} ВІДХИЛЕНО**\n\n"
                "На жаль, ми не можемо підтвердити ваше бронювання на цей час.\n"
                "Будь ласка, оберіть інший час або зателефонуйте нам."
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ **ВІДХИЛЕНО**",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await callback.answer("Бронювання відхилено.")
