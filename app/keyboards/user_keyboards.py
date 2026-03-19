from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.common.config import LOCATIONS
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="☕ БРОНЮВАННЯ")],
        [KeyboardButton(text="📖 МЕНЮ"), KeyboardButton(text="🌐 САЙТ")]
    ],
    resize_keyboard=True
)


def get_locations_kb():
    keyboard = []
    for loc_id, loc_info in LOCATIONS.items():
        keyboard.append([InlineKeyboardButton(text=f"📌 {loc_info['name']}", callback_data=f"loc_{loc_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_categories_kb(categories, read_only=False):
    keyboard = []
    row = []
    emoji_map = {
        'Кава': '☕',
        'Десерти': '🍰',
        'Матча та Масала': '🍵',
        'Фреші та Соки': '🥤',
        'Мілкшейки та Фрапе': '🥤',
        'Чаї': '🍃',
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

    if read_only:
        keyboard.append([InlineKeyboardButton(text="⏪️ ДО МЕНЮ", callback_data="back_main_menu_only")])
    else:
        keyboard.append([InlineKeyboardButton(text="⏪️ ПОВЕРНУТИСЬ", callback_data="back_to_booking_summary")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_items_kb(items, category, read_only=False):
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(text=f"▪️ {item[1]} — {item[2]}", callback_data=f"item_{item[0]}")])
    keyboard.append([InlineKeyboardButton(text="⏪️ ДО КАТЕГОРІЙ", callback_data="back_cats")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_item_actions_kb(item_id, read_only=False):
    if read_only:
        keyboard = [
            [InlineKeyboardButton(text="⏪️ НАЗАД ДО СПИСКУ", callback_data="back_items")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="➕ ДОДАТИ ДО ЗАМОВЛЕННЯ", callback_data=f"add_to_cart_{item_id}")],
            [InlineKeyboardButton(text="⏪️ НАЗАД ДО СПИСКУ", callback_data="back_items")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_social_kb():
    keyboard = [
        [
            InlineKeyboardButton(text="📷 Instagram", url="https://www.instagram.com/medelin_coffee/"),
            InlineKeyboardButton(text="📘 Facebook", url="https://www.facebook.com/medelin.uzhgorod/")
        ],
        [InlineKeyboardButton(text="🌐 ВІДКРИТИ САЙТ", url="https://gleb226.github.io/MedelinSite/pages/menu/menu.html")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
