import base64
import hashlib
import json
import pathlib
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.common.config import BOSS_IDS, LIQPAY_PRIVATE_KEY, LIQPAY_PUBLIC_KEY
from app.databases.guest_messages_database import guest_messages_db
from app.databases.location_database import location_db
from app.databases.orders_database import orders_db
from app.keyboards import admin_keyboards as akb
from app.utils.admin_notifications import send_admin_notification
from app.utils.data_cache import public_data_cache
from app.utils.phone_utils import format_phone

app = FastAPI(title="Medelin Menu API")

_uploads_dir = pathlib.Path(__file__).parent.parent / "MedelinSite" / "images" / "uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def warm_public_cache_on_startup():
    await public_data_cache.warm_all()

class CheckoutRequest(BaseModel):
    user_details: dict
    cart_menu: list
    cart_beans: list

class BookingRequest(BaseModel):
    name: str
    phone: str
    tg: str = ""
    location: str
    date: str
    time: str
    guests: str
    wishes: str = ""

class GuestReplyRequest(BaseModel):
    phone: str
    order_id: str = ""
    text: str

async def resolve_location(value: str | None):
    target = (value or "").strip()
    if not target:
        return None
    normalized = target.casefold()
    for loc in await location_db.get_all_locations():
        loc_id = str(loc.get("_id", ""))
        name = str(loc.get("name", "")).strip()
        address = str(loc.get("address", "")).strip()
        if target == loc_id:
            return loc
        if normalized in {
            name.casefold(),
            address.casefold(),
            f"{name} - {address}".casefold(),
            f"{name} — {address}".casefold(),
        }:
            return loc
    return None

def parse_price(value):
    import re
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else 0

def build_cart_text(cart_menu: list, cart_beans: list) -> tuple[int, str]:
    total = 0
    items = []
    for item in cart_menu:
        price = parse_price(item.get("price", 0))
        total += price
        items.append(f"- {item['name']} ({price} грн)")
    for item in cart_beans:
        price = parse_price(item.get("price", 0))
        total += price
        items.append(f"- {item['name']} {item.get('weight', '')}г ({price} грн)")
    return total, "\n".join(items)

def order_type_label(order_type: str) -> str:
    return {
        "takeaway": "На виніс",
        "in_house": "У закладі",
        "booking": "Бронювання",
    }.get(order_type, order_type or "Замовлення")

def payment_mode_label(payment_mode: str) -> str:
    return {
        "pay_now": "Оплатити зараз",
        "cashier": "Оплата на касі",
    }.get(payment_mode, payment_mode or "Не вказано")

async def notify_admins_about_order(
    order_id: str,
    user: dict,
    total: int,
    items_text: str,
    location_name: str,
    order_type: str,
    payment_mode: str,
    phone: str,
    table_number: str = "",
    loc_id: str | None = None,
):
    try:
        msg = "🔥 <b>НОВЕ ЗАМОВЛЕННЯ З САЙТУ</b> 🔥\n\n"
        msg += f"👤 Клієнт: {user.get('name', 'Не вказано')}\n"
        msg += f"📞 Телефон: <code>{phone}</code>\n"
        tg = user.get("tg", "")
        if tg:
            msg += f"💬 Telegram: {tg if tg.startswith('@') else '@' + tg}\n"
        msg += f"📍 Тип: {order_type_label(order_type)} | Локація: {location_name}\n"
        if table_number:
            msg += f"🪑 Столик: {table_number}\n"
        msg += f"💳 Оплата: {payment_mode_label(payment_mode)}\n"
        msg += f"💰 Сума: <b>{total} грн</b>\n\n"
        msg += f"🛒 Кошик:\n{items_text}"
        await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(order_id, -1), location_id=loc_id, include_boss=False)
    except Exception as e:
        print("Failed to send bot notification", e)

@app.post("/api/checkout")
async def process_checkout(req: CheckoutRequest):
    data = req.dict()
    cart_menu = data.get("cart_menu", [])
    cart_beans = data.get("cart_beans", [])
    user = data.get("user_details", {})
    total, items_text = build_cart_text(cart_menu, cart_beans)
    if total <= 0:
        raise HTTPException(status_code=400, detail="Сума замовлення не може бути нульовою.")
    location = await resolve_location(user.get("location"))
    loc_id = str(location["_id"]) if location else "unknown"
    location_name = location["name"] if location else (user.get("location") or "Невідомо")
    phone = format_phone(user.get("phone", "")) or user.get("phone", "Не вказано")
    requested_type = (user.get("type") or "").strip()
    order_type = "takeaway" if requested_type in {"takeaway", "На виніс", "З собою"} else "in_house"
    requested_payment_mode = (user.get("payment_mode") or "").strip()
    payment_mode = "pay_now" if order_type == "takeaway" else ("pay_now" if requested_payment_mode == "pay_now" else "cashier")
    table_number = (user.get("table_number") or "").strip()
    if order_type == "in_house" and not table_number:
        raise HTTPException(status_code=400, detail="Вкажіть номер столика для замовлення у закладі.")
    oid = await orders_db.add_order(
        user_id=None,
        username=user.get("tg", ""),
        fullname=user.get("name", "Не вказано"),
        phone=phone,
        location_id=loc_id,
        date_time="",
        people_count="0",
        wishes="",
        cart=items_text,
        order_type=order_type,
        payment_mode=payment_mode,
        table_number=table_number,
    )
    await notify_admins_about_order(oid, user, total, items_text, location_name, order_type, payment_mode, phone, table_number, loc_id=loc_id)
    if payment_mode == "cashier":
        return {"status": "ok", "manual": True, "order_id": oid}
    if not LIQPAY_PUBLIC_KEY or not LIQPAY_PRIVATE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Онлайн-оплата тимчасово недоступна. Для замовлення в закладі оберіть оплату на касі.",
        )
    liqpay_params = {
        "action": "pay",
        "amount": total,
        "currency": "UAH",
        "description": f"Замовлення #{oid} (Medelin)",
        "order_id": str(oid),
        "version": "3",
        "public_key": LIQPAY_PUBLIC_KEY,
        "result_url": "https://medelin.ua",
    }
    json_data = json.dumps(liqpay_params).encode("utf-8")
    encoded_data = base64.b64encode(json_data).decode("utf-8")
    sign_string = LIQPAY_PRIVATE_KEY + encoded_data + LIQPAY_PRIVATE_KEY
    signature = base64.b64encode(hashlib.sha1(sign_string.encode("utf-8")).digest()).decode("utf-8")
    return {"status": "ok", "data": encoded_data, "signature": signature, "order_id": oid}

@app.post("/api/booking")
async def process_booking(req: BookingRequest):
    data = req.dict()
    location = await resolve_location(data.get("location"))
    loc_id = str(location["_id"]) if location else "unknown"
    location_name = location["name"] if location else (data.get("location") or "Невідомо")
    phone = format_phone(data.get("phone", "")) or data.get("phone")
    booking_time = (data.get("time") or "").strip()
    oid = await orders_db.add_order(
        user_id=None,
        username=data.get("tg", ""),
        fullname=data.get("name"),
        phone=phone,
        location_id=loc_id,
        date_time=f"{data.get('date')} {booking_time}",
        people_count=data.get("guests"),
        wishes=data.get("wishes", ""),
        cart="Бронювання столика",
        order_type="booking",
        payment_mode="cashier",
    )
    if BOSS_IDS:
        try:
            msg = "🛎 <b>НОВЕ БРОНЮВАННЯ З САЙТУ</b> 🛎\n\n"
            msg += f"👤 Гість: {data.get('name')}\n"
            msg += f"📞 Телефон: <code>{phone}</code>\n"
            tg = data.get("tg", "")
            if tg:
                msg += f"💬 Telegram: {tg if tg.startswith('@') else '@' + tg}\n"
            msg += f"📍 Заклад: {location_name}\n"
            msg += f"📅 Дата: {data.get('date')} о {booking_time}\n"
            msg += f"👥 Осіб: {data.get('guests')}\n"
            if data.get("wishes"):
                msg += f"📝 Побажання: {data.get('wishes')}\n"
            await send_admin_notification(msg, reply_markup=akb.get_booking_manage_kb(oid, -1), location_id=loc_id, include_boss=False)
        except Exception as e:
            print("Failed to notify admins of booking", e)
    return {"status": "ok", "order_id": oid}

@app.get("/api/guest-messages")
async def get_guest_messages(
    phone: str = Query(default=""),
    order_id: str = Query(default=""),
    mark_read: bool = Query(default=False),
):
    messages = await guest_messages_db.get_messages(phone=phone, order_id=order_id or None)
    if mark_read:
        await guest_messages_db.mark_messages_read(phone=phone, order_id=order_id or None)
    return {
        "items": [
            {
                "source": item.get("source", "admin"),
                "text": item.get("text", ""),
                "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
                "read": bool(item.get("read")),
            }
            for item in messages
        ]
    }

@app.post("/api/guest-reply")
async def guest_reply(req: GuestReplyRequest):
    data = req.dict()
    phone = format_phone(data.get("phone", "")) or data.get("phone")
    order_id = data.get("order_id", "")
    text = data.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Текст повідомлення не може бути порожнім.")
    await guest_messages_db.add_message(order_id=order_id or None, phone=phone, source="guest", text=text)
    msg = f"💬 <b>ВІДПОВІДЬ ВІД ГОСТЯ (САЙТ)</b>\n\n"
    msg += f"👤 Телефон: <code>{phone}</code>\n"
    if order_id:
        msg += f"🔢 Замовлення: #{order_id[-6:]}\n"
    msg += f"📝 Повідомлення:\n<i>{text}</i>"
    try:
        await send_admin_notification(msg, include_boss=False)
    except Exception as e:
        print("Failed to notify admins of guest reply", e)
    return {"status": "ok"}

@app.get("/api/menu")
async def get_full_menu():
    cached = public_data_cache.get("menu")
    if cached is not None:
        return cached
    return await public_data_cache.refresh_menu()

@app.get("/api/coffee")
async def get_coffee_beans():
    cached = public_data_cache.get("coffee")
    if cached is not None:
        return cached
    return await public_data_cache.refresh_coffee()

@app.get("/api/locations")
async def get_locations():
    cached = public_data_cache.get("locations")
    if cached is not None:
        return cached
    return await public_data_cache.refresh_locations()

@app.get("/api/socials")
async def get_socials():
    cached = public_data_cache.get("socials")
    if cached is not None:
        return cached
    return await public_data_cache.refresh_socials()
