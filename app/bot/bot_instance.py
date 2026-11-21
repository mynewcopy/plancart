from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import BOT_TOKEN

bot: Bot = None
dp: Dispatcher = None

def get_bot() -> Bot:
    global bot
    if bot is None and BOT_TOKEN:
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    return bot

def get_dispatcher() -> Dispatcher:
    global dp
    if dp is None:
        dp = Dispatcher(storage=MemoryStorage())
    return dp
