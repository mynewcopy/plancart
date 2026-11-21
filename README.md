# 🛍 PlanCart — Telegram Wishlist Bot + Mini App

Telegram-бот и полноценное **Mini App** (Telegram WebApp) для управления списком желаемых покупок / вишлистом.

---

## ✨ Возможности

| Функция | Описание |
|---|---|
| 📱 **Mini App** | Мобильное веб-приложение прямо в Telegram |
| 📸 **Фото товаров** | Загрузка нескольких фото, выбор обложки |
| 🔗 **Ссылки** | Вставь URL — бот автоматически получает название и цену |
| 🏷 **Категории** | Электроника, Одежда, Обувь, Дом, Книги и другие |
| 🔥 **Приоритеты** | 💡 Идея / ⭐ Желательно / 🔥 Очень хочу |
| ✅ **Статусы** | Запланировано → Куплено → Архив |
| 🌐 **Публичный вишлист** | Поделись ссылкой с друзьями |
| 🎁 **Бронирование** | Друзья бронируют подарки, чтобы не повторяться |
| 📊 **Статистика** | Сумма запланированных и купленных товаров |
| 🤖 **Telegram-бот** | Быстрое добавление, просмотр и управление прямо в чате |

---

## 🚀 Быстрый старт

### 1. Клонируй и установи зависимости

```bash
pip install -r requirements.txt
```

### 2. Настрой `.env`

```bash
cp .env.example .env
```

Заполни в `.env`:
```env
BOT_TOKEN=1234567890:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
APP_URL=https://ваш-домен.ngrok-free.app   # или VPS URL — HTTPS обязателен для Mini App!
```

### 3. Запусти

```bash
python main.py
```

---

## 🌐 Деплой для Mini App (нужен HTTPS)

Telegram **требует HTTPS** для Mini App. Варианты:

### Вариант A — ngrok (для разработки)
```bash
# Установи ngrok: https://ngrok.com/download
ngrok http 8080

# Скопируй URL вида https://abc123.ngrok-free.app
# Пропиши его в APP_URL в .env
```

### Вариант B — Railway / Render (бесплатный хостинг)
1. Создай проект на [railway.app](https://railway.app) или [render.com](https://render.com)
2. Подключи репозиторий, добавь переменные окружения (`BOT_TOKEN`, `APP_URL`)
3. Добавь команду запуска: `python main.py`

---

## 🤖 Команды бота

| Команда | Описание |
|---|---|
| `/start` | Старт и приветствие, открытие Mini App |
| `/app` | Открыть Mini App |
| `/add` | Добавить товар через диалог в чате |
| `/list` | Посмотреть список (до 5 товаров) |
| `/stats` | Статистика суммы |
| `/share` | Получить публичную ссылку |
| `/help` | Справка |

**Лайфхак:** отправь боту ссылку (ozon.ru, wildberries.ru, amazon.com...) и он автоматически предложит добавить товар!

---

## 🏗 Структура проекта

```
plancart/
├── main.py                  # Точка входа (бот + веб-сервер)
├── requirements.txt
├── .env.example
├── app/
│   ├── config.py            # Конфигурация из env
│   ├── database.py          # SQLite (aiosqlite) — все CRUD операции
│   ├── bot/
│   │   ├── bot_instance.py  # Экземпляры Bot и Dispatcher
│   │   ├── keyboards.py     # Inline клавиатуры
│   │   └── handlers/
│   │       ├── start.py     # /start, /share, /app
│   │       └── items.py     # /add, /list, /stats, inline callbacks, FSM
│   ├── web/
│   │   ├── app.py           # aiohttp роутер
│   │   ├── api.py           # REST API endpoints
│   │   ├── auth.py          # Telegram initData проверка
│   │   ├── metadata.py      # OpenGraph парсинг ссылок
│   │   └── static/
│   │       ├── index.html   # Mini App (мой список)
│   │       ├── public.html  # Публичный вишлист
│   │       ├── css/
│   │       │   ├── app.css
│   │       │   └── public.css
│   │       └── js/
│   │           ├── app.js
│   │           └── public.js
│   └── utils/
│       └── images.py        # Обработка и сохранение изображений (Pillow)
└── data/                    # (создаётся автоматически)
    ├── plancart.db          # SQLite база данных
    └── uploads/             # Загруженные изображения
```

---

## 🔑 Переменные окружения

| Переменная | Описание | Пример |
|---|---|---|
| `BOT_TOKEN` | Токен от @BotFather | `1234567890:AAFxxx` |
| `APP_URL` | HTTPS URL сервера (для Mini App и webhook) | `https://abc.ngrok-free.app` |
| `HOST` | Хост веб-сервера | `0.0.0.0` |
| `PORT` | Порт веб-сервера | `8080` |
| `DEBUG` | Включить dev-режим | `true` / `false` |
| `SECRET_KEY` | Соль для безопасности | длинная случайная строка |
| `DATA_DIR` | Путь к папке с данными | `./data` |

---

## 🎁 Публичный вишлист

Каждый пользователь получает уникальную ссылку вида:
```
https://your-app.com/w/ТОКЕН12
```

По этой ссылке друзья могут:
- Просматривать список желаний с фото и ценами
- Переходить в магазины по ссылкам
- **Бронировать подарки** (анонимно или с именем), чтобы не дарить одно и то же

Ссылку можно отправить через `/share` или прямо из Mini App.
