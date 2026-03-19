from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton


main_admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 НОВІ БРОНЮВАННЯ")],
        [KeyboardButton(text="👥 КЕРУВАННЯ АДМІНАМИ")],
        [KeyboardButton(text="🏠 ПОВЕРНУТИСЬ В МЕНЮ")],
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


def get_admin_management_kb(is_super: bool):
    buttons = [
        [InlineKeyboardButton(text="➕ ДОДАТИ АДМІНА", callback_data="adm_add_new")],
        [InlineKeyboardButton(text="➖ ВИДАЛИТИ АДМІНА", callback_data="adm_remove")],
        [InlineKeyboardButton(text="📋 СПИСОК АДМІНІВ", callback_data="adm_list")],
    ]
    # super/god бачать ту ж кнопку add_new, але можуть обирати роль super у діалозі
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admins_to_remove_kb(admins: list):
    buttons = []
    for item in admins:
        user_id, username, *rest = item
        buttons.append(
            [InlineKeyboardButton(text=f"❌ {username or 'N/A'} (ID: {user_id})", callback_data=f"adm_delete_{user_id}")]
        )
    buttons.append([InlineKeyboardButton(text="◀️ НАЗАД", callback_data="adm_back_to_manage")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
