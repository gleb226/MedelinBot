import re



def normalize_phone(phone: str) -> str:

    return re.sub(r"\D", "", phone or "")



def format_phone(phone: str) -> str:

    digits = normalize_phone(phone)

    return f"+{digits}" if digits else ""



def is_same_phone(phone_a: str, phone_b: str) -> bool:

    return normalize_phone(phone_a) == normalize_phone(phone_b)

