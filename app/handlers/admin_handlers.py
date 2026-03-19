from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards import admin_keyboards as akb
from app.common.config import LOCATIONS, ADMINS_DB_PATH
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
from app.databases.user_database import user_db
import re
import sqlite3


admin_router = Router()


class AdminStates(StatesGroup):
    adding_admin_id = State()
    adding_admin_name = State()
    adding_admin_role = State()
    adding_admin_location = State()


def normalize_phone_digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def find_user_by_phone(phone: str):
    """
    Try to resolve user_id by phone from users.db, then bookings.db.
    Returns dict with keys: user_id, name, username, phone or None.
    """
    target = normalize_phone_digits(phone)
    if not target:
        return None

    # 1) users table
    row = user_db.get_user_by_phone(phone)
    if row:
        return {
            "user_id": row[0],
            "name": row[1],
            "username": row[2],
            "phone": row[3],
        }

    # 2) bookings table (latest match)
    conn = sqlite3.connect(booking_db.db_name)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    for r in cur.execute("SELECT * FROM bookings ORDER BY timestamp DESC"):
        if normalize_phone_digits(r["phone"]) == target:
            return {
                "user_id": r["user_id"],
                "name": r["fullname"],
                "username": r["username"],
                "phone": r["phone"],
            }
    return None


@admin_router.message(F.text == "🛰 АДМІН-ПАНЕЛЬ")
async def admin_panel_enter(message: Message):
    if not admin_db.is_admin(message.from_user.id):
        return

    await message.answer(
        "🔐 ВХІД В АДМІНІСТРАТИВНУ ПАНЕЛЬ\n"
        "═══════════════════\n"
        "Виберіть розділ керування:",
        reply_markup=akb.main_admin_menu,
    )


@admin_router.message(F.text == "📥 НОВІ БРОНЮВАННЯ")
async def show_new_bookings(message: Message):
    if not admin_db.is_admin(message.from_user.id):
        return

    if admin_db.is_super_admin(message.from_user.id):
        bookings = booking_db.get_new_bookings()
    else:
        locations = admin_db.get_locations_for_admin(message.from_user.id)
        bookings = booking_db.get_new_bookings_by_locations(locations)

    if not bookings:
        await message.answer("📭 Наразі немає нових бронювань.")
        return

    for b in bookings:
        text = (
            f"📥 БРОНЮВАННЯ №{b['id']}\n"
            f"🙋 Клієнт: {b['fullname']} (@{b['username']})\n"
            f"📞 Телефон: {b['phone'] or 'не вказано'}\n"
            f"🏢 Заклад: {LOCATIONS[b['location_id']]['name']}\n"
            f"🕔 Час: {b['date_time']}\n"
            f"👥 Гостей: {b['people_count']}\n"
            f"💬 Побажання: {b['wishes']}\n"
            f"🍽 Замовлення: {b['cart']}"
        )
        await message.answer(text, reply_markup=akb.get_booking_manage_kb(b['id']))


@admin_router.message(F.text == "👥 КЕРУВАННЯ АДМІНАМИ")
async def manage_admins(message: Message):
    if not admin_db.is_admin(message.from_user.id):
        return

    is_super = admin_db.is_super_admin(message.from_user.id)
    accessible_locations = admin_db.get_locations_for_admin(message.from_user.id)

    if not is_super and not accessible_locations:
        await message.answer("ℹ️ У вас ще немає закладів для керування. Зверніться до супер-адміна.")
        return

    await message.answer(
        "👥 КЕРУВАННЯ ПЕРСОНАЛОМ\n"
        "═══════════════════\n"
        "Тут можна додавати / забирати доступ до адмін-панелі.",
        reply_markup=akb.get_admin_management_kb(is_super),
    )


@admin_router.callback_query(F.data == "adm_add_new")
async def start_add_admin(callback: CallbackQuery, state: FSMContext):
    if not admin_db.is_admin(callback.from_user.id):
        return

    await callback.message.answer(
        "✳️ Введіть один з варіантів:\n"
        "• числовий Telegram ID\n"
        "• @username\n"
        "• номер телефону у форматі +380...\n"
        "кого хочете зробити адміном:"
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
        found_user = user_db.get_user_by_username(raw.lstrip("@"))
        if found_user:
            new_id = found_user[0]
    elif raw.startswith("+") and any(ch.isdigit() for ch in raw):
        found_user = find_user_by_phone(raw)
        if found_user:
            new_id = found_user["user_id"]
    elif re.fullmatch(r"\d{9,15}", raw):  # bare phone digits like 380501405135
        phone_norm = "+" + raw
        found_user = find_user_by_phone(phone_norm)
        if found_user:
            new_id = found_user["user_id"]

    if not new_id:
        await message.answer(
            "❌ Не знайшов користувача за цим ID/ніком/телефоном.\n"
            "Щоб додати по телефону, ця людина має хоч раз написати боту /start або зробити бронювання з цим номером.\n"
            "Тоді спробуйте знову або надішліть числовий Telegram ID:"
        )
        return

    await state.update_data(new_admin_id=new_id)
    # якщо знайшли в базі — підставимо ім'я та username
    if found_user:
        await state.update_data(prefill_name=found_user.get("name"), prefill_username=found_user.get("username"))
        uname = f"@{found_user['username']}" if found_user.get("username") else (found_user.get("name") or "")
        await message.answer(f"✅ Знайшов {uname} (ID: {new_id}). Підтвердіть/змінiть відображуване ім'я:")
    else:
        await message.answer("📝 Введіть ім'я/псевдонім для цього адміна:")
    await state.set_state(AdminStates.adding_admin_name)


@admin_router.message(AdminStates.adding_admin_name)
async def add_admin_name(message: Message, state: FSMContext):
    data = await state.get_data()
    name_to_save = message.text if message.text else data.get("prefill_name")
    await state.update_data(new_admin_name=name_to_save)

    if admin_db.is_super_admin(message.from_user.id):
        await message.answer("🔧 Вкажіть роль: напишіть `admin` або `super`.")
        await state.set_state(AdminStates.adding_admin_role)
    else:
        await state.update_data(new_admin_role="admin")
        await ask_for_location(message, state)


@admin_router.message(AdminStates.adding_admin_role)
async def add_admin_role(message: Message, state: FSMContext):
    role = message.text.strip().lower()
    if role not in ("admin", "super"):
        await message.answer("❌ Роль має бути `admin` або `super`. Спробуйте ще раз:")
        return

    await state.update_data(new_admin_role=role)

    if role == "super":
        data = await state.get_data()
        admin_db.add_admin(
            data["new_admin_id"],
            data.get("new_admin_name"),
            added_by=message.from_user.id,
            role="super",
            receive_notifications=0,
        )
        await message.answer(
            f"✅ {data.get('new_admin_name')} (ID: {data['new_admin_id']}) тепер СУПЕР-АДМІН (без сповіщень).",
            reply_markup=akb.main_admin_menu,
        )
        await state.clear()
    else:
        await ask_for_location(message, state)


async def ask_for_location(message: Message, state: FSMContext):
    allowed_locations = (
        list(LOCATIONS.keys()) if admin_db.is_super_admin(message.from_user.id) else admin_db.get_locations_for_admin(message.from_user.id)
    )
    if not allowed_locations:
        await message.answer("ℹ️ Немає доступних локацій для призначення.")
        await state.clear()
        return

    options = "\n".join([f"{loc_id} — {LOCATIONS[loc_id]['name']}" for loc_id in allowed_locations])
    await message.answer(
        "🏢 Оберіть ID закладу для цього адміна та надішліть його числом:\n" + options
    )
    await state.set_state(AdminStates.adding_admin_location)


@admin_router.message(AdminStates.adding_admin_location)
async def add_admin_location(message: Message, state: FSMContext):
    loc_id = message.text.strip()
    allowed_locations = (
        list(LOCATIONS.keys()) if admin_db.is_super_admin(message.from_user.id) else admin_db.get_locations_for_admin(message.from_user.id)
    )
    if loc_id not in allowed_locations:
        await message.answer("❌ Немає доступу до цієї локації. Введіть ID із списку:")
        return

    data = await state.get_data()
    admin_db.add_admin(
        data["new_admin_id"],
        data.get("new_admin_name"),
        added_by=message.from_user.id,
        role=data.get("new_admin_role", "admin"),
        locations=[loc_id],
        receive_notifications=True,
    )

    await message.answer(
        f"✅ {data.get('new_admin_name')} (ID: {data['new_admin_id']}) тепер адмін закладу {LOCATIONS[loc_id]['name']}.",
        reply_markup=akb.main_admin_menu,
    )
    await state.clear()


@admin_router.callback_query(F.data == "adm_list")
async def list_admins(callback: CallbackQuery):
    if not admin_db.is_admin(callback.from_user.id):
        return

    import sqlite3

    conn = sqlite3.connect(ADMINS_DB_PATH)
    cur = conn.cursor()

    if admin_db.is_super_admin(callback.from_user.id):
        rows = cur.execute(
            """
            SELECT a.user_id, a.username, a.role, GROUP_CONCAT(l.location_id)
            FROM admins a
            LEFT JOIN admin_locations l ON a.user_id = l.user_id
            WHERE a.role != 'god'
            GROUP BY a.user_id
            """
        ).fetchall()
    else:
        allowed = admin_db.get_locations_for_admin(callback.from_user.id)
        if not allowed:
            await callback.message.answer("ℹ️ У вас немає підлеглих адмінів.")
            await callback.answer()
            return
        placeholders = ",".join(["?"] * len(allowed))
        rows = cur.execute(
            f"""
            SELECT a.user_id, a.username, a.role, GROUP_CONCAT(l.location_id)
            FROM admins a
            JOIN admin_locations l ON a.user_id = l.user_id
            WHERE l.location_id IN ({placeholders}) AND a.role = 'admin'
            GROUP BY a.user_id
            """,
            tuple(allowed),
        ).fetchall()

    conn.close()

    text = "📋 СПИСОК АДМІНІВ:\n"
    if not rows:
        text += "— Поки що порожньо."
    else:
        for user_id, username, role, locs in rows:
            if admin_db.is_god(user_id):
                continue
            loc_names = ""
            if locs:
                loc_names = ", ".join([LOCATIONS[l]["name"] for l in locs.split(",") if l in LOCATIONS])
            text += f"— {username or 'N/A'} (ID: {user_id}) [{role}] {loc_names}\n"

    await callback.message.answer(text)
    await callback.answer()


@admin_router.callback_query(F.data == "adm_back_to_manage")
async def back_to_manage_admins(callback: CallbackQuery):
    if not admin_db.is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "👥 КЕРУВАННЯ ПЕРСОНАЛОМ\n"
        "═══════════════════\n"
        "Тут можна додавати / забирати доступ до адмін-панелі.",
        reply_markup=akb.get_admin_management_kb(admin_db.is_super_admin(callback.from_user.id)),
    )


@admin_router.callback_query(F.data == "adm_remove")
async def start_remove_admin(callback: CallbackQuery):
    if not admin_db.is_admin(callback.from_user.id):
        return

    import sqlite3

    conn = sqlite3.connect(ADMINS_DB_PATH)
    cur = conn.cursor()

    rows = []
    if admin_db.is_super_admin(callback.from_user.id):
        rows = cur.execute(
            "SELECT user_id, username, role FROM admins WHERE role != 'god'"
        ).fetchall()
    else:
        allowed = admin_db.get_locations_for_admin(callback.from_user.id)
        if allowed:
            placeholders = ",".join(["?"] * len(allowed))
            rows = cur.execute(
                f"""
                SELECT DISTINCT a.user_id, a.username, a.role
                FROM admins a
                JOIN admin_locations l ON a.user_id = l.user_id
                WHERE a.role = 'admin' AND l.location_id IN ({placeholders})
                """,
                tuple(allowed),
            ).fetchall()

    conn.close()

    if not rows:
        await callback.answer("ℹ️ Немає адмінів для видалення.")
        return

    await callback.message.edit_text(
        "👇 Натисніть на адміна, щоб видалити його:",
        reply_markup=akb.get_admins_to_remove_kb(rows),
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("adm_delete_"))
async def confirm_remove_admin(callback: CallbackQuery):
    if not admin_db.is_admin(callback.from_user.id):
        return

    user_id_to_remove = int(callback.data.split("_")[2])

    import sqlite3

    conn = sqlite3.connect(ADMINS_DB_PATH)
    cur = conn.cursor()
    row = cur.execute("SELECT role FROM admins WHERE user_id = ?", (user_id_to_remove,)).fetchone()
    role = row[0] if row else None

    if role == "god":
        await callback.answer("❌ Неможливо видалити GOD-користувача.")
        conn.close()
        return

    if not admin_db.is_super_admin(callback.from_user.id):
        allowed = admin_db.get_locations_for_admin(callback.from_user.id)
        if not allowed:
            await callback.answer("❌ Немає прав видаляти цього адміна.")
            conn.close()
            return
        # ensure target is within allowed locations
        placeholders = ",".join(["?"] * len(allowed))
        allowed_rows = cur.execute(
            f"SELECT 1 FROM admin_locations WHERE user_id = ? AND location_id IN ({placeholders})",
            (user_id_to_remove, *allowed),
        ).fetchone()
        if not allowed_rows:
            await callback.answer("❌ Немає прав видаляти цього адміна.")
            conn.close()
            return

    conn.close()
    admin_db.remove_admin(user_id_to_remove)
    await callback.answer(f"✅ Адміна з ID {user_id_to_remove} видалено.")
    await callback.message.edit_text("✅ Адміна видалено.")


@admin_router.callback_query(F.data.startswith("adm_confirm_"))
async def confirm_booking(callback: CallbackQuery, bot: Bot):
    if not admin_db.is_admin(callback.from_user.id):
        return

    booking_id = callback.data.split("_")[2]
    booking = booking_db.get_booking_by_id(booking_id)

    if not booking:
        await callback.answer("❌ Бронювання не знайдено.")
        return

    if not admin_db.has_location_access(callback.from_user.id, booking["location_id"]):
        await callback.answer("🚫 Немає доступу до цього закладу.")
        return

    booking_db.update_status(booking_id, "confirmed")

    try:
        user_id = booking["user_id"]
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ Ваше бронювання №{booking_id} ПІДТВЕРДЖЕНО!\nБудемо чекати на вас у «MEDELIN» ❤️",
        )
    except Exception as e:
        print(f"Error notifying user: {e}")

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ ПІДТВЕРДЖЕНО",
        reply_markup=None,
    )
    await callback.answer("Бронювання підтверджено!")


@admin_router.callback_query(F.data.startswith("adm_cancel_"))
async def cancel_booking(callback: CallbackQuery, bot: Bot):
    if not admin_db.is_admin(callback.from_user.id):
        return

    booking_id = callback.data.split("_")[2]
    booking = booking_db.get_booking_by_id(booking_id)

    if not booking:
        await callback.answer("❌ Бронювання не знайдено.")
        return

    if not admin_db.has_location_access(callback.from_user.id, booking["location_id"]):
        await callback.answer("🚫 Немає доступу до цього закладу.")
        return

    booking_db.update_status(booking_id, "cancelled")

    try:
        user_id = booking["user_id"]
        await bot.send_message(
            chat_id=user_id,
            text=f"❌ На жаль, ми не можемо підтвердити ваше бронювання №{booking_id} на цей час.\nБудь ласка, оберіть інший час або зателефонуйте нам.",
        )
    except Exception as e:
        print(f"Error notifying user: {e}")

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ ВІДХИЛЕНО",
        reply_markup=None,
    )
    await callback.answer("Бронювання відхилено.")
