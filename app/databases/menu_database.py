import re
from bson import ObjectId
from typing import Any
from app.databases.mongo_client import get_db

class MenuDatabase:
    async def connect(self):
        await get_db()

    async def add_item(self, category, name, price, description="", volume="", calories="", image_url="", strength=0, sweetness=0, composition="", options=None, is_new=False, is_popular=False, country="", altitude="", sort="", processing="", roast="", taste=""):
        db = await get_db()
        res = await db.menu.insert_one({
            "category": category, "name": name, "price": price, "description": description,
            "volume": volume, "calories": calories, "image_url": image_url,
            "strength": strength, "sweetness": sweetness, "composition": composition,
            "options": options or [], "is_new": is_new, "is_popular": is_popular,
            "country": country, "altitude": altitude, "sort": sort, "processing": processing,
            "roast": roast, "taste": taste
        })
        from app.utils.data_cache import public_data_cache
        await public_data_cache.refresh_menu()
        return str(res.inserted_id)

    async def get_categories(self):
        db = await get_db()
        cats = await db.menu.distinct("category")
        cats_list = list(cats or [])
        cats_list.sort()
        return cats_list

    async def get_items_by_category(self, category):
        db = await get_db()
        return await db.menu.find({"category": category}).sort("_id", 1).to_list(length=None)

    async def clear_menu(self):
        db = await get_db()
        await db.menu.delete_many({})
        from app.utils.data_cache import public_data_cache
        await public_data_cache.refresh_menu()

menu_db = MenuDatabase()
