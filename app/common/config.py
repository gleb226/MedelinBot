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
SALES_DB_PATH = DB_DIR / "sales.db"

DB_DIR.mkdir(parents=True, exist_ok=True)

MONGO_URI = os.getenv("MONGO_URI", "").strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "medelinbot").strip() or "medelinbot"

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "2051251535:TEST:OTk5MDA4ODgxLTAwNQ")
WORK_START_HOUR = int(os.getenv("WORK_START_HOUR", 8))
WORK_END_HOUR = int(os.getenv("WORK_END_HOUR", 20))

BOSS_IDS = [bid for bid in os.getenv("BOSS_IDS", "").split(",") if bid]
