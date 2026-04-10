import hashlib
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BTN_ADMIN = "🔐 АДМІН-ПАНЕЛЬ"

def cat_key(category: str) -> str:
    return hashlib.blake2s(category.encode("utf-8"), digest_size=6).hexdigest()

def get_main_menu(is_admin: bool = False):
    if is_admin:
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_ADMIN)]], resize_keyboard=True)
    return None
