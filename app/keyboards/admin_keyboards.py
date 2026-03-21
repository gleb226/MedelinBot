from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton

main_admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 НОВІ ЗАПИТИ")],
        [KeyboardButton(text="👥 КОМАНДА ТА ПРАВА")],
        [KeyboardButton(text="🏠 ПОВЕРНУТИСЬ ДО ГОЛОВНОЇ")],
    ],
    resize_keyboard=True,
)

def get_booking_manage_kb(booking_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ ПІДТВЕРДИТИ", callback_data=f"adm_confirm_{booking_id}"),
                InlineKeyboardButton(text="❌ ВІДХИЛИТИ", callback_data=f"adm_cancel_{booking_id}"),
            ]
        ]
    )

def get_admin_management_kb(is_super_or_god: bool):
    buttons = [
        [InlineKeyboardButton(text="➕ ДОДАТИ СПІВРОБІТНИКА", callback_data="adm_add_new")],
        [InlineKeyboardButton(text="📋 СПИСОК КОМАНДИ", callback_data="adm_list")],
    ]
    if is_super_or_god:
        buttons.insert(1, [InlineKeyboardButton(text="🗑 ВИДАЛИТИ ДОСТУП", callback_data="adm_remove")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admins_to_remove_kb(admins: list):
    buttons = []
    for item in admins:
        user_id, username, *rest = item
        buttons.append(
            [InlineKeyboardButton(text=f"👤 {username or 'N/A'} (ID: {user_id})", callback_data=f"adm_delete_{user_id}")]
        )
    buttons.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="adm_back_to_manage")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
