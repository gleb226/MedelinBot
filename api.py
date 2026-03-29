import os

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.databases.menu_database import menu_db, clean_coffee_name

from app.databases.coffee_beans_database import coffee_beans_db

from pathlib import Path



from app.databases.location_database import location_db
from app.databases.socials_database import socials_db

app = FastAPI(title="Medelin Menu API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/api/menu")

async def get_full_menu():

    categories = await menu_db.get_categories()

    full_menu = []

    

    for cat in categories:

        items = await menu_db.get_items_by_category(cat)

        formatted_items = []

        for item in items:

            formatted_items.append({

                "id": item[0],

                "name": item[1],

                "price": item[2],

                "description": item[3],

                "volume": item[4],

                "calories": item[5],

                "image_url": item[6]

            })

        

        full_menu.append({

            "category": cat,

            "items": formatted_items,

            "simple": cat in ["➕ До Кави", "🍃 Декаф", "🥛 Кава На Альтернативному"]

        })

    

    return full_menu



import re

@app.get("/api/coffee")
async def get_coffee_beans():
    beans = await coffee_beans_db.get_all_beans()
    formatted_beans = []
    for bean in beans:
        name = clean_coffee_name(bean["name"])

        formatted_beans.append({
            "id": str(bean["_id"]),
            "name": name,
            "price_250": bean["price_250"],
            "price_500": bean["price_500"],
            "price_1000": bean["price_1000"],
            "description": bean["description"],
            "sort": bean["sort"],
            "taste": bean["taste"],
            "roast": bean["roast"],
            "image_url": bean.get("image_url", "")
        })
    return formatted_beans



@app.get("/api/locations")
async def get_locations():
    locs = await location_db.get_all_locations()
    formatted_locs = []
    for l in locs:
        formatted_locs.append({
            "id": str(l["_id"]),
            "name": l["name"],
            "address": l["address"],
            "schedule": l["schedule"],
            "phone": l["phone"],
            "email": l["email"],
            "google_maps_url": l["google_maps_url"],
            "coordinates": l.get("coordinates"),
            "image_url": l.get("image_url", "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800&q=80")
        })
    return formatted_locs

@app.get("/api/socials")
async def get_socials():
    socs = await socials_db.get_all_socials()
    formatted_socs = []
    for s in socs:
        formatted_socs.append({
            "id": str(s["_id"]),
            "name": s["name"],
            "url": s["url"]
        })
    return formatted_socs

