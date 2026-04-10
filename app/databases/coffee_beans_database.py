from bson import ObjectId
from typing import Any
from app.databases.mongo_client import get_db, projection_without_mongo_id

class CoffeeBeansDatabase:
    async def connect(self):
        await get_db()

    async def close(self):
        return

    def calculate_prices(self, price_250: float) -> dict:
        p500 = (price_250 * 2) * 0.97               
        p1000 = (price_250 * 4) * 0.92               
        return {"250": round(price_250), "500": round(p500), "1000": round(p1000)}

    async def add_bean(self, name, price_250, description, sort, taste, roast, image_url="", country="", altitude="", processing="", acidity=0, bitterness=0, body=0, variety="", cup_score="", harvest="", recommendation=""):
        db = await get_db()
        prices = self.calculate_prices(float(price_250))
        res = await db.coffee_beans.insert_one({
            "name": name, "price_250": prices["250"], "price_500": prices["500"], "price_1000": prices["1000"],
            "description": description, "sort": sort, "taste": taste, "roast": roast, "image_url": image_url,
            "country": country, "altitude": altitude, "processing": processing, "acidity": acidity, "bitterness": bitterness, "body": body,
            "variety": variety, "cup_score": cup_score, "harvest": harvest, "recommendation": recommendation
        })
        from app.utils.data_cache import public_data_cache
        await public_data_cache.refresh_coffee()
        return str(res.inserted_id)

    async def get_all_beans(self):
        db = await get_db()
        return await db.coffee_beans.find({}).to_list(length=None)

    async def get_bean_by_id(self, bean_id):
        db = await get_db()
        try: return await db.coffee_beans.find_one({"_id": ObjectId(bean_id)})
        except: return None

    async def update_bean(self, bean_id: str, update: dict) -> bool:
        db = await get_db()
        try: oid = ObjectId(bean_id)
        except: return False
        if "price_250" in update:
            prices = self.calculate_prices(float(update["price_250"]))
            update["price_500"], update["price_1000"] = prices["500"], prices["1000"]
        res = await db.coffee_beans.update_one({"_id": oid}, {"$set": update})
        if res.matched_count:
            from app.utils.data_cache import public_data_cache
            await public_data_cache.refresh_coffee()
        return bool(res.matched_count)

    async def delete_bean(self, bean_id):
        db = await get_db()
        try:
            res = await db.coffee_beans.delete_one({"_id": ObjectId(bean_id)})
            if res.deleted_count:
                from app.utils.data_cache import public_data_cache
                await public_data_cache.refresh_coffee()
            return bool(res.deleted_count)
        except: return False

    async def clear_beans(self):
        db = await get_db()
        await db.coffee_beans.delete_many({})
        from app.utils.data_cache import public_data_cache
        await public_data_cache.refresh_coffee()

coffee_beans_db = CoffeeBeansDatabase()
