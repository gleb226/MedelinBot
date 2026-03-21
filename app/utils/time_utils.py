from datetime import datetime
from app.common.config import WORK_START_HOUR, WORK_END_HOUR

def is_working_hours() -> bool:
    now = datetime.now()
    return WORK_START_HOUR <= now.hour < WORK_END_HOUR

def get_closed_message() -> str:
    return f"😴 **Наразі ми зачинені.**\n\nНаші робочі години: з {WORK_START_HOUR:02d}:00 до {WORK_END_HOUR:02d}:00.\nБудемо раді бачити вас в робочий час! ☕️"
