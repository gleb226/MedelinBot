import re
from bson import ObjectId
from typing import Any
from app.databases.mongo_client import get_db

_GRAM_RE = re.compile(
    r"""
    (?:[\(\[\{]?\s*)?
    (?P<num>\d+(?:[.,]\d+)?)
    \s*
    (?P<unit>кг|kg|г|гр|грам|грамм)
    (?:\s*[\)\]\}]?)?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

def strip_gramovka(name: str) -> tuple[str, bool]:
    if not name:
        return name, False
    original = name
    s = name.strip()
    s = re.sub(r"[\s\-–—:]+$", "", s)
    m = _GRAM_RE.search(s)
    if not m:
        return original, False
    base = s[: m.start()].strip()
    base = re.sub(r"[\s\-–—:]+$", "", base).strip()
    return (base if base else original), True

def parse_gramovka_grams(name: str) -> int | None:
    if not name:
        return None
    s = name.strip()
    s = re.sub(r"[\s\-–—:]+$", "", s)
    m = _GRAM_RE.search(s)
    if not m:
        return None
    num_s = (m.group("num") or "").replace(",", ".").strip()
    try:
        num = float(num_s)
    except Exception:
        return None
    unit = (m.group("unit") or "").lower()
    grams = int(round(num * 1000)) if unit in ("кг", "kg") else int(round(num))
    return grams if grams > 0 else None

def _doc_id(doc: dict[str, Any]) -> str:
    oid = doc.get("_id")
    if isinstance(oid, ObjectId):
        return str(oid)
    return str(oid) if oid is not None else ""

class MenuDatabase:
    async def connect(self):
        await get_db()

    async def close(self):
        return

    async def add_item(self, category, name, price, description="", volume="", calories="", image_url=""):
        db = await get_db()
        res = await db.menu.insert_one(
            {
                "category": category,
                "name": name,
                "price": price,
                "description": description or "",
                "volume": volume or "",
                "calories": calories or "",
                "image_url": image_url or "",
            }
        )
        return str(res.inserted_id)

    async def get_categories(self):
        db = await get_db()
        cats = await db.menu.distinct("category")
        cats_list = list(cats or [])
        def sort_key(cat):
            if cat == "Кава в зернах":
                return (0, cat)
            if cat == "Кава":
                return (1, cat)
            return (2, cat)
        cats_list.sort(key=sort_key)
        return cats_list

    async def get_items_by_category(self, category):
        db = await get_db()
        cur = db.menu.find({"category": category})
        items = await cur.sort("_id", 1).to_list(length=None)
        rows = []
        for i in (items or []):
            rows.append(
                (_doc_id(i), i.get("name"), i.get("price"), i.get("description"), i.get("volume"), i.get("calories"), i.get("image_url", ""))
            )
        if category != "Кава в зернах":
            return rows
        chosen: dict[str, tuple] = {}
        meta: dict[str, tuple[bool, str]] = {}
        raw_by_id = { _doc_id(x): (x.get("name") or "") for x in (items or []) }
        for r in rows:
            item_id, display_name, *_ = r
            raw = raw_by_id.get(item_id, "") or (display_name or "")
            base, had = strip_gramovka(raw)
            key = (base or raw).strip().lower()
            if not key:
                continue
            if key not in chosen:
                chosen[key] = r
                meta[key] = (had, item_id)
                continue
            prev_had, prev_id = meta[key]
            if prev_had and not had:
                chosen[key] = r
                meta[key] = (had, item_id)
            elif prev_had == had and item_id < prev_id:
                chosen[key] = r
                meta[key] = (had, item_id)
        return [chosen[k] for k in sorted(chosen.keys(), key=lambda kk: meta[kk][1])]

    async def get_item_by_id(self, item_id):
        db = await get_db()
        try:
            oid = ObjectId(item_id)
        except Exception:
            return None
        d = await db.menu.find_one({"_id": oid})
        if not d:
            return None
        return (
            _doc_id(d),
            d.get("category"),
            d.get("name"),
            d.get("price"),
            d.get("description"),
            d.get("volume"),
            d.get("calories") or "",
            d.get("image_url") or "",
        )

    async def get_item_by_name(self, name):
        db = await get_db()
        d = await db.menu.find_one({"name": name})
        if not d:
            return None
        return (
            _doc_id(d),
            d.get("category"),
            d.get("name"),
            d.get("price"),
            d.get("description"),
            d.get("volume"),
            d.get("calories") or "",
            d.get("image_url") or "",
        )

    async def update_item(self, item_id: str, update: dict) -> bool:
        db = await get_db()
        try:
            oid = ObjectId(item_id)
        except Exception:
            return False
        allowed_fields = {"category", "name", "price", "description", "volume", "calories", "image_url"}
        update = {k: v for k, v in (update or {}).items() if k in allowed_fields}
        if not update:
            return False
        res = await db.menu.update_one({"_id": oid}, {"$set": update})
        return bool(res.matched_count)

    async def delete_item(self, item_id: str) -> bool:
        db = await get_db()
        try:
            oid = ObjectId(item_id)
        except Exception:
            return False
        res = await db.menu.delete_one({"_id": oid})
        return bool(res.deleted_count)

    async def clear_menu(self):
        db = await get_db()
        await db.menu.delete_many({})

menu_db = MenuDatabase()
