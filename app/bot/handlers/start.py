from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import MenuButtonWebApp, WebAppInfo
from app.config import APP_URL
from app.database import (
    get_or_create_user,
    get_user_by_public_token,
    get_user_by_id
)
from app.bot.keyboards import get_main_menu_keyboard

router = Router(name="start_router")

@router.message(CommandStart())
async def handle_start(message: types.Message):
    user = message.from_user
    args = message.text.split(maxsplit=1)
    deep_link = args[1] if len(args) > 1 else ""

    # Check deep linking for friend's wishlist: /start w_abc123
    if deep_link.startswith("w_"):
        token = deep_link[2:]
        owner = await get_user_by_public_token(token)
        if owner and owner["is_public"]:
            owner_name = owner["first_name"] or owner["username"] or "друга"
            public_url = f"{APP_URL}/w/{token}"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=f"🎁 Открыть вишлист {owner_name}",
                        web_app=WebAppInfo(url=public_url)
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="🛍 Создать свой список покупок",
                        web_app=WebAppInfo(url=APP_URL)
                    )
                ]
            ])
            await message.answer(
                f"🎉 <b>Вишлист: {owner['wishlist_title']}</b>\n\n"
                f"👤 Автор: <b>{owner_name}</b>\n"
                f"📝 {owner['wishlist_description'] or 'Желания и подарки'}\n\n"
                f"Нажмите кнопку ниже, чтобы посмотреть список, забронировать подарок или перейти по ссылкам на товары:",
                reply_markup=kb
            )
            return

    # Regular user registration / welcome
    db_user = await get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    # Set Telegram Menu button next to input bar
    try:
        await message.bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(
                text="🛍 PlanCart App",
                web_app=WebAppInfo(url=APP_URL)
            )
        )
    except Exception:
        pass

    welcome_text = (
        f"👋 Привет, <b>{user.first_name or 'друг'}</b>!\n\n"
        f"Добро пожаловать в <b>PlanCart</b> — твой умный вишлист и персональный план покупок!\n\n"
        f"✨ <b>Что умеет бот:</b>\n"
        f"• 📱 <b>Полноценное приложение (Mini App)</b> — нажми кнопку ниже, чтобы управлять списком с удобным мобильным интерфейсом.\n"
        f"• 📸 <b>Фото, ссылки, цены и описания</b> — добавляй вещи с фото, ссылками на маркетплейсы, приоритетами и категориями.\n"
        f"• 🔗 <b>Публичный вишлист</b> — делись ссылкой с друзьями на праздники и дни рождения! Друзья могут бронировать подарки, чтобы не повторяться.\n"
        f"• ⚡️ <b>Быстрое добавление</b> — просто отправь боту ссылку на товар или фото прямо сюда в чат!"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(db_user["public_token"])
    )

@router.message(Command("help"))
async def handle_help(message: types.Message):
    help_text = (
        "💡 <b>Как пользоваться PlanCart:</b>\n\n"
        "🔹 <b>/app</b> — Открыть Telegram Mini App (полный интерфейс)\n"
        "🔹 <b>/add</b> — Быстро добавить товар через диалог в чате\n"
        "🔹 <b>/list</b> — Посмотреть текущий список покупок\n"
        "🔹 <b>/share</b> — Получить ссылку на свой публичный вишлист\n"
        "🔹 <b>/stats</b> — Узнать сумму запланированных и купленных вещей\n\n"
        "⚡️ <i>Лайфхак:</i> отправь боту ссылку на товар (Wildberries, Ozon, Amazon и др.) или фото — бот автоматически распознает и предложит сохранить в список!"
    )
    await message.answer(help_text)

@router.message(Command("app"))
async def handle_app_command(message: types.Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(
        "🚀 Запуск приложения PlanCart:",
        reply_markup=get_main_menu_keyboard(user["public_token"])
    )

@router.message(Command("share"))
async def handle_share_command(message: types.Message):
    user = await get_or_create_user(message.from_user.id)
    public_url = f"{APP_URL}/w/{user['public_token']}"
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="👀 Посмотреть мой вишлист", url=public_url)
        ],
        [
            types.InlineKeyboardButton(
                text="📤 Отправить другу в чат",
                switch_inline_query=f"Посмотри мой вишлист: {public_url}"
            )
        ]
    ])
    
    await message.answer(
        f"🎁 <b>Твоя публичная ссылка на вишлист:</b>\n\n"
        f"👉 <code>{public_url}</code>\n\n"
        f"Отправь её друзьям или родственникам! Они смогут посмотреть список твоих желаний с ценами, фото и забронировать подарки.",
        reply_markup=kb
    )
