from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
env_candidates = [
    BASE_DIR.parent / ".env",
    BASE_DIR / ".env",
]
for env_path in env_candidates:
    if env_path.exists():
        load_dotenv(env_path, override=True, encoding="utf-8")

APP_DIR = BASE_DIR / "app"
DB_DIR = APP_DIR / "databases"
USERS_DB_PATH = DB_DIR / "users.db"
ORDERS_DB_PATH = DB_DIR / "orders.db"
MENU_DB_PATH = DB_DIR / "menu.db"
ERRORS_DB_PATH = DB_DIR / "errors.db"
LOGS_DB_PATH = DB_DIR / "logs.db"
ADMINS_DB_PATH = DB_DIR / "admins.db"
SALES_DB_PATH = DB_DIR / "sales.db"

DB_DIR.mkdir(parents=True, exist_ok=True)

MONGO_URI = os.getenv("MONGO_URI", "").strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "medelinbot").strip() or "medelinbot"
BOT_TOKEN = os.getenv("BOT_TOKEN")
LIQPAY_PUBLIC_KEY = os.getenv("LIQPAY_PUBLIC_KEY")
LIQPAY_PRIVATE_KEY = os.getenv("LIQPAY_PRIVATE_KEY")
BOSS_IDS = [bid for bid in os.getenv("BOSS_IDS", "").split(",") if bid]
REMOTE_API_URL = os.getenv("REMOTE_API_URL", "http://localhost:8000").strip()
