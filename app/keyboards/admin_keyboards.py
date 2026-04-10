from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


EMOJI_MAP = {
    "Кава": "☕",
    "До Кави": "➕",
    "Декаф": "🍃",
    "Кава На Альтернативному": "🥛",
    "Десерти": "🍰",
    "Напої": "🍹",
    "Масала": "🌶️",
    "Фреш": "🍉",
    "Чай": "🍵",
    "Мілк": "🥤",
    "Матча": "🍵",
    "Какао": "🍫",
    "Кава в зернах": "☕",
}


def get_cat_with_emoji(cat):
    cat_s = cat.strip()
    for emoji in EMOJI_MAP.values():
        cat_s = cat_s.replace(emoji, "").strip()
    emoji = EMOJI_MAP.get(cat_s, "🍽️")
    return f"{emoji} {cat_s}"


def get_main_admin_menu(is_on_shift: bool = False, role: str = "admin"):
    keyboard = []
    if role == "admin":
        shift_text = "🔴 ЗАВЕРШИТИ ЗМІНУ" if is_on_shift else "🟢 ПОЧАТИ ЗМІНУ"
        keyboard.append([KeyboardButton(text=shift_text)])
    keyboard.append([KeyboardButton(text="🆕 НОВІ ЗАПИТИ"), KeyboardButton(text="⚡️ АКТИВНІ")])
    keyboard.append([KeyboardButton(text="👥 КОМАНДА")])
    if role == "boss":
        keyboard.append([KeyboardButton(text="📋 МЕНЮ"), KeyboardButton(text="☕ ЗЕРНО")])
        keyboard.append([KeyboardButton(text="📍 ЛОКАЦІЇ"), KeyboardButton(text="📱 СОЦМЕРЕЖІ")])
    keyboard.append([KeyboardButton(text="↩️ НА ГОЛОВНУ")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_active_types_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 АКТИВНІ БРОНІ", callback_data="active_bookings")],
            [InlineKeyboardButton(text="🛍 АКТИВНІ ЗАМОВЛЕННЯ", callback_data="active_orders")],
            [InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="admin_panel_back")],
        ]
    )


def get_active_bookings_list_kb(bookings):
    buttons = []
    for booking in bookings:
        buttons.append([InlineKeyboardButton(text=f"✅ {booking['fullname']} ({booking['date_time_str']})", callback_data=f"finish_book_{booking['_id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="active_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_active_orders_list_kb(orders):
    labels = {
        "takeaway": "На виніс",
        "in_house": "У закладі",
        "booking": "Бронювання",
    }
    buttons = []
    for order in orders:
        order_label = labels.get(order.get("order_type"), order.get("order_type", "Замовлення"))
        buttons.append([InlineKeyboardButton(text=f"✅ {order['fullname']} ({order_label})", callback_data=f"finish_order_{order['_id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="active_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_management_kb(is_super: bool = False):
    buttons = []
    if is_super:
        buttons.append([InlineKeyboardButton(text="➕ ДОДАТИ ПЕРСОНАЛ", callback_data="adm_add_new")])
        buttons.append([InlineKeyboardButton(text="🗑 ВИДАЛИТИ ДОСТУП", callback_data="adm_remove")])
    buttons.append([InlineKeyboardButton(text="📋 СПИСОК КОМАНДИ", callback_data="adm_list")])
    buttons.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="admin_panel_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_booking_manage_kb(booking_id, user_id=None):
    buttons = [
        [
            InlineKeyboardButton(text="✅ ПІДТВЕРДИТИ", callback_data=f"adm2_confirm_{booking_id}"),
            InlineKeyboardButton(text="❌ ВІДХИЛИТИ", callback_data=f"adm2_cancel_{booking_id}"),
        ]
    ]
    buttons.append([InlineKeyboardButton(text="💬 НАПИСАТИ ГОСТЮ", callback_data=f"adm_msg_{user_id}_{booking_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admins_to_remove_kb(admins):
    buttons = []
    for user_id, username, display_name, role in admins:
        title = display_name or (f"@{username}" if username else None) or str(user_id)
        buttons.append([InlineKeyboardButton(text=f"❌ {title} ({role})", callback_data=f"adm_delete_{user_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="adm_back_to_manage")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_menu_manage_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ ДОДАТИ ПОЗИЦІЮ", callback_data="menu_add")],
            [InlineKeyboardButton(text="✏️ РЕДАГУВАТИ ПОЗИЦІЮ", callback_data="menu_edit")],
            [InlineKeyboardButton(text="🗑 ВИДАЛИТИ ПОЗИЦІЮ", callback_data="menu_del")],
            [InlineKeyboardButton(text="📚 СПИСОК КАТЕГОРІЙ", callback_data="menu_cats")],
            [InlineKeyboardButton(text="⬅️ В АДМІН-ПАНЕЛЬ", callback_data="menu_back")],
        ]
    )


def get_beans_manage_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ ДОДАТИ ЗЕРНО", callback_data="beans_add")],
            [InlineKeyboardButton(text="✏️ РЕДАГУВАТИ ЗЕРНО", callback_data="beans_edit")],
            [InlineKeyboardButton(text="🗑 ВИДАЛИТИ ЗЕРНО", callback_data="beans_del")],
            [InlineKeyboardButton(text="📋 СПИСОК ЗЕРНА", callback_data="beans_list")],
            [InlineKeyboardButton(text="⬅️ В АДМІН-ПАНЕЛЬ", callback_data="beans_back")],
        ]
    )


def get_locations_manage_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ ДОДАТИ ЛОКАЦІЮ", callback_data="locs_add")],
            [InlineKeyboardButton(text="✏️ РЕДАГУВАТИ ЛОКАЦІЮ", callback_data="locs_edit")],
            [InlineKeyboardButton(text="🗑 ВИДАЛИТИ ЛОКАЦІЮ", callback_data="locs_del")],
            [InlineKeyboardButton(text="📋 СПИСОК ЛОКАЦІЙ", callback_data="locs_list")],
            [InlineKeyboardButton(text="⬅️ В АДМІН-ПАНЕЛЬ", callback_data="locs_back")],
        ]
    )


def get_socials_manage_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 ДОДАТИ СОЦМЕРЕЖУ", callback_data="soc_add")],
            [InlineKeyboardButton(text="✏️ РЕДАГУВАТИ СОЦМЕРЕЖУ", callback_data="soc_edit")],
            [InlineKeyboardButton(text="🗑 ВИДАЛИТИ СОЦМЕРЕЖУ", callback_data="soc_del")],
            [InlineKeyboardButton(text="📋 СПИСОК СОЦМЕРЕЖ", callback_data="soc_list")],
            [InlineKeyboardButton(text="⬅️ В АДМІН-ПАНЕЛЬ", callback_data="soc_back")],
        ]
    )


def get_yes_no_kb(yes_cb: str, no_cb: str = "menu_no"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ ПІДТВЕРДИТИ", callback_data=yes_cb),
                InlineKeyboardButton(text="❌ СКАСУВАТИ", callback_data=no_cb),
            ]
        ]
    )


def get_category_selection_kb(categories, prefix, include_new=False, back_cb="menu_back"):
    keyboard = []
    from app.keyboards.user_keyboards import cat_key

    for cat in categories:
        keyboard.append([InlineKeyboardButton(text=get_cat_with_emoji(cat), callback_data=f"{prefix}_{cat_key(cat)}")])

    if include_new:
        keyboard.append([InlineKeyboardButton(text="➕ Нова категорія", callback_data=f"{prefix}_NEW")])
    keyboard.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_items_in_category_kb(items, prefix, back_cb="menu_back"):
    keyboard = []
    for item_id, name in items:
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"{prefix}_{item_id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_beans_list_kb(beans, prefix="beans_delete"):
    buttons = []
    prefix_str = "❌" if "delete" in prefix or "del" in prefix else "✏️"
    for bean in beans:
        buttons.append([InlineKeyboardButton(text=f"{prefix_str} {bean['name']}", callback_data=f"{prefix}_{bean['_id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="beans_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_locations_list_kb(locs, prefix="locs_delete"):
    buttons = []
    prefix_str = "🗑" if "delete" in prefix or "del" in prefix else "✏️"
    for loc in locs:
        buttons.append([InlineKeyboardButton(text=f"{prefix_str} {loc['name']}", callback_data=f"{prefix}_{loc['_id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="locs_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_socials_list_kb(socs, prefix="soc_delete"):
    buttons = []
    prefix_str = "❌" if "delete" in prefix or "del" in prefix else "✏️"
    for social in socs:
        buttons.append([InlineKeyboardButton(text=f"{prefix_str} {social['name']}", callback_data=f"{prefix}_{social['_id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="soc_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
