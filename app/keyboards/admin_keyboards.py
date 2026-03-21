from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from app.common.config import LOCATIONS

def get_main_admin_menu(is_on_shift: bool = False, role: str = "admin"):
    keyboard = []
    if role == "admin":
        shift_text = "🔴 ЗАВЕРШИТИ ЗМІНУ" if is_on_shift else "🟢 ПОЧАТИ ЗМІНУ"
        keyboard.append([KeyboardButton(text=shift_text)])
    keyboard.append([KeyboardButton(text="📥 НОВІ ЗАПИТИ"), KeyboardButton(text="👥 КОМАНДА ТА ПРАВА")])
    keyboard.append([KeyboardButton(text="🏠 ПОВЕРНУТИСЬ ДО ГОЛОВНОЇ")])
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
    for user_id, username, role in admins:
        buttons.append([InlineKeyboardButton(text=f"❌ {username or 'N/A'} ({role})", callback_data=f"adm_delete_{user_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="adm_back_to_manage")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
