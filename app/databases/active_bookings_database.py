from __future__ import annotations

from datetime import datetime, timedelta

from bson import ObjectId

from app.databases.mongo_client import get_db



class ActiveBookingsDatabase:

    async def connect(self):

        await get_db()



    async def close(self):

        return



    async def add_active_booking(self, order_id, user_id, fullname, phone, location_id, date_time, people_count, wishes):

        db = await get_db()

        try:

            date_part, time_part = date_time.split(" о ")

            day, month = date_part.split(".")

            hour, minute = time_part.split(":")

            year = datetime.now().year

            booking_dt = datetime(year, int(month), int(day), int(hour), int(minute))

        except:

            booking_dt = datetime.utcnow()



        await db.active_bookings.insert_one({

            "order_id": str(order_id),

            "user_id": int(user_id),

            "fullname": fullname,

            "phone": phone,

            "location_id": str(location_id),

            "date_time_str": date_time,

            "booking_at": booking_dt,

            "people_count": people_count,

            "wishes": wishes,

            "created_at": datetime.utcnow()

        })



    async def get_active_bookings(self, location_ids=None):

        db = await get_db()

        query = {}

        if location_ids:

            query["location_id"] = {"$in": [str(x) for x in location_ids]}

        

        cutoff = datetime.now() - timedelta(hours=1)

        await db.active_bookings.delete_many({"booking_at": {"$lt": cutoff}})

        

        cur = db.active_bookings.find(query).sort("booking_at", 1)

        return await cur.to_list(length=None)



    async def remove_booking(self, active_id):

        db = await get_db()

        await db.active_bookings.delete_one({"_id": ObjectId(str(active_id))})



    async def remove_booking_by_order_id(self, order_id):

        db = await get_db()

        await db.active_bookings.delete_one({"order_id": str(order_id)})



active_bookings_db = ActiveBookingsDatabase()

