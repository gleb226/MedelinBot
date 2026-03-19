# 🏥 MedelinBot

<div align="center">

![MedelinBot Logo](https://img.shields.io/badge/Medelin-Bot-blue?style=for-the-badge&logo=telegram)

**Розумний медичний асистент у вашому Telegram**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-blue?style=flat-square&logo=telegram)](https://core.telegram.org/bots/api)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained-Yes-brightgreen.svg?style=flat-square)](https://github.com/gleb226/MedelinBot/graphs/commit-activity)

[Особливості](#-особливості) • [Встановлення](#-встановлення) • [Використання](#-використання) • [Документація](#-документація) • [Внесок](#-внесок)

</div>

---

## 📋 Зміст

- [Про проект](#-про-проект)
- [Особливості](#-особливості)
- [Технології](#-технології)
- [Встановлення](#-встановлення)
- [Конфігурація](#-конфігурація)
- [Використання](#-використання)
- [Команди](#-команди)
- [Структура проекту](#-структура-проекту)
- [API Документація](#-api-документація)
- [База даних](#-база-даних)
- [Безпека](#-безпека)
- [Тестування](#-тестування)
- [Розгортання](#-розгортання)
- [Внесок у проект](#-внесок-у-проект)
- [Ліцензія](#-ліцензія)
- [Контакти](#-контакти)

---

## 🎯 Про проект

**MedelinBot** — це інтелектуальний Telegram бот, створений для спрощення доступу до медичних послуг та інформації. Бот надає користувачам можливість швидко отримувати консультації, записуватися на прийом, відстежувати стан здоров'я та отримувати корисні медичні рекомендації.

### 🌟 Чому MedelinBot?

- ⚡ **Швидкість**: Миттєві відповіді на запити 24/7
- 🔒 **Безпека**: Шифрування персональних даних
- 🎯 **Точність**: Інтеграція з перевіреними медичними базами
- 🌍 **Доступність**: Працює на будь-якому пристрої з Telegram
- 🇺🇦 **Локалізація**: Повна підтримка української мови

---

## ✨ Особливості

### 🏥 Медичні функції

- 📅 **Запис на прийом**
    - Онлайн-запис до лікарів
    - Вибір зручного часу
    - Нагадування про візити
    - Історія записів

- 💊 **Інформація про ліки**
    - Пошук медикаментів
    - Інструкції та дозування
    - Побічні ефекти
    - Взаємодія препаратів

- 🔍 **Діагностичний помічник**
    - Аналіз симптомів
    - Рекомендації щодо консультацій
    - Перша допомога
    - Медичні довідники

### 👤 Персоналізація

- 📊 **Особистий кабінет**
    - Історія звернень
    - Медична картка
    - Рецепти та аналізи
    - Налаштування профілю

- 🔔 **Нагадування**
    - Прийом ліків за розкладом
    - Планові огляди
    - Вакцинація
    - Здоровий спосіб життя

### 🤖 Інтелектуальні можливості

- 💬 **Чат-бот консультант**
    - Розуміння природної мови
    - Контекстні діалоги
    - Багатомовність
    - Голосові повідомлення

- 📈 **Аналітика здоров'я**
    - Моніторинг показників
    - Графіки та статистика
    - Рекомендації
    - Експорт даних

---

## 🛠 Технології

### Backend

```python
Python 3.8+          # Основна мова програмування
python-telegram-bot  # Telegram Bot API
SQLAlchemy          # ORM для роботи з БД
Redis               # Кешування та черги
Celery              # Асинхронні задачі
```

### База даних

```sql
PostgreSQL 13+      # Основна БД
Redis 6+            # Кеш та сесії
```

### Інструменти розробки

```yaml
Docker              # Контейнеризація
Docker Compose      # Оркестрація
pytest              # Тестування
pre-commit          # Git hooks
Black               # Форматування коду
Flake8              # Лінтинг
```

### Інфраструктура

```
Nginx               # Reverse proxy
Gunicorn            # WSGI сервер
Supervisor          # Менеджер процесів
Prometheus          # Моніторинг
Grafana             # Візуалізація метрик
```

---

## 🚀 Встановлення

### Передумови

Переконайтеся, що у вас встановлено:

- Python 3.8 або новіша версія
- PostgreSQL 13+
- Redis 6+
- Git

### Швидкий старт

#### 1. Клонування репозиторію

```bash
git clone https://github.com/gleb226/MedelinBot.git
cd MedelinBot
```

#### 2. Створення віртуального середовища

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

#### 4. Налаштування змінних середовища

```bash
cp .env.example .env
nano .env  # або використовуйте свій улюблений редактор
```

#### 5. Ініціалізація бази даних

```bash
# Створення таблиць
python manage.py db init
python manage.py db migrate
python manage.py db upgrade

# Заповнення початковими даними
python manage.py seed
```

#### 6. Запуск бота

```bash
python main.py
```

### 🐳 Встановлення через Docker

```bash
# Клонування репозиторію
git clone https://github.com/gleb226/MedelinBot.git
cd MedelinBot

# Налаштування змінних середовища
cp .env.example .env
nano .env

# Запуск через Docker Compose
docker-compose up -d

# Перевірка логів
docker-compose logs -f bot
```

---

## ⚙️ Конфігурація

### Файл .env

Створіть файл `.env` у кореневій директорії проекту:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username

# База даних
DATABASE_URL=postgresql://user:password@localhost:5432/medelinbot
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# Безпека
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# Логування
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log

# API ключі (опціонально)
OPENAI_API_KEY=your_openai_key
MEDICAL_API_KEY=your_medical_api_key

# Налаштування
TIMEZONE=Europe/Kiev
LANGUAGE=uk
MAX_MESSAGE_LENGTH=4096
```

### Конфігурація бота

Файл `config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME')
    
    # База даних
    DATABASE_URL = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL')
    
    # Безпека
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Налаштування
    TIMEZONE = os.getenv('TIMEZONE', 'Europe/Kiev')
    LANGUAGE = os.getenv('LANGUAGE', 'uk')
```

---

## 📱 Використання

### Початок роботи

1. **Знайдіть бота** у Telegram: `@MedelinBot`
2. **Натисніть** `/start` для початку
3. **Зареєструйтеся** або увійдіть
4. **Виберіть потрібну послугу** з меню

### Приклади використання

#### 📅 Запис на прийом

```
Користувач: Запис до кардіолога
Бот: 🏥 Доступні кардіологи:
     1. Іваненко І.І. - Вівторок, 14:00
     2. Петренко П.П. - Середа, 10:00
     Виберіть номер або час:
```

#### 💊 Інформація про ліки

```
Користувач: Парацетамол
Бот: 💊 Парацетамол
     
     📋 Застосування: жарознижуючий засіб
     💉 Дозування: 500мг 3 рази на день
     ⚠️ Побічні ефекти: рідко - алергія
     🚫 Протипоказання: захворювання печінки
```

#### 🔍 Аналіз симптомів

```
Користувач: Головний біль та температура 38
Бот: 🔍 Аналізую ваші симптоми...
     
     Можливі причини:
     • Застуда / ГРВІ
     • Грип
     
     Рекомендації:
     ✓ Відпочинок
     ✓ Багато рідини
     ✓ Жарознижуючі
     
     ⚠️ Якщо симптоми погіршуються - зверніться до лікаря
```

---

## 📚 Команди

### Основні команди

| Команда | Опис |
|---------|------|
| `/start` | Запуск бота та реєстрація |
| `/help` | Довідка по командам |
| `/menu` | Головне меню |
| `/profile` | Особистий кабінет |
| `/appointments` | Мої записи |
| `/history` | Історія звернень |

### Медичні команди

| Команда | Опис |
|---------|------|
| `/book` | Записатися на прийом |
| `/doctors` | Список лікарів |
| `/medicine <назва>` | Інформація про ліки |
| `/symptoms` | Аналіз симптомів |
| `/emergency` | Екстрена допомога |

### Налаштування

| Команда | Опис |
|---------|------|
| `/settings` | Налаштування профілю |
| `/language` | Вибір мови |
| `/notifications` | Налаштування сповіщень |
| `/privacy` | Налаштування приватності |

### Адміністративні команди

| Команда | Опис |
|---------|------|
| `/admin` | Панель адміністратора |
| `/stats` | Статистика використання |
| `/broadcast` | Розсилка повідомлень |
| `/users` | Управління користувачами |

---

## 📁 Структура проекту

```
MedelinBot/
├── 📂 app/
│   ├── 📂 handlers/          # Обробники команд
│   │   ├── __init__.py
│   │   ├── start.py         # /start, /help
│   │   ├── appointments.py  # Записи на прийом
│   │   ├── medicine.py      # Інформація про ліки
│   │   └── profile.py       # Профіль користувача
│   ├── 📂 models/           # Моделі бази даних
│   │   ├── __init__.py
│   │   ├── user.py          # Користувачі
│   │   ├── appointment.py   # Записи
│   │   └── medicine.py      # Медикаменти
│   ├── 📂 services/         # Бізнес-логіка
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── appointment_service.py
│   │   └── notification_service.py
│   ├── 📂 utils/            # Допоміжні функції
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   ├── formatters.py
│   │   └── decorators.py
│   ├── 📂 middleware/       # Middleware
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── logging.py
│   └── 📂 keyboards/        # Клавіатури
│       ├── __init__.py
│       ├── main_menu.py
│       └── inline_buttons.py
├── 📂 database/
│   ├── migrations/          # Міграції БД
│   └── seeds/              # Початкові дані
├── 📂 tests/               # Тести
│   ├── test_handlers/
│   ├── test_services/
│   └── test_models/
├── 📂 docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
├── 📂 docs/                # Документація
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── CONTRIBUTING.md
├── 📂 logs/                # Логи
├── 📂 scripts/             # Скрипти
│   ├── deploy.sh
│   └── backup.sh
├── .env.example            # Приклад змінних
├── .gitignore
├── requirements.txt        # Залежності Python
├── config.py              # Конфігурація
├── main.py                # Точка входу
├── manage.py              # CLI команди
├── README.md              # Цей файл
└── LICENSE                # Ліцензія
```

---

## 🔌 API Документація

### Endpoints

#### Користувачі

```http
GET /api/users/{user_id}
POST /api/users
PUT /api/users/{user_id}
DELETE /api/users/{user_id}
```

#### Записи

```http
GET /api/appointments
POST /api/appointments
GET /api/appointments/{id}
PUT /api/appointments/{id}
DELETE /api/appointments/{id}
```

#### Лікарі

```http
GET /api/doctors
GET /api/doctors/{id}
GET /api/doctors/{id}/schedule
```

### Приклади запитів

#### Створення запису

```bash
curl -X POST https://api.medelinbot.com/appointments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "doctor_id": 123,
    "date": "2024-03-20",
    "time": "14:00",
    "reason": "Консультація"
  }'
```

#### Отримання списку лікарів

```bash
curl -X GET https://api.medelinbot.com/doctors \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 💾 База даних

### Схема бази даних

```sql
-- Користувачі
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    full_name VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    language VARCHAR(10) DEFAULT 'uk',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Записи на прийом
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    doctor_id INTEGER REFERENCES doctors(id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Лікарі
CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    specialization VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    rating DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Медикаменти
CREATE TABLE medicines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    dosage VARCHAR(255),
    contraindications TEXT,
    side_effects TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Міграції

```bash
# Створити нову міграцію
python manage.py db migrate -m "Опис змін"

# Застосувати міграції
python manage.py db upgrade

# Відкотити міграцію
python manage.py db downgrade
```

---

## 🔒 Безпека

### Захист даних

- 🔐 **Шифрування**: Всі персональні дані шифруються AES-256
- 🛡️ **GDPR**: Повна відповідність вимогам GDPR
- 🔑 **Токени**: JWT токени для аутентифікації
- 🚫 **Rate Limiting**: Захист від спаму та DDoS

### Рекомендації

```python
# Ніколи не зберігайте токени у коді
# ❌ НЕПРАВИЛЬНО
BOT_TOKEN = "123456:ABC-DEF"

# ✅ ПРАВИЛЬНО
import os
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
```

### Безпечні практики

1. **Регулярно оновлюйте залежності**
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

2. **Використовуйте сильні паролі для БД**
3. **Обмежуйте доступ до адмін-панелі**
4. **Регулярно робіть бекапи**
5. **Моніторте логи на підозрілу активність**

---

## 🧪 Тестування

### Запуск тестів

```bash
# Всі тести
pytest

# З покриттям коду
pytest --cov=app tests/

# Конкретний тест
pytest tests/test_handlers/test_start.py

# З виводом у консоль
pytest -v

# Паралельний запуск
pytest -n auto
```

### Структура тестів

```python
# tests/test_handlers/test_start.py
import pytest
from app.handlers.start import start_command

@pytest.mark.asyncio
async def test_start_command():
    """Тест команди /start"""
    # Arrange
    mock_update = create_mock_update()
    
    # Act
    result = await start_command(mock_update, None)
    
    # Assert
    assert result is not None
    assert "Вітаємо" in result
```

### Покриття коду

```bash
# Генерація звіту покриття
coverage run -m pytest
coverage report
coverage html  # HTML звіт
```

---

## 🚀 Розгортання

### Production на VPS

#### 1. Підготовка сервера

```bash
# Оновлення системи
sudo apt update && sudo apt upgrade -y

# Встановлення необхідних пакетів
sudo apt install python3.8 python3-pip postgresql redis-server nginx -y
```

#### 2. Налаштування PostgreSQL

```bash
sudo -u postgres psql
CREATE DATABASE medelinbot;
CREATE USER botuser WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE medelinbot TO botuser;
\q
```

#### 3. Клонування та налаштування

```bash
cd /var/www
git clone https://github.com/gleb226/MedelinBot.git
cd MedelinBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Systemd Service

Створіть `/etc/systemd/system/medelinbot.service`:

```ini
[Unit]
Description=MedelinBot Telegram Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/MedelinBot
Environment="PATH=/var/www/MedelinBot/venv/bin"
ExecStart=/var/www/MedelinBot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start medelinbot
sudo systemctl enable medelinbot
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  bot:
    build: .
    container_name: medelinbot
    restart: always
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:13
    container_name: medelinbot_db
    restart: always
    environment:
      POSTGRES_DB: medelinbot
      POSTGRES_USER: botuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    container_name: medelinbot_redis
    restart: always

volumes:
  postgres_data:
```

---

## 🤝 Внесок у проект

Ми вітаємо будь-який внесок у розвиток проекту!

### Як долучитися

1. **Fork** проекту
2. **Створіть** feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** ваші зміни (`git commit -m 'Add some AmazingFeature'`)
4. **Push** в branch (`git push origin feature/AmazingFeature`)
5. **Відкрийте** Pull Request

### Правила коду

- Використовуйте **Black** для форматування
- Додавайте **docstrings** до функцій
- Пишіть **тести** для нового функціоналу
- Дотримуйтесь **PEP 8**

```bash
# Форматування коду
black app/

# Перевірка стилю
flake8 app/

# Сортування імпортів
isort app/
```

### Звіт про помилки

Створюйте Issue з такою інформацією:

- 📝 Опис проблеми
- 🔄 Кроки для відтворення
- ✅ Очікувана поведінка
- ❌ Фактична поведінка
- 💻 Версія Python, ОС
- 📋 Логи (якщо є)

---

## 📈 Roadmap

### v2.0 (Q2 2024)

- [ ] 🤖 Інтеграція з ChatGPT для консультацій
- [ ] 📊 Розширена аналітика здоров'я
- [ ] 🌐 Мультимовність (англійська, польська)
- [ ] 💳 Онлайн-оплата послуг

### v2.1 (Q3 2024)

- [ ] 📱 Мобільний додаток
- [ ] 🔗 Інтеграція з медичними системами
- [ ] 🎙️ Голосовий асистент
- [ ] 📸 Розпізнавання рецептів

### Довгострокові плани

- [ ] 🧬 Генетичні рекомендації
- [ ] 🏃 Інтеграція з фітнес-трекерами
- [ ] 👥 Сімейний акаунт
- [ ] 🌍 Телемедицина

---

## 📊 Статистика

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/gleb226/MedelinBot?style=social)
![GitHub forks](https://img.shields.io/github/forks/gleb226/MedelinBot?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/gleb226/MedelinBot?style=social)

![Commit Activity](https://img.shields.io/github/commit-activity/m/gleb226/MedelinBot)
![Last Commit](https://img.shields.io/github/last-commit/gleb226/MedelinBot)
![Code Size](https://img.shields.io/github/languages/code-size/gleb226/MedelinBot)

</div>

---

## 📄 Ліцензія

Цей проект ліцензовано під [MIT License](LICENSE).

```
MIT License

Copyright (c) 2024 MedelinBot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 👨‍💻 Автори

- **Gleb** - *Initial work* - [@gleb226](https://github.com/gleb226)

### Contributors

<a href="https://github.com/gleb226/MedelinBot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=gleb226/MedelinBot" />
</a>

---

## 📞 Контакти

- 📧 Email: support@medelinbot.com
- 💬 Telegram: [@MedelinBot](https://t.me/MedelinBot)
- 🐛 Issues: [GitHub Issues](https://github.com/gleb226/MedelinBot/issues)
- 📖 Документація: [Wiki](https://github.com/gleb226/MedelinBot/wiki)

---

## 🙏 Подяки

Особлива подяка всім, хто долучився до розвитку проекту:

- Python Telegram Bot спільноті
- Медичним консультантам
- Тестувальникам
- Open Source спільноті

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=gleb226/MedelinBot&type=Date)](https://star-history.com/#gleb226/MedelinBot&Date)

---

<div align="center">

**Зроблено з ❤️ для здорового майбутнього**

[⬆ Повернутися до початку](#-medelinbot)

</div>