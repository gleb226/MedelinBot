from bson import ObjectId
from typing import Any
from app.databases.mongo_client import get_db

class LocationDatabase:
    async def connect(self):
        await get_db()

    async def close(self):
        return

    async def add_location(self, name, address, schedule, phone, email, google_maps_url, lat, lon):
        db = await get_db()
        res = await db.locations.insert_one({
            "name": name,
            "address": address,
            "schedule": schedule,
            "phone": phone,
            "email": email,
            "google_maps_url": google_maps_url,
            "coordinates": {
                "lat": float(lat),
                "lon": float(lon)
            }
        })
        return str(res.inserted_id)

    async def get_all_locations(self):
        db = await get_db()
        cursor = db.locations.find({})
        return await cursor.to_list(length=None)

    async def get_locations_dict(self):
        db = await get_db()
        cursor = db.locations.find({})
        locations = await cursor.to_list(length=None)
        return {str(loc['_id']): loc for loc in locations}

    async def get_location_by_id(self, loc_id):
        db = await get_db()
        try:
            return await db.locations.find_one({"_id": ObjectId(loc_id)})
        except:
            return None

    async def delete_location(self, loc_id):
        db = await get_db()
        try:
            await db.locations.delete_one({"_id": ObjectId(loc_id)})
            return True
        except:
            return False

    async def clear_locations(self):
        db = await get_db()
        await db.locations.delete_many({})

location_db = LocationDatabase()
