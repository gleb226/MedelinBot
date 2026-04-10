import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.databases.menu_database import menu_db
from app.databases.coffee_beans_database import coffee_beans_db
from app.databases.location_database import location_db
from app.databases.socials_database import socials_db
from app.databases.mongo_client import close_client

PHOTO_URL_MENU = "https://images.unsplash.com/photo-1630040995437-80b01c5dd52d?q=80&w=687&auto=format&fit=crop"
PHOTO_URL_BEANS = "https://images.pexels.com/photos/1695052/pexels-photo-1695052.jpeg?auto=compress&cs=tinysrgb&w=800"

STR_MAP = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
SWEET_MAP = {"відсутня": 0, "низька": 1, "середня": 3, "висока": 5}

MILK_OPTIONS = [
    {"type": "milk", "name": "Звичайне", "add_price": 0},
    {"type": "milk", "name": "Безлактозне", "add_price": 15},
    {"type": "milk", "name": "Вівсяне", "add_price": 25},
    {"type": "milk", "name": "Мигдалеве", "add_price": 25},
    {"type": "milk", "name": "Кокосове", "add_price": 25},
]

CAFFEINE_OPTIONS = [
    {"type": "caffeine", "name": "Звичайна", "add_price": 0},
    {"type": "caffeine", "name": "Декаф", "add_price": 15},
]

ADDON_OPTIONS = [
    {"type": "addon", "name": "Молоко 70мл", "add_price": 10},
    {"type": "addon", "name": "Вершки 70мл", "add_price": 10},
    {"type": "addon", "name": "Мед", "add_price": 10},
    {"type": "addon", "name": "Згущене молоко", "add_price": 15},
    {"type": "addon", "name": "Карамель", "add_price": 15},
]

MENU_DATA = [
    ("Кава", "Американо", "43", "Класична чорна кава з м'яким смаком для бадьорого ранку.", "150 мл", "5 ккал", "2", "низька", "100% арабіка", False, True, ("Індія", "900-1200м", "Арабіка", "Монсунінг", "Середнє", "Мускатний горіх, земляні ноти")),
    ("Кава", "Глясе", "73", "Прохолодна кава з великою кулькою ніжного ванільного морозива.", "250 мл", "180 ккал", "2", "висока", "100% арабіка + морозиво", True, True, ("Бразилія", "1100м", "Арабіка", "Натуральна", "Середнє", "Горіх, шоколад")),
    ("Кава", "Еспресо", "42", "Основа основ — концентрований напій з щільним тілом та стійкою пінкою.", "30 мл", "5 ккал", "3", "відсутня", "100% арабіка", False, True, ("Індія", "900-1200м", "Арабіка", "Монсунінг", "Середнє", "Земляні ноти")),
    ("Кава", "Капучино", "57", "Класичне співвідношення еспресо та ніжно збитого молока.", "200 мл", "120 ккал", "2", "низька", "100% арабіка + молоко", True, True, ("Ефіопія", "1800-2100м", "Арабіка", "Мита", "Світле", "Жасмин, цитрус")),
    ("Кава", "Лате", "63", "Найніжніший кавовий напій з великою кількістю молока.", "300 мл", "150 ккал", "1", "низька", "100% арабіка + молоко", True, True, ("Бразилія", "1100м", "Арабіка", "Натуральна", "Середнє", "Карамель, молочний шоколад")),
    ("Кава", "Раф", "76", "Вершковий десертний напій, збитий разом з ванільним цукром.", "250 мл", "250 ккал", "1", "висока", "100% арабіка + вершки + ваніль", True, True, ("Колумбія", "1400-1600м", "Арабіка", "Мита", "Середнє", "Ваніль, вершки")),
    ("Кава", "Фільтр кава", "60", "Чиста кава, приготована методом прокапування через паперовий фільтр.", "250 мл", "2 ккал", "2", "відсутня", "100% Specialty Арабіка", False, False, ("Ефіопія", "2000м", "Арабіка", "Натуральна", "Світле", "Ягоди, бергамот")),
    ("Кава", "Флет Вайт", "94", "Насичений смак подвійного рістрето з тонким шаром еластичного молока.", "200 мл", "130 ккал", "3", "низька", "100% арабіка + молоко", True, True, ("Бразилія", "1100м", "Арабіка", "Натуральна", "Середнє", "Горіх, карамель")),
    ("Десерти", "Вишневий Чізкейк", "110", "Легкий чізкейк з кислинкою вишні та ніжною текстурою.", "150 г", "380 ккал", "0", "середня", "Вершковий сир, вишня, пісочна основа", False, False, None),
    ("Десерти", "Горішки зі згущенкою", "30", "Ті самі легендарні горішки зі справжнім згущеним молоком.", "50 г", "250 ккал", "0", "висока", "Згущене молоко, волоський горіх, пісочне тісто", False, False, None),
    ("Десерти", "Еклер Карамельний", "80", "Ніжне заварне тісто з оксамитовим карамельним кремом.", "70 г", "290 ккал", "0", "висока", "Заварний крем, карамель, бельгійський шоколад", False, False, None),
    ("Десерти", "Макаронс (набір)", "140", "Набір з двох французьких мигдалевих тістечок з різними смаками.", "70 г", "240 ккал", "0", "висока", "Мигдалеве борошно, білок, фруктовий ганаш", False, False, None),
    ("Десерти", "Чізкейк Сан-Себастьян", "110", "Насичений сирний десерт з характерною карамельною скоринкою.", "150 г", "450 ккал", "0", "середня", "Вершковий сир, вершки 33%, цукор, яйця", False, False, None),
    ("Напої", "Еспресо Тонік", "85", "Освіжаючий та ігристий мікс подвійного еспресо, тоніку та льоду.", "250 мл", "90 ккал", "2", "середня", "Еспресо, тонік Schweppes, лід, лимон", False, True, None),
    ("Напої", "Лимонад Класичний", "90", "Натуральний авторський лимонад з цитрусових.", "300 мл", "120 ккал", "0", "середня", "Сік лимона, сік апельсина, цукровий сироп, газована вода", False, False, None),
    ("Напої", "Джміль (Bumble)", "105", "Тришаровий напій з карамельного сиропу, апельсинового соку та еспресо.", "300 мл", "180 ккал", "2", "середня", "Еспресо, апельсиновий сік, карамельний сироп, лід", False, True, None),
    ("Чай", "Чай Масала", "90", "Пряний індійський чай на молочній основі з секретними спеціями.", "250 мл", "160 ккал", "1", "середня", "Чорний чай, молоко, імбир, кориця, кардамон, гвоздика", True, False, None),
    ("Чай", "Зелений (Сенча)", "70", "Класичний японський зелений чай з м'яким трав'яним смаком.", "400 мл", "2 ккал", "0", "відсутня", "Листовий зелений чай сорту Сенча", False, False, None),
    ("Чай", "Карпатський збір", "70", "Ароматний збір гірських трав, зібраних власноруч.", "400 мл", "2 ккал", "0", "відсутня", "М'ята, чебрець, материнка, липа, шипшина", False, False, None),
    ("Матча", "Матча Лате", "90", "Традиційний японський церемоніальний чай матча з молоком.", "250 мл", "140 ккал", "1", "середня", "Пудра матча, збите молоко", True, False, None),
    ("Какао", "Какао з маршмелоу", "65", "Насичений шоколадний напій з солодкими хмаринками маршмелоу.", "250 мл", "220 ккал", "0", "середня", "Какао-порошок Barry Callebaut, молоко, маршмелоу", True, False, None),
]

BEANS_DATA = [
    {
        "name": "Індія Монсун Малабар", 
        "price_250": 271, 
        "sort": "Арабіка 100%", 
        "roast": "Середнє", 
        "taste": "Мускатний горіх, спеції, шоколад, тютюнові ноти", 
        "description": "Унікальна кава, що проходить обробку мусонними вітрами на узбережжі Індії. Має низьку кислотність та густе тіло.",
        "country": "Індія",
        "altitude": "900-1200м",
        "processing": "Monsooned",
        "acidity": 1,
        "bitterness": 3,
        "body": 5,
        "variety": "Kents, S.795",
        "cup_score": "82",
        "harvest": "Жовтень - Лютий",
        "recommendation": "Ідеально для джезви та гейзерної кавоварки."
    },
    {
        "name": "Ефіопія Йергачіф", 
        "price_250": 281, 
        "sort": "Арабіка 100% (Specialty)", 
        "roast": "Світло-середнє", 
        "taste": "Бергамот, лимонна цедра, жасмин, чайні ноти", 
        "description": "Класика африканської кави з яскравим квітковим ароматом та витонченою цитрусовою кислинкою.",
        "country": "Ефіопія",
        "altitude": "1800-2100м",
        "processing": "Washed",
        "acidity": 4,
        "bitterness": 1,
        "body": 2,
        "variety": "Heirloom",
        "cup_score": "86.5",
        "harvest": "Листопад - Січень",
        "recommendation": "Найкраще розкривається у фільтрі та пуровері."
    },
    {
        "name": "Бразилія Сантос", 
        "price_250": 235, 
        "sort": "Арабіка 100%", 
        "roast": "Середнє", 
        "taste": "Смажений горіх, молочний шоколад, карамель", 
        "description": "Найпопулярніша бразильська кава. Ідеально збалансований смак без зайвої кислотності.",
        "country": "Бразилія",
        "altitude": "1100м",
        "processing": "Natural",
        "acidity": 2,
        "bitterness": 2,
        "body": 3,
        "variety": "Bourbon, Catuai",
        "cup_score": "81",
        "harvest": "Травень - Вересень",
        "recommendation": "Універсальний вибір для еспресо-машин."
    },
    {
        "name": "Колумбія Ексельсо", 
        "price_250": 265, 
        "sort": "Арабіка 100%", 
        "roast": "Середнє", 
        "taste": "Червоне яблуко, тростинний цукор, какао", 
        "description": "Класична колумбійська кава з приємною фруктовою кислинкою та солодким післясмаком.",
        "country": "Колумбія",
        "altitude": "1400-1600м",
        "processing": "Washed",
        "acidity": 3,
        "bitterness": 2,
        "body": 3,
        "variety": "Caturra, Typica",
        "cup_score": "83.5",
        "harvest": "Березень - Червень",
        "recommendation": "Чудово підходить для автоматичних кавомашин."
    },
    {
        "name": "Італьяно (Купаж)", 
        "price_250": 210, 
        "sort": "80% Арабіка / 20% Робуста", 
        "roast": "Темне", 
        "taste": "Темний шоколад, підсмажений тост, стійка пінка", 
        "description": "Авторська суміш для ідеального еспресо. Міцна, насичена та надзвичайно бадьора.",
        "country": "Blend",
        "altitude": "Різна",
        "processing": "Mixed",
        "acidity": 1,
        "bitterness": 4,
        "body": 5,
        "variety": "Blend",
        "cup_score": "78",
        "harvest": "Круглий рік",
        "recommendation": "Для тих, хто любить міцну каву з густою пінкою."
    },
]

LOCATIONS_DATA = [
    {
        "name": "Medelin на Закарпатській",
        "address": "вул. Закарпатська, 44, Ужгород",
        "schedule": "Пн–Нд: 08:00 – 21:00",
        "phone": "+38 (050) 377-59-06",
        "email": "medelin.social@gmail.com",
        "coords": (48.6318, 22.2858),
        "url": "https://www.google.com/maps?q=48.6318,22.2858",
        "tables": 10,
        "img": "https://images.pexels.com/photos/1307698/pexels-photo-1307698.jpeg?auto=compress&cs=tinysrgb&w=800",
        "amenities": ["Безкоштовний Wi-Fi", "Зручна робоча зона", "Власний обсмаж", "Літня тераса", "Pet-friendly"],
        "atmosphere": "Затишна кав'ярня з великим вибором кави та власною кондитерською. Чудово підходить для зустрічей, відпочинку та неспішних розмов."
    },
    {
        "name": "Medelin Кабінет (Гойди)",
        "address": "вул. Гойди, 10, Ужгород",
        "schedule": "Пн–Пт: 08:00 – 20:00, Сб-Нд: 09:00 - 19:00",
        "phone": "+38 (050) 377-59-06",
        "email": "kabinet@medelin.ua",
        "coords": (48.6274, 22.2906),
        "url": "https://www.google.com/maps?q=48.6274,22.2906",
        "tables": 12,
        "img": "https://images.pexels.com/photos/2615323/pexels-photo-2615323.jpeg?auto=compress&cs=tinysrgb&w=800",
        "amenities": ["Швидкий Wi-Fi", "Багато розеток", "Тиха атмосфера", "Ідеально для роботи", "Кондиціонер"],
        "atmosphere": "Справжній кабінет для продуктивної роботи. Тиха атмосфера та продумана ергономіка створюють ідеальні умови для фрілансу та ділових зустрічей."
    },
]

SOCIALS_DATA = [
    {"name": "Instagram", "url": "https://www.instagram.com/medelin_coffee/"},
    {"name": "Facebook", "url": "https://www.facebook.com/medelin.coffee/"},
    {"name": "Telegram", "url": "https://t.me/medelin_bot"},
]

async def seed():
    await menu_db.connect(); await coffee_beans_db.connect(); await location_db.connect(); await socials_db.connect()
    print("Clearing databases..."); await menu_db.clear_menu(); await coffee_beans_db.clear_beans(); await location_db.clear_locations(); await socials_db.clear_socials()

    print("Seeding Menu...")
    for item in MENU_DATA:
        cat, name, price, desc, vol, cal, strng, sweet, comp, has_milk, has_decaf, c_info = item
        opts = []
        if has_decaf: opts.extend(CAFFEINE_OPTIONS)
        if has_milk: opts.extend(MILK_OPTIONS)
        if cat == "Кава": opts.extend(ADDON_OPTIONS)
            
        c_country, c_altitude, c_sort, c_proc, c_roast, c_taste = ("", "", "", "", "", "")
        if c_info: c_country, c_altitude, c_sort, c_proc, c_roast, c_taste = c_info
        await menu_db.add_item(category=cat, name=name, price=price, description=desc, volume=vol, calories=cal, image_url=PHOTO_URL_MENU, strength=STR_MAP.get(strng, 0), sweetness=SWEET_MAP.get(sweet, 0), composition=comp, options=opts, country=c_country, altitude=c_altitude, sort=c_sort, processing=c_proc, roast=c_roast, taste=c_taste)

    print("Seeding Coffee Beans...")
    for b in BEANS_DATA: 
        await coffee_beans_db.add_bean(
            name=b["name"], 
            price_250=b["price_250"], 
            description=b["description"], 
            sort=b["sort"], 
            taste=b["taste"], 
            roast=b["roast"], 
            image_url=PHOTO_URL_BEANS,
            country=b["country"],
            altitude=b["altitude"],
            processing=b["processing"],
            acidity=b["acidity"],
            bitterness=b["bitterness"],
            body=b["body"],
            variety=b["variety"],
            cup_score=b["cup_score"],
            harvest=b["harvest"],
            recommendation=b["recommendation"]
        )

    print("Seeding Locations...")
    for l in LOCATIONS_DATA: 
        await location_db.add_location(name=l["name"], address=l["address"], schedule=l["schedule"], phone=l["phone"], email=l["email"], google_maps_url=l["url"], coordinates={"lat": l["coords"][0], "lon": l["coords"][1]}, max_tables=l["tables"], image_url=l["img"], amenities=l.get("amenities", []), atmosphere=l.get("atmosphere", ""))

    print("Seeding Socials...")
    for s in SOCIALS_DATA: await socials_db.add_social(s["name"], s["url"])

    print("Database seeding completed successfully!")
    await close_client()

if __name__ == "__main__":
    asyncio.run(seed())
