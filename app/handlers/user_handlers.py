from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards import user_keyboards as kb
from app.keyboards import admin_keyboards as akb
from app.common.config import LOCATIONS
from app.databases.menu_database import menu_db
from app.databases.user_database import user_db
from app.databases.booking_database import booking_db
from app.databases.admin_database import admin_db
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
async def cmd_start(message: Message):
    await log_activity(message.from_user.id, message.from_user.username, "start")
    await user_db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    
    keyboard = [
        [KeyboardButton(text="✨ ЗАБРОНЮВАТИ СТОЛИК")],
        [KeyboardButton(text="📜 ПЕРЕГЛЯНУТИ МЕНЮ"), KeyboardButton(text="📸 НАШІ СОЦМЕРЕЖІ")],
        [KeyboardButton(text="📞 КОНТАКТИ")]
    ]
    
    if await admin_db.is_admin(message.from_user.id):
        keyboard.append([KeyboardButton(text="🛰 АДМІН-ПАНЕЛЬ")])
    
    markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    welcome_text = f"""✨ **ВІТАЄМО В «MEDELIN», {message.from_user.first_name.upper()}!** ✨

Ми створюємо атмосферу затишку та справжнього смаку кави. ☕️🥐

Оберіть дію нижче, щоб зробити ваш день особливим 👇"""
    await message.answer(welcome_text, reply_markup=markup, parse_mode="Markdown")

@user_router.message(F.text == "📞 КОНТАКТИ")
async def show_contacts(message: Message):
    text = "📍 **НАШІ ЗАКЛАДИ**\n\n"
    for loc_id, loc_info in LOCATIONS.items():
        text += f"☕️ **{loc_info['name']}**\n"
        text += f"🗺️ Адреса: {loc_info['address']}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@user_router.message(F.text == "🏠 ПОВЕРНУТИСЬ ДО ГОЛОВНОЇ")
async def back_to_main(message: Message):
    await cmd_start(message)

@user_router.message(F.text == "✨ ЗАБРОНЮВАТИ СТОЛИК")
async def process_booking(message: Message, state: FSMContext):
    await log_activity(message.from_user.id, message.from_user.username, "booking_start")
    await state.clear()
    await state.update_data(booking_mode=True, fullname=message.from_user.full_name)
    
    text = """🏢 **ОБЕРІТЬ ЛОКАЦІЮ**

Де б ви хотіли провести час сьогодні?"""
    await message.answer(text, reply_markup=kb.get_locations_kb(), parse_mode="Markdown")
    await state.set_state(BookingStates.choosing_location)

@user_router.message(F.text == "📜 ПЕРЕГЛЯНУТИ МЕНЮ")
async def main_menu_opened(message: Message, state: FSMContext):
    await log_activity(message.from_user.id, message.from_user.username, "main_menu_opened")
    await state.clear()
    await state.update_data(booking_mode=False)
    cats = await menu_db.get_categories()
    if not cats:
        await message.answer("""☕️ **ОЙ! МЕНЮ ЗАРАЗ ОНОВЛЮЄТЬСЯ.**
Спробуйте пізніше.""", parse_mode="Markdown")
        return
    await message.answer(
        """📜 **НАШЕ МЕНЮ**

Відкрийте для себе палітру смаків «Medelin»:""",
        reply_markup=kb.get_categories_kb(cats, read_only=True),
        parse_mode="Markdown"
    )

@user_router.message(F.text == "📸 НАШІ СОЦМЕРЕЖІ")
async def show_socials(message: Message):
    await message.answer(
        """📸 **МИ В МЕРЕЖАХ**

Слідкуйте за новинами та діліться враженнями:""",
        reply_markup=kb.get_social_kb(),
        parse_mode="Markdown"
    )

@user_router.callback_query(F.data.startswith("loc_"))
async def location_chosen(callback: CallbackQuery, state: FSMContext):
    loc_id = callback.data.split("_")[1]
    await log_activity(callback.from_user.id, callback.from_user.username, "location_chosen", f"loc_id: {loc_id}")
    await state.update_data(location_id=loc_id)
    
    text = f"""📍 **ОБРАНО:** {LOCATIONS[loc_id]['name'].upper()}

🗓 **КРОК 2/5:** Дата й час

Вкажіть бажану дату та час (наприклад: сьогодні о 18:00):"""
    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.set_state(BookingStates.choosing_date_time)

@user_router.message(BookingStates.choosing_date_time)
async def date_time_entered(message: Message, state: FSMContext):
    await log_activity(message.from_user.id, message.from_user.username, "date_time_entered", message.text)
    await state.update_data(date_time=message.text)
    
    text = """👥 **КРОК 3/5:** Кількість гостей

Будь ласка, вкажіть кількість осіб:"""
    await message.answer(text, parse_mode="Markdown")
    await state.set_state(BookingStates.choosing_people_count)

@user_router.message(BookingStates.choosing_people_count)
async def people_count_entered(message: Message, state: FSMContext):
    await log_activity(message.from_user.id, message.from_user.username, "people_count_entered", message.text)
    await state.update_data(people_count=message.text)
    
    text = """💬 **КРОК 4/5:** Побажання

Напишіть ваші побажання до бронювання або «ні»:"""
    await message.answer(text, parse_mode="Markdown")
    await state.set_state(BookingStates.entering_wishes)

@user_router.message(BookingStates.entering_wishes)
async def wishes_entered(message: Message, state: FSMContext):
    await log_activity(message.from_user.id, message.from_user.username, "wishes_entered", message.text)
    await state.update_data(wishes=message.text)
    data = await state.get_data()
    if 'cart' not in data:
        await state.update_data(cart=[])
    saved_phone = await user_db.get_phone(message.from_user.id)
    if saved_phone:
        await state.update_data(phone=saved_phone)
        await show_booking_summary(message, state)
        return
    text = """📞 **КРОК 5/5:** Номер телефону

Вкажіть свій номер у форматі `+380...`"""
    await message.answer(text, parse_mode="Markdown")
    await state.set_state(BookingStates.entering_phone)

@user_router.message(BookingStates.entering_phone)
async def phone_entered(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text.strip()
    else:
        await message.answer("Будь ласка, вкажіть свій номер телефону.")
        return
        
    await state.update_data(phone=phone)
    await user_db.set_phone(message.from_user.id, phone)
    await show_booking_summary(message, state)

async def show_booking_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    loc_name = LOCATIONS[data['location_id']]['name']
    phone = data.get('phone', 'не вказано')
    
    cart_text = ""
    if data.get('cart'):
        cart_text = "\n📋 **ПОПЕРЕДНЄ ЗАМОВЛЕННЯ:**\n"
        for item_name in data['cart']:
            cart_text += f" • {item_name}\n"

    summary = f"""📝 **ПІДСУМОК БРОНЮВАННЯ**

🏛 **ЗАКЛАД:** {loc_name.upper()}
🕒 **ЧАС:** {data['date_time'].upper()}
👥 **ГОСТЕЙ:** {data['people_count']}
💬 **ПОБАЖАННЯ:** {data['wishes'].upper()}
📞 **ТЕЛЕФОН:** `{phone}`
{cart_text}

🥘 Бажаєте додати щось з нашого меню?"""
    
    keyboard = [
        [InlineKeyboardButton(text="🍕 ВІДКРИТИ МЕНЮ", callback_data="open_menu_for_booking")],
        [InlineKeyboardButton(text="✅ НАДІСЛАТИ ЗАЯВКУ", callback_data="finish_booking")]
    ]
    await message.answer(summary, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

@user_router.callback_query(F.data == "open_menu_for_booking")
async def open_menu(callback: CallbackQuery, state: FSMContext):
    await log_activity(callback.from_user.id, callback.from_user.username, "menu_opened")
    cats = await menu_db.get_categories()
    await callback.message.edit_text("📖 **ОБЕРІТЬ КАТЕГОРІЮ МЕНЮ:**", reply_markup=kb.get_categories_kb(cats), parse_mode="Markdown")
    await state.set_state(BookingStates.browsing_menu)

@user_router.callback_query(F.data.startswith("cat_"))
async def show_items(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.split("_")[1]
    items = await menu_db.get_items_by_category(cat)
    data = await state.get_data()
    read_only = not data.get('booking_mode', False)
    await callback.message.edit_text(f"🍴 **КАТЕГОРІЯ:** {cat.upper()}", reply_markup=kb.get_items_kb(items, cat, read_only=read_only), parse_mode="Markdown")

@user_router.callback_query(F.data.startswith("item_"))
async def show_item_details(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split("_")[1]
    item = await menu_db.get_item_by_id(item_id)
    await state.update_data(last_cat=item[1])
    data = await state.get_data()
    read_only = not data.get('booking_mode', False)
    
    text = f"""✨ **{item[2].upper()}** ✨

💰 **ЦІНА:** `{item[3]}`
⚖️ **ОБ'ЄМ:** `{item[5]}`
🔥 **КАЛОРІЇ:** `{item[6] or 'н/д'}`

📖 **ОПИС:**
_{item[4] or 'Опис відсутній'}_"""
    await callback.message.edit_text(text, reply_markup=kb.get_item_actions_kb(item[0], read_only=read_only), parse_mode="Markdown")

@user_router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split("_")[3]
    item = await menu_db.get_item_by_id(item_id)
    data = await state.get_data()
    if not data.get('booking_mode'):
        await callback.answer("Це лише перегляд меню. Додати можна під час бронювання.")
        return
    cart = data.get('cart', [])
    cart.append(item[2])
    await state.update_data(cart=cart)
    await callback.answer(f"✅ ДОДАНО: {item[2]}")
    items = await menu_db.get_items_by_category(item[1])
    await callback.message.edit_text(f"🍴 **КАТЕГОРІЯ:** {item[1].upper()}", reply_markup=kb.get_items_kb(items, item[1]), parse_mode="Markdown")

@user_router.callback_query(F.data == "back_items")
async def back_to_items(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cat = data.get('last_cat')
    if cat:
        items = await menu_db.get_items_by_category(cat)
        await callback.message.edit_text(f"🍴 **КАТЕГОРІЯ:** {cat.upper()}", reply_markup=kb.get_items_kb(items, cat), parse_mode="Markdown")
    else:
        await back_to_cats(callback, state)

@user_router.callback_query(F.data == "back_cats")
async def back_to_cats(callback: CallbackQuery, state: FSMContext):
    cats = await menu_db.get_categories()
    data = await state.get_data()
    read_only = not data.get('booking_mode', False)
    await callback.message.edit_text("📖 **ОБЕРІТЬ КАТЕГОРІЮ МЕНЮ:**", reply_markup=kb.get_categories_kb(cats, read_only=read_only), parse_mode="Markdown")

@user_router.callback_query(F.data == "back_main_menu_only")
async def back_main_menu_only(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await cmd_start(callback.message)

@user_router.callback_query(F.data == "back_to_booking_summary")
async def back_to_summary(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'location_id' not in data:
        await callback.answer("Спочатку почніть бронювання.")
        return
    await callback.message.delete()
    await show_booking_summary(callback.message, state)

@user_router.callback_query(F.data == "finish_booking")
async def finish_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    loc_id = data['location_id']
    
    cart_text = "ВІДСУТНЄ"
    if data.get('cart'):
        cart_text = ", ".join(data['cart']).upper()
    booking_id = await booking_db.add_booking(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        fullname=data.get('fullname', callback.from_user.full_name),
        phone=data.get('phone') or await user_db.get_phone(callback.from_user.id) or 'не вказано',
        location_id=loc_id,
        date_time=data['date_time'],
        people_count=data['people_count'],
        wishes=data['wishes'],
        cart=cart_text
    )

    admin_msg = f"""🔔 **НОВЕ БРОНЮВАННЯ №{booking_id}**

👤 **КЛІЄНТ:** {data.get('fullname', callback.from_user.full_name)} (@{callback.from_user.username})
📞 **ТЕЛЕФОН:** `{data.get('phone', 'не вказано')}`
🏛 **ЗАКЛАД:** {LOCATIONS[loc_id]['name'].upper()}
🕒 **ЧАС:** {data['date_time'].upper()}
👥 **ГОСТЕЙ:** {data['people_count']}
💬 **ПОБАЖАННЯ:** {data['wishes'].upper()}
🥘 **ЗАМОВЛЕННЯ:** {cart_text}"""
    admin_kb = akb.get_booking_manage_kb(booking_id)
    targets = await admin_db.get_notification_targets(loc_id)

    for admin_id in targets:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_msg, reply_markup=admin_kb, parse_mode="Markdown")
        except Exception as e:
            await log_activity(callback.from_user.id, callback.from_user.username, "admin_notify_error", f"Admin {admin_id}: {str(e)}")

    final_text = """🎉 **ВАША ЗАЯВКА НАДІСЛАНА!**

Адміністратор зв'яжеться з вами найближчим часом для підтвердження.

Дякуємо, що обираєте нас! ❤️"""
    await callback.message.edit_text(final_text, parse_mode="Markdown")
    await state.clear()

@user_router.message(F.text == "🌐 САЙТ")
async def show_site_direct(message: Message):
    await message.answer("🌐 Наші соціальні мережі та сайт:", reply_markup=kb.get_social_kb())
