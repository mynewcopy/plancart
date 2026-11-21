from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)
from app.config import APP_URL

def get_main_menu_keyboard(public_token: str = "") -> InlineKeyboardMarkup:
    web_app_url = f"{APP_URL}"
    public_url = f"{APP_URL}/w/{public_token}" if public_token else web_app_url
    
    keyboard = [
        [
            InlineKeyboardButton(
                text="📱 Открыть приложение (Mini App)",
                web_app=WebAppInfo(url=web_app_url)
            )
        ],
        [
            InlineKeyboardButton(
                text="🔗 Мой публичный вишлист",
                url=public_url
            ),
            InlineKeyboardButton(
                text="📤 Поделиться",
                switch_inline_query=f"Посмотри мой вишлист: {public_url}"
            )
        ],
        [
            InlineKeyboardButton(text="📋 Мой список", callback_data="bot_list_items"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="bot_stats")
        ],
        [
            InlineKeyboardButton(text="➕ Быстро добавить", callback_data="bot_quick_add")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_item_card_keyboard(item_id: int, status: str, url: str = None) -> InlineKeyboardMarkup:
    buttons = []
    
    row1 = []
    if url:
        row1.append(InlineKeyboardButton(text="🛒 В магазин", url=url))
        
    if status == "planned":
        row1.append(InlineKeyboardButton(text="✅ Куплено", callback_data=f"item_bought:{item_id}"))
    else:
        row1.append(InlineKeyboardButton(text="🔄 В план", callback_data=f"item_plan:{item_id}"))
    
    if row1:
        buttons.append(row1)
        
    buttons.append([
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"item_del:{item_id}"),
        InlineKeyboardButton(text="📱 Открыть в приложении", web_app=WebAppInfo(url=f"{APP_URL}"))
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
