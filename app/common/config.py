from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True, encoding="utf-8")

APP_DIR = BASE_DIR / "app"
DB_DIR = APP_DIR / "databases"

USERS_DB_PATH = DB_DIR / "users.db"
BOOKINGS_DB_PATH = DB_DIR / "bookings.db"
MENU_DB_PATH = DB_DIR / "menu.db"
ERRORS_DB_PATH = DB_DIR / "errors.db"
LOGS_DB_PATH = DB_DIR / "logs.db"
ADMINS_DB_PATH = DB_DIR / "admins.db"

DB_DIR.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", BOT_TOKEN)
ADMIN_IDS = [aid for aid in os.getenv("ADMIN_IDS", "").split(",") if aid]

LOCATIONS = {
    "1": {"name": "Medelin на Корятовича", "address": "вул. Корятовича, 5"},
    "2": {"name": "Medelin на Закарпатській", "address": "вул. Закарпатська, 44"},
    "3": {"name": "Medelin на Проспекті Свободи", "address": "просп. Свободи, 54"},
    "4": {"name": "Medelin Bozdosh", "address": "Слов'янська набережна, 23А"},
    "5": {"name": "Medelin на Гойди", "address": "вул. Гойди, 4"},
    "6": {"name": "Medelin на Новака", "address": "вул. Новака, 2"},
}

GOD_IDS = [gid for gid in os.getenv("GOD_IDS", "").split(",") if gid]
