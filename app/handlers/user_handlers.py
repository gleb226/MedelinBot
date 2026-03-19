from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards import user_keyboards as kb
from app.keyboards import admin_keyboards as akb
from app.common.config import LOCATIONS, LOCATION_ADMINS
from app.databases.menu_database import menu_db
from app.databases.user_database import user_db
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
from app.handlers.error_handler import error_handler
from app.utils.logger import log_activity

user_router = Router()

class BookingStates(StatesGroup):
    choosing_location = State()
    choosing_date_time = State()
    choosing_people_count = State()
    entering_wishes = State()
    entering_phone = State()
    browsing_menu = State()

@user_router.message(CommandStart())
@error_handler("start")
async def cmd_start(message: Message):
    log_activity(message.from_user.id, message.from_user.username, "start")
    user_db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    
    keyboard = [
        [KeyboardButton(text="☕ БРОНЮВАННЯ")],
        [KeyboardButton(text="📖 МЕНЮ"), KeyboardButton(text="🌐 САЙТ")]
    ]
    
    if admin_db.is_admin(message.from_user.id):
        keyboard.append([KeyboardButton(text="🛰 АДМІН-ПАНЕЛЬ")])
    
    markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    welcome_text = (
        f"🌟 ВІТАЄМО В «МЕДЕЛІН», {message.from_user.first_name.upper()}! 🌟\n"
        "✨ Забронюйте столик або перегляньте меню.\n"
        "Оберіть дію нижче 👇"
    )
    await message.answer(welcome_text, reply_markup=markup)

@user_router.message(F.text == "🏠 ПОВЕРНУТИСЬ В МЕНЮ")
async def back_to_main(message: Message):
    await cmd_start(message)

@user_router.message(F.text == "☕ БРОНЮВАННЯ")
@error_handler("booking_start")
async def process_booking(message: Message, state: FSMContext):
    log_activity(message.from_user.id, message.from_user.username, "booking_start")
    await state.clear()
    await state.update_data(booking_mode=True)
    
    text = (
        "📍 КРОК 1/4: вибір закладу\n"
        "Оберіть кав'ярню для вашого відпочинку:"
    )
    await message.answer(text, reply_markup=kb.get_locations_kb())
    await state.set_state(BookingStates.choosing_location)

@user_router.message(F.text == "📖 МЕНЮ")
@error_handler("main_menu_opened")
async def main_menu_opened(message: Message, state: FSMContext):
    log_activity(message.from_user.id, message.from_user.username, "main_menu_opened")
    await state.clear()
    await state.update_data(booking_mode=False)
    cats = menu_db.get_categories()
    if not cats:
        await message.answer("☕ ОЙ! МЕНЮ ЗАРАЗ ОНОВЛЮЄТЬСЯ І ТИМЧАСОВО ПОРОЖНЄ.\nСПРОБУЙТЕ ПІЗНІШЕ.")
        return
    await message.answer("📖 ОБЕРІТЬ КАТЕГОРІЮ МЕНЮ:", reply_markup=kb.get_categories_kb(cats, read_only=True))

@user_router.callback_query(F.data.startswith("loc_"))
@error_handler("location_chosen")
async def location_chosen(callback: CallbackQuery, state: FSMContext):
    loc_id = callback.data.split("_")[1]
    log_activity(callback.from_user.id, callback.from_user.username, "location_chosen", f"loc_id: {loc_id}")
    await state.update_data(location_id=loc_id)
    
    text = (
        f"✅ ОБРАНО: {LOCATIONS[loc_id]['name'].upper()}\n"
        "🗓 КРОК 2/4: дата й час\n"
        "Вкажіть бажану дату та час (наприклад: сьогодні о 18:00):"
    )
    await callback.message.edit_text(text)
    await state.set_state(BookingStates.choosing_date_time)

@user_router.message(BookingStates.choosing_date_time)
@error_handler("date_time_entered")
async def date_time_entered(message: Message, state: FSMContext):
    log_activity(message.from_user.id, message.from_user.username, "date_time_entered", message.text)
    await state.update_data(date_time=message.text)
    
    text = (
        "👥 КРОК 3/4: кількість гостей\n"
        "Будь ласка, вкажіть кількість осіб:"
    )
    await message.answer(text)
    await state.set_state(BookingStates.choosing_people_count)

@user_router.message(BookingStates.choosing_people_count)
@error_handler("people_count_entered")
async def people_count_entered(message: Message, state: FSMContext):
    log_activity(message.from_user.id, message.from_user.username, "people_count_entered", message.text)
    await state.update_data(people_count=message.text)
    
    text = (
        "💬 КРОК 4/5: побажання\n"
        "Напишіть ваші побажання до бронювання або «ні»:"
    )
    await message.answer(text)
    await state.set_state(BookingStates.entering_wishes)

@user_router.message(BookingStates.entering_wishes)
@error_handler("wishes_entered")
async def wishes_entered(message: Message, state: FSMContext):
    log_activity(message.from_user.id, message.from_user.username, "wishes_entered", message.text)
    await state.update_data(wishes=message.text)
    data = await state.get_data()
    if 'cart' not in data:
        await state.update_data(cart=[])
    saved_phone = user_db.get_phone(message.from_user.id)
    if saved_phone:
        await state.update_data(phone=saved_phone)
        await show_booking_summary(message, state)
        return
    text = (
        "📞 КРОК 5/5: номер телефону\n"
        "Вкажіть свій номер у форматі +380..."
    )
    await message.answer(text)
    await state.set_state(BookingStates.entering_phone)

@user_router.message(BookingStates.entering_phone)
@error_handler("phone_entered")
async def phone_entered(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    user_db.set_phone(message.from_user.id, phone)
    await show_booking_summary(message, state)

async def show_booking_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    loc_name = LOCATIONS[data['location_id']]['name']
    phone = data.get('phone', 'не вказано')
    
    cart_text = ""
    if data.get('cart'):
        cart_text = "\n📋 ПОПЕРЕДНЄ ЗАМОВЛЕННЯ:\n"
        for item_name in data['cart']:
            cart_text += f" • {item_name}\n"

    summary = (
        "📝 ПІДСУМОК БРОНЮВАННЯ\n"
        f"🏛 ЗАКЛАД: {loc_name.upper()}\n"
        f"🕒 ЧАС: {data['date_time'].upper()}\n"
        f"👥 ГОСТЕЙ: {data['people_count']}\n"
        f"💬 ПОБАЖАННЯ: {data['wishes'].upper()}\n"
        f"📞 ТЕЛЕФОН: {phone}\n"
        f"{cart_text}"
        "\n"
        "🥘 Бажаєте додати щось з нашого меню?"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="🍕 ВІДКРИТИ МЕНЮ", callback_data="open_menu_for_booking")],
        [InlineKeyboardButton(text="✅ НАДІСЛАТИ ЗАЯВКУ", callback_data="finish_booking")]
    ]
    await message.answer(summary, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@user_router.callback_query(F.data == "open_menu_for_booking")
@error_handler("open_menu")
async def open_menu(callback: CallbackQuery, state: FSMContext):
    log_activity(callback.from_user.id, callback.from_user.username, "menu_opened")
    cats = menu_db.get_categories()
    await callback.message.edit_text("📖 ОБЕРІТЬ КАТЕГОРІЮ МЕНЮ:", reply_markup=kb.get_categories_kb(cats))
    await state.set_state(BookingStates.browsing_menu)

@user_router.callback_query(F.data.startswith("cat_"))
@error_handler("show_items")
async def show_items(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.split("_")[1]
    items = menu_db.get_items_by_category(cat)
    data = await state.get_data()
    read_only = not data.get('booking_mode', False)
    await callback.message.edit_text(f"🍴 КАТЕГОРІЯ: {cat.upper()}", reply_markup=kb.get_items_kb(items, cat, read_only=read_only))

@user_router.callback_query(F.data.startswith("item_"))
@error_handler("show_item_details")
async def show_item_details(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split("_")[1]
    item = menu_db.get_item_by_id(item_id)
    await state.update_data(last_cat=item[1])
    data = await state.get_data()
    read_only = not data.get('booking_mode', False)
    
    text = (
        f"✨ {item[2].upper()} ✨\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"💰 ЦІНА: {item[3]}\n"
        f"⚖️ ОБ'ЄМ: {item[5]}\n\n"
        f"📖 ОПИС: {item[4]}"
    )
    await callback.message.edit_text(text, reply_markup=kb.get_item_actions_kb(item[0], read_only=read_only))

@user_router.callback_query(F.data.startswith("add_to_cart_"))
@error_handler("add_to_cart")
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split("_")[3]
    item = menu_db.get_item_by_id(item_id)
    data = await state.get_data()
    if not data.get('booking_mode'):
        await callback.answer("Це лише перегляд меню. Додати можна під час бронювання.")
        return
    cart = data.get('cart', [])
    cart.append(item[2])
    await state.update_data(cart=cart)
    await callback.answer(f"✅ ДОДАНО: {item[2]}")
    
    # Повертаємо до списку категорії
    items = menu_db.get_items_by_category(item[1])
    await callback.message.edit_text(f"🍴 КАТЕГОРІЯ: {item[1].upper()}", reply_markup=kb.get_items_kb(items, item[1]))

@user_router.callback_query(F.data == "back_items")
@error_handler("back_to_items")
async def back_to_items(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cat = data.get('last_cat')
    if cat:
        items = menu_db.get_items_by_category(cat)
        await callback.message.edit_text(f"🍴 КАТЕГОРІЯ: {cat.upper()}", reply_markup=kb.get_items_kb(items, cat))
    else:
        await back_to_cats(callback, state)

@user_router.callback_query(F.data == "back_cats")
@error_handler("back_to_cats")
async def back_to_cats(callback: CallbackQuery, state: FSMContext):
    cats = menu_db.get_categories()
    data = await state.get_data()
    read_only = not data.get('booking_mode', False)
    await callback.message.edit_text("📖 ОБЕРІТЬ КАТЕГОРІЮ МЕНЮ:", reply_markup=kb.get_categories_kb(cats, read_only=read_only))

@user_router.callback_query(F.data == "back_main_menu_only")
async def back_main_menu_only(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await cmd_start(callback.message)

@user_router.callback_query(F.data == "back_to_booking_summary")
@error_handler("back_to_summary")
async def back_to_summary(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'location_id' not in data:
        await callback.answer("Спочатку почніть бронювання.")
        return
    await callback.message.delete()
    await show_booking_summary(callback.message, state)

@user_router.callback_query(F.data == "finish_booking")
@error_handler("finish_booking")
async def finish_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    loc_id = data['location_id']
    
    cart_text = "ВІДСУТНЄ"
    if data.get('cart'):
        cart_text = ", ".join(data['cart']).upper()

    # Зберігаємо в базу
    booking_id = booking_db.add_booking(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        fullname=callback.from_user.full_name,
        phone=data.get('phone') or user_db.get_phone(callback.from_user.id) or 'не вказано',
        location_id=loc_id,
        date_time=data['date_time'],
        people_count=data['people_count'],
        wishes=data['wishes'],
        cart=cart_text
    )

    admin_msg = (
        f"🔔 НОВЕ БРОНЮВАННЯ №{booking_id}\n"
        f"👤 КЛІЄНТ: {callback.from_user.full_name} (@{callback.from_user.username})\n"
        f"📞 ТЕЛЕФОН: {data.get('phone', 'не вказано')}\n"
        f"🏛 ЗАКЛАД: {LOCATIONS[loc_id]['name'].upper()}\n"
        f"🕒 ЧАС: {data['date_time'].upper()}\n"
        f"👥 ГОСТЕЙ: {data['people_count']}\n"
        f"💬 ПОБАЖАННЯ: {data['wishes'].upper()}\n"
        f"🥘 ЗАМОВЛЕННЯ: {cart_text}"
    )
    
    # Кнопки для керування
    admin_kb = akb.get_booking_manage_kb(booking_id)
    
    # Сповіщаємо всіх адмінів
    targets = admin_db.get_notification_targets(loc_id)

    for admin_id in targets:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_msg, reply_markup=admin_kb)
        except Exception as e:
            log_activity(callback.from_user.id, callback.from_user.username, "admin_notify_error", f"Admin {admin_id}: {str(e)}")

    final_text = (
        "🎉 ВАША ЗАЯВКА НАДІСЛАНА!\n"
        "Адміністратор зв'яжеться з вами найближчим часом для підтвердження.\n"
        "Дякуємо, що обираєте нас! ❤️"
    )
    await callback.message.edit_text(final_text)
    await state.clear()

@user_router.message(F.text == "🌐 САЙТ")
async def show_site(message: Message):
    await message.answer("🌐 Наші соціальні мережі та сайт:", reply_markup=kb.get_social_kb())
