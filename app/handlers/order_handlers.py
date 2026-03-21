from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.common.config import LOCATIONS, PAYMENT_TOKEN
from app.databases.booking_database import booking_db
from app.databases.user_database import user_db
from app.databases.admin_database import admin_db
from app.databases.menu_database import menu_db
from app.databases.sales_database import sales_db
from app.utils.logger import log_activity
from app.utils.time_utils import is_working_hours, get_closed_message
import app.keyboards.admin_keyboards as akb
import app.keyboards.user_keyboards as kb
import re, time

order_router = Router()

class OrderStates(StatesGroup):
    choosing_order_type = State()
    choosing_location = State()
    entering_table_number = State()
    entering_pickup_time = State()
    entering_phone = State()

@order_router.callback_query(F.data == "checkout_order")
async def order_start(callback: CallbackQuery, state: FSMContext):
    if not is_working_hours():
        await callback.message.answer(get_closed_message(), parse_mode="HTML"); return
    data = await state.get_data()
    if not data.get('cart'):
        await callback.answer("🛒 Кошик порожній."); return
    kb_type = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏢 В закладі", callback_data="order_type_in_house")],[InlineKeyboardButton(text="🛍 На виніс", callback_data="order_type_takeaway")],[InlineKeyboardButton(text="🔙 Скасувати", callback_data="back_main_menu_only")]])
    await callback.message.edit_text("🧾 <b>ОБЕРІТЬ ТИП ЗАМОВЛЕННЯ:</b>", reply_markup=kb_type, parse_mode="HTML")
    await state.set_state(OrderStates.choosing_order_type)

@order_router.callback_query(F.data == "checkout_booking")
async def booking_checkout(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_working_hours():
        await callback.message.answer(get_closed_message(), parse_mode="HTML"); return
    data = await state.get_data()
    if not data.get("booking_mode"):
        await callback.answer("Немає активної броні."); return
    if not data.get("cart"):
        await callback.answer("🛒 Спочатку додайте позиції з меню."); return
    if not data.get("phone"):
        await callback.message.answer("📞 <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН (+380...):</b>", parse_mode="HTML")
        return
    await callback.answer()
    await send_order_invoice(callback.from_user, callback.message.chat.id, state, bot)

@order_router.callback_query(F.data.startswith("order_type_"), OrderStates.choosing_order_type)
async def order_type_chosen(callback: CallbackQuery, state: FSMContext):
    await state.update_data(order_type=callback.data.replace("order_type_", ""))
    await callback.message.edit_text("📍 <b>ОБЕРІТЬ ЗАКЛАД:</b>", reply_markup=kb.get_locations_kb(), parse_mode="HTML")
    await state.set_state(OrderStates.choosing_location)

@order_router.callback_query(F.data.startswith("loc_"), OrderStates.choosing_location)
async def order_loc_chosen(callback: CallbackQuery, state: FSMContext, bot: Bot):
    loc_id = callback.data.split("_")[1]; await state.update_data(location_id=loc_id); data = await state.get_data()
    if data.get('order_type') == 'in_house':
        max_t = LOCATIONS[loc_id].get('max_tables', 10)
        await callback.message.edit_text(f"""🔢 <b>ВКАЖІТЬ НОМЕР ВАШОГО СТОЛИКА:</b>
<i>(Доступно: 1 - {max_t})</i>""", parse_mode="HTML")
        await state.set_state(OrderStates.entering_table_number)
    else:
        await state.update_data(pickup_time="ПО ГОТОВНОСТІ")
        phone = await user_db.get_phone(callback.from_user.id)
        if phone:
            await state.update_data(phone=phone)
            await send_order_invoice(callback.from_user, callback.message.chat.id, state, bot)
        else:
            await ask_phone_order(callback, state)

@order_router.callback_query(F.data.startswith("pickup_time_"))
async def order_pickup_time_chosen(callback: CallbackQuery, state: FSMContext, bot: Bot):
    time_str = callback.data.replace("pickup_time_", "")
    await state.update_data(pickup_time=time_str)
    phone = await user_db.get_phone(callback.from_user.id)
    if phone: await state.update_data(phone=phone); await send_order_invoice(callback.from_user, callback.message.chat.id, state, bot)
    else: await ask_phone_order(callback, state)

@order_router.message(OrderStates.entering_table_number)
async def order_table_entered(message: Message, state: FSMContext, bot: Bot):
    val = message.text.strip(); data = await state.get_data(); loc_id = data.get('location_id')
    max_t = LOCATIONS[loc_id].get('max_tables', 10)
    if not val.isdigit() or not (1 <= int(val) <= max_t):
        await message.answer(f"❌ <b>НЕВІРНИЙ НОМЕР.</b> Вкажіть число від 1 до {max_t}:", parse_mode="HTML"); return
    await state.update_data(table_number=val); phone = await user_db.get_phone(message.from_user.id)
    if phone: await state.update_data(phone=phone); await process_order_final(message.from_user, message.chat.id, state, bot)
    else: await ask_phone_order(message, state)

async def ask_phone_order(target, state: FSMContext):
    text = "📞 <b>ВКАЖІТЬ ВАШ ТЕЛЕФОН (+380...):</b>"
    if isinstance(target, CallbackQuery): await target.message.answer(text, parse_mode="HTML")
    else: await target.answer(text, parse_mode="HTML")
    await state.set_state(OrderStates.entering_phone)

@order_router.message(OrderStates.entering_phone)
async def order_phone_entered(message: Message, state: FSMContext, bot: Bot):
    phone = message.text.strip(); await state.update_data(phone=phone); await user_db.set_phone(message.from_user.id, phone); data = await state.get_data()
    if data.get('order_type') == 'in_house': await process_order_final(message.from_user, message.chat.id, state, bot)
    else: await send_order_invoice(message.from_user, message.chat.id, state, bot)

async def send_order_invoice(user, chat_id, state, bot):
    data = await state.get_data(); prices = []; freq = {}
    for i in data['cart']: freq[i] = freq.get(i, 0) + 1
    for name, count in freq.items():
        row = await menu_db.get_item_by_name(name)
        if row: prices.append(LabeledPrice(label=f"{name} x{count}", amount=int(re.sub(r'\D','',row[3]))*100*count))
    if not prices: return
    p_type = "bookpay" if data.get('booking_mode') else "pay"
    pay_id = f"{p_type}_{user.id}_{int(time.time())}"; await state.update_data(pay_id=pay_id)
    title = "💳 ОПЛАТА БРОНІ + ЗАМОВЛЕННЯ" if data.get("booking_mode") else "💳 ОПЛАТА ЗАМОВЛЕННЯ"
    description = "Бронювання столика + замовлення у Medelin Coffee" if data.get("booking_mode") else "Замовлення у Medelin Coffee"
    await bot.send_invoice(chat_id=chat_id, title=title, description=description, payload=pay_id, provider_token=PAYMENT_TOKEN, currency="UAH", prices=prices, start_parameter="order-payment")

async def send_beans_invoice(user, chat_id, state, bot):
    data = await state.get_data(); base = int(''.join(filter(str.isdigit, data['base_price']))) or 300
    total = int(base * (int(data['weight'])/250)) or base; pay_id = f"beans_{user.id}_{int(time.time())}"; await state.update_data(pay_id=pay_id)
    await bot.send_invoice(chat_id=chat_id, title="☕️ ОПЛАТА КАВИ", description=f"{data['bean_name']} ({data['weight']}г)", payload=pay_id, provider_token=PAYMENT_TOKEN, currency="UAH", prices=[LabeledPrice(label=data['bean_name'], amount=total*100)], start_parameter="beans-payment")

@order_router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@order_router.message(F.successful_payment)
async def pay_ok(message: Message, state: FSMContext, bot: Bot):
    p = message.successful_payment; await sales_db.record_payment(message.from_user.id, p.total_amount/100, p.currency, p.invoice_payload, p.telegram_payment_charge_id, p.provider_payment_charge_id)
    await state.update_data(payment_charge_id=p.telegram_payment_charge_id)
    if "beans" in p.invoice_payload: await process_beans_final(message.from_user, message.chat.id, state, bot)
    elif "bookpay" in p.invoice_payload: await process_booking_order_final(message.from_user, message.chat.id, state, bot)
    else: await process_order_final(message.from_user, message.chat.id, state, bot)

async def process_booking_order_final(user, chat_id, state, bot):
    data = await state.get_data(); loc_id = data.get('location_id'); is_admin = await admin_db.is_admin(user.id)
    rid = await booking_db.add_booking(user.id, user.username, user.full_name, data['phone'], loc_id, data.get('date_time'), data.get('people_count'), data.get('wishes'), ", ".join(data['cart']).upper(), "order_with_booking")
    await booking_db._execute("UPDATE bookings SET payment_id = ? WHERE id = ?", (data.get('payment_charge_id'), rid))
    msg = f"""🌟 <b>БРОНЮВАННЯ ТА ЗАМОВЛЕННЯ</b>

👤 <b>КЛІЄНТ:</b> {user.full_name}
📞 <b>ТЕЛЕФОН:</b> <code>{data['phone']}</code>
🏛 <b>ЗАКЛАД:</b> {LOCATIONS[loc_id]['name']}
🕒 <b>ЧАС:</b> {data.get('date_time')}
👥 <b>ГОСТЕЙ:</b> {data.get('people_count')}
💬 <b>ПОБАЖАННЯ:</b> {data.get('wishes') or "—"}
🥘 <b>МЕНЮ:</b> {', '.join(data['cart']).upper()}
💰 <b>СТАТУС:</b> ОПЛАЧЕНО"""
    for aid in await admin_db.get_notification_targets(loc_id):
        try: await bot.send_message(aid, msg, reply_markup=akb.get_booking_manage_kb(rid), parse_mode="HTML")
        except: pass
    await bot.send_message(
        chat_id,
        f"🎉 <b>ДЯКУЄМО! ЗАМОВЛЕННЯ ПРИЙНЯТО!</b>\n\nМи чекаємо на вас у <b>{LOCATIONS[loc_id]['name']}</b>.",
        reply_markup=kb.get_main_menu(is_admin),
        parse_mode="HTML",
    )
    await state.clear()

async def process_beans_final(user, chat_id, state, bot):
    data = await state.get_data(); is_admin = await admin_db.is_admin(user.id)
    rid = await booking_db.add_booking(user.id, user.username, user.full_name, data['phone'], data['location_id'], "БРОНЬ 2 ДНІ", "0", f"ВАГА: {data['weight']}г", f"ЗЕРНА: {data['bean_name']}", "beans_booking")
    await booking_db._execute("UPDATE bookings SET payment_id = ? WHERE id = ?", (data.get('payment_charge_id'), rid))
    msg = f"""🌟 <b>НОВЕ ЗАБРОНЮВАННЯ ЗЕРЕН</b>

👤 <b>КЛІЄНТ:</b> {user.full_name}
📞 <b>ТЕЛЕФОН:</b> <code>{data['phone']}</code>
🏛 <b>ЗАКЛАД:</b> {LOCATIONS[data['location_id']]['name']}
☕️ <b>СОРТ:</b> {data['bean_name']} ({data['weight']}г)
💰 <b>СТАТУС:</b> ОПЛАЧЕНО"""
    for aid in await admin_db.get_notification_targets(data['location_id']):
        try: await bot.send_message(aid, msg, reply_markup=akb.get_booking_manage_kb(rid), parse_mode="HTML")
        except: pass
    await bot.send_message(chat_id, f"""🎉 <b>ДЯКУЄМО! ЗАМОВЛЕННЯ ПРИЙНЯТО!</b>

Кава чекатиме на вас у <b>{LOCATIONS[data['location_id']]['name']}</b> протягом 2 днів.""", reply_markup=kb.get_main_menu(is_admin), parse_mode="HTML"); await state.clear()

async def process_order_final(user, chat_id, state, bot):
    data = await state.get_data(); is_house = data.get('order_type') == 'in_house'; is_admin = await admin_db.is_admin(user.id)
    cart_s = ", ".join(data['cart']).upper()
    time_info = data.get('pickup_time', 'ЗАРАЗ')
    rid = await booking_db.add_booking(user.id, user.username, user.full_name, data['phone'], data['location_id'], time_info, "0", "МЕНЮ", cart_s, data.get('order_type', 'order'), data.get('table_number',''))
    if not is_house: await booking_db._execute("UPDATE bookings SET payment_id = ? WHERE id = ?", (data.get('payment_charge_id'), rid))
    for item in data['cart']:
        row = await menu_db.get_item_by_name(item); price = int(''.join(filter(str.isdigit, row[3]))) if row else 0
        await sales_db.record_sale(user.id, item, price, 1, data['order_type'])
    t_line = (
        f"🪑 <b>СТОЛИК:</b> {data.get('table_number')}\n"
        if is_house
        else f"🕒 <b>ЧАС:</b> {time_info}\n"
    )
    p_stat = "💰 <b>ОПЛАЧЕНО</b>" if not is_house else "⏳ <b>ОПЛАТА В ЗАКЛАДІ</b>"
    msg = f"""🔔 <b>НОВЕ ЗАМОВЛЕННЯ</b>

👤 <b>КЛІЄНТ:</b> {user.full_name}
📞 <b>ТЕЛЕФОН:</b> <code>{data['phone']}</code>
🏛 <b>ЗАКЛАД:</b> {LOCATIONS[data['location_id']]['name']}
{t_line}🥘 <b>ПОЗИЦІЇ:</b> {cart_s}
{p_stat}"""
    for aid in await admin_db.get_notification_targets(data['location_id']):
        try: await bot.send_message(aid, msg, reply_markup=akb.get_booking_manage_kb(rid), parse_mode="HTML")
        except: pass
    await bot.send_message(chat_id, """🎉 <b>ЗАМОВЛЕННЯ ПРИЙНЯТО!</b>

Ми вже розпочали приготування. Чекаємо на вас у «Medelin»!""", reply_markup=kb.get_main_menu(is_admin), parse_mode="HTML"); await state.clear()
