from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from app.common.config import LOCATIONS

EMOJI_MAP = {
    'Кава': '☕️',
    'До Кави': '➕',
    'Декаф': '🍃',
    'Кава На Альтернативному': '🥛',
    'Десерти': '🍰',
    'Напої': '🥤',
    'Масала': '☕',
    'Фреш': '🍊',
    'Чай': '🫖',
    'Мілк': '🥛',
    'Матча': '🍵',
    'Какао': '🍫',
    'Кава в зернах': '☕️'
}

def get_cat_with_emoji(cat):
    cat_s = cat.strip()
    for emoji in EMOJI_MAP.values():
        cat_s = cat_s.replace(emoji, "").strip()
    emoji = EMOJI_MAP.get(cat_s, '🍽️')
    return f"{emoji} {cat_s}"

def get_main_admin_menu(is_on_shift: bool = False, role: str = "admin"):
    keyboard = []
    if role == "admin":
        shift_text = "🔴 ЗАВЕРШИТИ ЗМІНУ" if is_on_shift else "🟢 ПОЧАТИ ЗМІНУ"
        keyboard.append([KeyboardButton(text=shift_text)])
    keyboard.append([KeyboardButton(text="🆕 НОВІ ЗАПИТИ"), KeyboardButton(text="👥 КОМАНДА")])
    if role == "god":
        keyboard.append([KeyboardButton(text="📋 МЕНЮ")])
    keyboard.append([KeyboardButton(text="↩️ НА ГОЛОВНУ")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_management_kb(is_super: bool = False):
    buttons = [[InlineKeyboardButton(text="➕ ДОДАТИ ПЕРСОНАЛ", callback_data="adm_add_new")]]
    if is_super:
        buttons.append([InlineKeyboardButton(text="🗑 ВИДАЛИТИ ДОСТУП", callback_data="adm_remove")])
    buttons.append([InlineKeyboardButton(text="📋 СПИСОК КОМАНДИ", callback_data="adm_list")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_booking_manage_kb(booking_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ПІДТВЕРДИТИ", callback_data=f"adm_confirm_{booking_id}"),
         InlineKeyboardButton(text="❌ ВІДХИЛИТИ", callback_data=f"adm_cancel_{booking_id}")]
    ])

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

def get_yes_no_kb(yes_cb: str, no_cb: str = "menu_no"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ ПІДТВЕРДИТИ", callback_data=yes_cb),
                InlineKeyboardButton(text="❌ СКАСУВАТИ", callback_data=no_cb),
            ]
        ]
    )


def get_category_selection_kb(categories, prefix, include_new=False):
    keyboard = []
    cols = 2
    row = []
    for idx, cat in enumerate(categories):
        title = get_cat_with_emoji(cat)
        row.append(InlineKeyboardButton(text=title, callback_data=f"{prefix}_{idx}"))
        if len(row) == cols:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    if include_new:
        keyboard.append([InlineKeyboardButton(text="➕ Нова категорія", callback_data=f"{prefix}_NEW")])
    keyboard.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_items_in_category_kb(items, prefix):
    keyboard = []
    cols = 2
    row = []
    for item_id, name in items:
        row.append(InlineKeyboardButton(text=name, callback_data=f"{prefix}_{item_id}"))
        if len(row) == cols:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="menu_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
