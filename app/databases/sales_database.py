from datetime import datetime
from app.databases.mongo_client import get_db, projection_without_mongo_id


class SalesDatabase:
    async def connect(self):
        await get_db()

    async def close(self):
        return

    async def record_sale(
        self,
        user_id: int,
        item_name: str,
        price: int,
        quantity: int = 1,
        item_type: str = "menu_item",
    ):
        db = await get_db()
        await db.sales.insert_one(
            {
                "record_type": "sale",
                "user_id": int(user_id),
                "item_name": item_name,
                "price": int(price),
                "quantity": int(quantity),
                "item_type": item_type,
                "timestamp": datetime.utcnow(),
            }
        )

    async def record_payment(
        self,
        user_id: int,
        amount: int,
        currency: str,
        payload: str,
        telegram_id: str,
        provider_id: str,
    ):
        db = await get_db()
        await db.sales.insert_one(
            {
                "record_type": "payment",
                "user_id": int(user_id),
                "amount": int(amount),
                "currency": currency,
                "payload": payload,
                "telegram_payment_charge_id": telegram_id,
                "provider_payment_charge_id": provider_id,
                "timestamp": datetime.utcnow(),
            }
        )

    async def get_user_sales(self, user_id: int):
        db = await get_db()
        cur = (
            db.sales.find({"record_type": "sale", "user_id": int(user_id)}, projection_without_mongo_id())
            .sort("timestamp", -1)
        )
        return await cur.to_list(length=None)

    async def get_all_sales(self):
        db = await get_db()
        cur = db.sales.find({"record_type": "sale"}, projection_without_mongo_id()).sort("timestamp", -1)
        return await cur.to_list(length=None)

    async def clear_all_sales(self) -> int:
        db = await get_db()
        res = await db.sales.delete_many({})
        return int(res.deleted_count or 0)


sales_db = SalesDatabase()
