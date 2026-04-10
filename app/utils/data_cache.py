import json
from pathlib import Path
from typing import Any
from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.location_database import location_db
from app.databases.menu_database import menu_db
from app.databases.socials_database import socials_db

class PublicDataCache:
    def __init__(self) -> None:
        self._memory: dict[str, Any] = {}
        self._dir = Path(__file__).resolve().parents[2] / "cache"
        self._dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Any | None: return self._memory.get(key) or self._load_from_disk(key)
    def set(self, key: str, value: Any) -> Any: self._memory[key] = value; self._write_to_disk(key, value); return value

    async def warm_all(self) -> None:
        await self.refresh_menu(); await self.refresh_coffee(); await self.refresh_locations(); await self.refresh_socials()

    async def refresh_menu(self) -> list[dict[str, Any]]:
        categories = await menu_db.get_categories()
        full_menu = []
        for cat in categories:
            items = await menu_db.get_items_by_category(cat)
            formatted = []
            for i in items:
                formatted.append({
                    "id": str(i["_id"]), "name": i["name"], "price": i["price"], "description": i.get("description", ""),
                    "volume": i.get("volume", ""), "calories": i.get("calories", ""), "image_url": i.get("image_url", ""),
                    "options": i.get("options", []), "strength": i.get("strength", 0), "sweetness": i.get("sweetness", 0),
                    "composition": i.get("composition", ""),
                    "country": i.get("country", ""), "altitude": i.get("altitude", ""), "sort": i.get("sort", ""),
                    "processing": i.get("processing", ""), "roast": i.get("roast", ""), "taste": i.get("taste", "")
                })
            full_menu.append({"category": cat, "items": formatted})
        return self.set("menu", full_menu)

    async def refresh_coffee(self) -> list[dict[str, Any]]:
        beans = await coffee_beans_db.get_all_beans()
        formatted = []
        for b in beans:
            formatted.append({
                "id": str(b["_id"]), "name": b["name"], "price_250": b["price_250"], "price_500": b["price_500"], "price_1000": b["price_1000"],
                "description": b.get("description", ""), "sort": b.get("sort", ""), "taste": b.get("taste", ""), "roast": b.get("roast", ""),
                "country": b.get("country", ""), "altitude": b.get("altitude", ""), "processing": b.get("processing", ""),
                "acidity": b.get("acidity", 0), "bitterness": b.get("bitterness", 0), "body": b.get("body", 0), "image_url": b.get("image_url", "")
            })
        return self.set("coffee", formatted)

    async def refresh_locations(self) -> list[dict[str, Any]]:
        locs = await location_db.get_all_locations()
        formatted = [{
            "id": str(l["_id"]), 
            "name": l["name"], 
            "address": l["address"], 
            "schedule": l["schedule"], 
            "phone": l.get("phone", ""), 
            "google_maps_url": l.get("google_maps_url", ""), 
            "image_url": l.get("image_url", ""),
            "amenities": l.get("amenities", []),
            "atmosphere": l.get("atmosphere", ""),
            "coordinates": l.get("coordinates")
        } for l in locs]
        return self.set("locations", formatted)

    async def refresh_socials(self) -> list[dict[str, Any]]:
        socs = await socials_db.get_all_socials()
        formatted = [{"id": str(s["_id"]), "name": s["name"], "url": s["url"]} for s in socs]
        return self.set("socials", formatted)

    def _path_for(self, key: str) -> Path: return self._dir / f"{key}.json"
    def _load_from_disk(self, key: str) -> Any | None:
        p = self._path_for(key)
        if not p.exists(): return None
        try: d = json.loads(p.read_text(encoding="utf-8")); self._memory[key] = d; return d
        except: return None
    def _write_to_disk(self, key: str, value: Any) -> None: self._path_for(key).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

public_data_cache = PublicDataCache()
