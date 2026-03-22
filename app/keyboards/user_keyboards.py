from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.common.config import LOCATIONS, WORK_START_HOUR, WORK_END_HOUR
import datetime
import hashlib

BTN_BOOK_TABLE = "📅 ЗАБРОНЮВАТИ СТОЛИК"
BTN_MENU = "🍽️ МЕНЮ / ЗАМОВЛЕННЯ"
BTN_BEANS = "☕️ КАВА В ЗЕРНАХ"
BTN_LOCATIONS = "📍 НАШІ ЗАКЛАДИ"
BTN_CONTACTS = "☎️ КОНТАКТИ"
BTN_ADMIN = "🔐 АДМІН-ПАНЕЛЬ"

def _clamp_hour(hour: int, *, allow_24: bool = False) -> int:
    try:
        hour = int(hour)
    except Exception:
        return 0
    if allow_24 and hour == 24:
        return 24
    return max(0, min(23, hour))

def cat_key(category: str) -> str:
    return hashlib.blake2s(category.encode("utf-8"), digest_size=6).hexdigest()

def get_main_menu(is_admin: bool = False):
    keyboard = [
        [KeyboardButton(text=BTN_BOOK_TABLE)],
        [KeyboardButton(text=BTN_MENU)],
        [KeyboardButton(text=BTN_BEANS)],
        [KeyboardButton(text=BTN_LOCATIONS), KeyboardButton(text=BTN_CONTACTS)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_date_kb():
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    day_after = today + datetime.timedelta(days=2)
    
    keyboard = [
        [InlineKeyboardButton(text=f"🗓 Сьогодні, {today.strftime('%d.%m')}", callback_data=f"book_date_{today.isoformat()}")],
        [InlineKeyboardButton(text=f"🗓 Завтра, {tomorrow.strftime('%d.%m')}", callback_data=f"book_date_{tomorrow.isoformat()}")],
        [InlineKeyboardButton(text=f"🗓 Післязавтра, {day_after.strftime('%d.%m')}", callback_data=f"book_date_{day_after.isoformat()}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def _ceil_to_next_half_hour(dt: datetime.datetime) -> datetime.datetime:
    dt = dt.replace(second=0, microsecond=0)
    minute = dt.minute
    if minute == 0 or minute == 30:
        return dt
    if minute < 30:
        return dt.replace(minute=30)
    return (dt + datetime.timedelta(hours=1)).replace(minute=0)

def get_time_kb(selected_date: datetime.date | None = None):
    times = []
    now = datetime.datetime.now()
    selected_date = selected_date or now.date()
    start_hour = _clamp_hour(WORK_START_HOUR)
    end_hour_raw = _clamp_hour(WORK_END_HOUR, allow_24=True)

    t = datetime.datetime.combine(selected_date, datetime.time(hour=start_hour, minute=0))

    if selected_date == now.date():
        t = max(t, _ceil_to_next_half_hour(now))

    if end_hour_raw == 24:
        closing = datetime.datetime.combine(selected_date, datetime.time(hour=0, minute=0)) + datetime.timedelta(days=1)
    else:
        closing = datetime.datetime.combine(selected_date, datetime.time(hour=_clamp_hour(end_hour_raw), minute=0))
    end = (closing - datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    while t <= end:
        times.append(t.strftime("%H:%M"))
        t += datetime.timedelta(minutes=30)

    keyboard = []
    cols = 3
    for i in range(0, len(times), cols):
        row = [
            InlineKeyboardButton(text=tm, callback_data=f"book_time_{tm}")
            for tm in times[i : i + cols]
        ]
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_pickup_time_kb():
    keyboard = [
        [InlineKeyboardButton(text="⚡️ По готовності", callback_data="pickup_time_now")],
    ]
    now = datetime.datetime.now()
    for i in range(1, 5):
        t = now + datetime.timedelta(minutes=i * 30)
        if t.hour < WORK_END_HOUR:
            keyboard.append([InlineKeyboardButton(text=f"⏱ ~{t.strftime('%H:%M')}", callback_data=f"pickup_time_{t.strftime('%H:%M')}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_locations_kb():
    keyboard = []
    row = []
    for loc_id, loc_info in LOCATIONS.items():
        name = loc_info['name'].replace("Medelin ", "")
        row.append(InlineKeyboardButton(text=f"🏛 {name}", callback_data=f"loc_{loc_id}"))
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_categories_kb(categories, booking_mode=False, cart_count=0):
    keyboard = []; row = []
    emoji_map = {
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
        'Матча': '🍵',
        'Какао': '🍫'
    }

    fixed_order = [
        'Кава', 'До Кави', 'Декаф', 'Кава На Альтернативному',
        'Десерти', 'Напої', 'Масала', 'Фреш', 'Чай', 'Мілк', 'Матча', 'Какао'
    ]

    def normalize_cat(cat):
        cat = str(cat)
        for emoji in emoji_map.values():
            cat = cat.replace(emoji, "").strip()
        if cat == 'Мільк': return 'Мілк'
        return cat

    sorted_cats = sorted(categories, key=lambda x: fixed_order.index(normalize_cat(x)) if normalize_cat(x) in fixed_order else 999)

    filtered_cats = [c for c in sorted_cats if "зерн" not in c.lower()]
    for cat in filtered_cats:
        cat_s = normalize_cat(cat)
        emoji = emoji_map.get(cat_s, '🍽️')
        title = f"{emoji} {cat_s}"
        row.append(InlineKeyboardButton(text=title, callback_data=f"cat_{cat_key(cat_s)}"))
        if len(row) == 2: keyboard.append(row); row = []
    if row: keyboard.append(row)
    if cart_count > 0 and not booking_mode:
        keyboard.append([InlineKeyboardButton(text=f"🛍 КОШИК ({cart_count})", callback_data="checkout_order")])
    bt, bd = ("⬅️ ДО БРОНІ", "back_to_booking_summary") if booking_mode else ("🏠 НА ГОЛОВНУ", "back_main_menu_only")
    keyboard.append([InlineKeyboardButton(text=bt, callback_data=bd)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def truncate(text, length=22):
    if len(text) <= length:
        return text
    return text[:length-1] + "…"

def get_items_kb(items, category, cart_count=0, booking_mode=False):
    keyboard = []
    sorted_items = sorted(items, key=lambda x: x[1])
    
    row = []
    for item in sorted_items:
        btn_text = f"{truncate(item[1])} - {item[2]}"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"item_{item[0]}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    if cart_count > 0 and not booking_mode:
        keyboard.append([InlineKeyboardButton(text=f"🛍 КОШИК ({cart_count})", callback_data="checkout_order")])
    keyboard.append([InlineKeyboardButton(text="⬅️ ДО КАТЕГОРІЙ", callback_data="back_cats")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_item_actions_kb(item_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ДОДАТИ В КОШИК", callback_data=f"add_to_cart_{item_id}")],
        [InlineKeyboardButton(text="⬅️ ДО СПИСКУ", callback_data="back_items")]
    ])

def get_beans_kb(items):
    keyboard = []
    row = []
    for item in items:
        name = truncate(item[1], 25)
        row.append(InlineKeyboardButton(text=f"☕️ {name}", callback_data=f"bean_{item[0]}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🏠 НА ГОЛОВНУ", callback_data="back_main_menu_only")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_beans_weight_kb():
    weights = ["250", "500", "1000"]
    keyboard = [[InlineKeyboardButton(text=f"⚖️ {w} г", callback_data=f"bean_w_{w}") for w in weights]]
    keyboard.append([InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="bean_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_phone_kb():
    keyboard = [
        [KeyboardButton(text="📱 НАДІСЛАТИ НОМЕР", request_contact=True)],
        [KeyboardButton(text="🏠 НА ГОЛОВНУ")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_contact_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 САЙТ", url="https://gleb226.github.io/MedelinSitel"),
         InlineKeyboardButton(text="📸 INSTAGRAM", url="https://instagram.com/medelincoffee")],
        [InlineKeyboardButton(text="🔵 FACEBOOK", url="https://facebook.com/coffee.uzhgorod.ua"),
         InlineKeyboardButton(text="📞 ТЕЛЕФОН", callback_data="contact_phone")],
        [InlineKeyboardButton(text="✉️ EMAIL", callback_data="contact_email"),
         InlineKeyboardButton(text="💻 GITHUB", url="https://github.com/gleb226/MedelinBot")],
    ])
