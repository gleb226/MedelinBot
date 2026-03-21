from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.common.config import LOCATIONS

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✨ ЗАБРОНЮВАТИ СТОЛИК")],
        [
            KeyboardButton(text="📜 ПЕРЕГЛЯНУТИ МЕНЮ"),
            KeyboardButton(text="📸 НАШІ СОЦМЕРЕЖІ")
        ],
        [KeyboardButton(text="🛰 АДМІН-ПАНЕЛЬ")]
    ],
    resize_keyboard=True
)

def get_locations_kb():
    keyboard = []
    row = []
    for loc_id, loc_info in LOCATIONS.items():
        name = loc_info['name'].replace("Medelin ", "")
        row.append(InlineKeyboardButton(text=f"📍 {name}", callback_data=f"loc_{loc_id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_categories_kb(categories, read_only=False):
    keyboard = []
    row = []
    emoji_map = {
        'Кава': '☕',
        'До Кави': '➕',
        'Декаф': '🍃',
        'Кава На Альтернативному': '🥛',
        'Десерти': '🍰',
        'Напої': '🥤',
        'Масала': '☕',
        'Фреш': '🍊',
        'Чай': '🍵',
        'Мілк': '🥛',
        'Матча': '🍵',
        'Какао': '🍫'
    }
    for cat in categories:
        emoji = emoji_map.get(cat, '✨')
        row.append(InlineKeyboardButton(text=f"{emoji} {cat}", callback_data=f"cat_{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    back_text = "🔙 НАЗАД" if not read_only else "🏠 ГОЛОВНА"
    back_data = "back_to_booking_summary" if not read_only else "back_main_menu_only"
    keyboard.append([InlineKeyboardButton(text=back_text, callback_data=back_data)])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_items_kb(items, category, read_only=False):
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(text=f"💎 {item[1]} — {item[2]}", callback_data=f"item_{item[0]}")])
    keyboard.append([InlineKeyboardButton(text="📂 ДО КАТЕГОРІЙ", callback_data="back_cats")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_item_actions_kb(item_id, read_only=False):
    keyboard = []
    if not read_only:
        keyboard.append([InlineKeyboardButton(text="➕ ДОДАТИ ДО ЗАМОВЛЕННЯ", callback_data=f"add_to_cart_{item_id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ НАЗАД ДО СПИСКУ", callback_data="back_items")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_social_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📸 Instagram", url="https://www.instagram.com/medelincoffee/"),
            InlineKeyboardButton(text="🔵 Facebook", url="https://www.facebook.com/coffee.uzhgorod.ua")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 GitHub Project", url="https://github.com/gleb226/MedelinBot"),
            InlineKeyboardButton(text="🌐 Офіційний сайт", url="https://medelin.com")
        ]
    ])
