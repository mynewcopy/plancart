from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from app.database import (
    get_or_create_user,
    get_user_items,
    add_item,
    update_item,
    delete_item,
    get_item,
    get_user_stats
)
from app.web.metadata import extract_url_metadata
from app.bot.keyboards import get_main_menu_keyboard, get_item_card_keyboard
from app.config import APP_URL

router = Router(name="items_router")

PRIORITY_LABELS = {1: "💡 Идея", 2: "⭐️ Желательно", 3: "🔥 Очень хочу"}
STATUS_LABELS = {"planned": "📋 Запланировано", "bought": "✅ Куплено", "archived": "📦 Архив"}
CATEGORIES = ["Электроника", "Одежда", "Обувь", "Дом и дача", "Книги", "Спорт", "Красота", "Игры", "Хобби", "Другое"]

class QuickAddStates(StatesGroup):
    waiting_title = State()
    waiting_price = State()
    waiting_url = State()
    waiting_photo = State()


def format_price(price: float, currency: str = "₽") -> str:
    if price <= 0:
        return "Цена не указана"
    if price >= 1000:
        return f"{price:,.0f} {currency}".replace(",", " ")
    return f"{price:.0f} {currency}"

def format_item_text(item: dict) -> str:
    prio = PRIORITY_LABELS.get(item.get("priority", 2), "⭐️")
    status = STATUS_LABELS.get(item.get("status", "planned"), "📋")
    price = format_price(item.get("price", 0), item.get("currency", "₽"))
    
    text = (
        f"{prio} <b>{item['title']}</b>\n"
        f"💰 {price}  •  {status}\n"
    )
    if item.get("category") and item["category"] != "Другое":
        text += f"📂 {item['category']}\n"
    if item.get("description"):
        text += f"📝 {item['description'][:200]}\n"
    if item.get("url"):
        text += f"🔗 <a href='{item['url']}'>Ссылка на товар</a>\n"
    if item.get("is_reserved") and item.get("reservation"):
        r = item["reservation"]
        by_name = "Анонимно" if r["is_anonymous"] else r["by_name"]
        text += f"\n🔒 Забронировано: <i>{by_name}</i>"
    return text


@router.message(Command("list"))
async def handle_list_command(message: types.Message):
    user = await get_or_create_user(message.from_user.id)
    items = await get_user_items(user["id"], status="planned")
    
    if not items:
        await message.answer(
            "📋 <b>Список покупок пуст!</b>\n\n"
            "Начни добавлять желаемые товары через приложение или отправь /add",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="📱 Открыть приложение",
                    web_app=types.WebAppInfo(url=APP_URL)
                )
            ]])
        )
        return
    
    total = sum(i.get("price", 0) for i in items)
    currency = items[0].get("currency", "₽") if items else "₽"
    header = f"📋 <b>Список покупок</b> ({len(items)} позиций)\n💰 Итого: {format_price(total, currency)}\n\n"
    
    # Show up to 5 items in bot chat; rest available in app
    shown = items[:5]
    for item in shown:
        item_text = format_item_text(item)
        kb = get_item_card_keyboard(item["id"], item.get("status", "planned"), item.get("url"))
        try:
            if item.get("cover_photo"):
                from app.config import DATA_DIR
                photo_path = DATA_DIR / item["cover_photo"]
                if photo_path.exists():
                    with open(photo_path, "rb") as f:
                        await message.answer_photo(
                            photo=types.BufferedInputFile(f.read(), filename="photo.jpg"),
                            caption=item_text,
                            reply_markup=kb
                        )
                    continue
        except Exception:
            pass
        await message.answer(item_text, reply_markup=kb)
    
    if len(items) > 5:
        remaining = len(items) - 5
        await message.answer(
            f"<i>...и ещё {remaining} товаров. Открой приложение для полного просмотра.</i>",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="📱 Всё в приложении", web_app=types.WebAppInfo(url=APP_URL))
            ]])
        )

@router.message(Command("stats"))
async def handle_stats_command(message: types.Message):
    user = await get_or_create_user(message.from_user.id)
    stats = await get_user_stats(user["id"])
    
    planned_sum = stats.get("planned_sum") or 0
    bought_sum = stats.get("bought_sum") or 0
    currency = user.get("currency_pref", "₽")
    
    text = (
        f"📊 <b>Статистика твоего вишлиста</b>\n\n"
        f"📋 Запланировано: <b>{stats.get('planned_count', 0)}</b> товаров\n"
        f"✅ Куплено: <b>{stats.get('bought_count', 0)}</b> товаров\n"
        f"📦 Всего позиций: <b>{stats.get('total_count', 0)}</b>\n\n"
        f"💰 Запланировано на сумму: <b>{format_price(planned_sum, currency)}</b>\n"
        f"🎉 Уже потрачено: <b>{format_price(bought_sum, currency)}</b>\n"
    )
    if stats.get("reserved_count", 0) > 0:
        text += f"\n🎁 Забронировано друзьями: <b>{stats['reserved_count']}</b>\n"
    
    if stats.get("categories"):
        text += "\n📂 <b>По категориям:</b>\n"
        for cat in stats["categories"][:5]:
            text += f"  • {cat['category']}: {cat['count']} шт. — {format_price(cat.get('total_price') or 0, currency)}\n"
    
    await message.answer(text)


@router.message(Command("add"))
async def handle_add_command(message: types.Message, state: FSMContext):
    await state.set_state(QuickAddStates.waiting_title)
    await message.answer(
        "➕ <b>Быстрое добавление товара</b>\n\n"
        "Введи <b>название</b> товара или отправь <b>ссылку</b> на него (Wildberries, Ozon, Amazon и т.д.):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@router.message(QuickAddStates.waiting_title)
async def handle_quick_add_title(message: types.Message, state: FSMContext):
    text_input = message.text or ""
    
    # Check if it's a URL
    if text_input.strip().startswith(("http://", "https://", "www.")):
        await message.answer("🔄 Загружаю информацию по ссылке...")
        meta = await extract_url_metadata(text_input.strip())
        
        if meta.get("title"):
            await state.update_data(
                url=meta["url"],
                title=meta["title"],
                description=meta.get("description", ""),
                price=meta.get("price") or 0.0,
                image_url=meta.get("image_url", "")
            )
            
            preview = (
                f"✅ <b>Найдено:</b>\n"
                f"📌 {meta['title']}\n"
            )
            if meta.get("price"):
                preview += f"💰 {format_price(meta['price'], '₽')}\n"
            if meta.get("description"):
                preview += f"📝 {meta['description'][:100]}...\n"
            
            preview += "\n💰 <b>Введи цену в рублях</b> или нажми /skip чтобы пропустить:"
            
            await state.set_state(QuickAddStates.waiting_price)
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⏭ Пропустить цену", callback_data="skip_price")]
            ])
            await message.answer(preview, reply_markup=kb)
        else:
            await state.update_data(url=text_input.strip())
            await message.answer(
                "⚠️ Не удалось автоматически получить информацию о товаре.\n\n"
                "Введи <b>название</b> товара вручную:"
            )
    else:
        await state.update_data(title=text_input.strip(), url="")
        await state.set_state(QuickAddStates.waiting_price)
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⏭ Пропустить цену", callback_data="skip_price")]
        ])
        await message.answer(
            "💰 Введи <b>цену в рублях</b> (или нажми кнопку чтобы пропустить):",
            reply_markup=kb
        )

@router.message(QuickAddStates.waiting_price, F.text)
async def handle_quick_add_price(message: types.Message, state: FSMContext):
    text = (message.text or "").replace(",", ".").replace(" ", "").strip()
    try:
        price = float(text)
    except ValueError:
        price = 0.0
    
    await state.update_data(price=price)
    await _ask_for_photo(message, state)

@router.callback_query(F.data == "skip_price", QuickAddStates.waiting_price)
async def handle_skip_price(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(price=0.0)
    await callback.answer()
    await _ask_for_photo(callback.message, state)

async def _ask_for_photo(message: types.Message, state: FSMContext):
    await state.set_state(QuickAddStates.waiting_photo)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⏭ Пропустить фото", callback_data="skip_photo")]
    ])
    await message.answer(
        "📸 Отправь <b>фото товара</b> (необязательно) или нажми кнопку для пропуска:",
        reply_markup=kb
    )

@router.message(QuickAddStates.waiting_photo, F.photo)
async def handle_quick_add_photo(message: types.Message, state: FSMContext):
    from app.utils.images import process_and_save_image
    from app.config import DATA_DIR
    
    # Get the largest available photo
    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)
    
    try:
        import io
        import aiohttp
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_info.file_path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                image_bytes = await resp.read()
        
        saved_path = process_and_save_image(image_bytes)
        await state.update_data(photo_path=saved_path)
    except Exception as e:
        await state.update_data(photo_path=None)
    
    await _save_quick_add_item(message, state)

@router.callback_query(F.data == "skip_photo", QuickAddStates.waiting_photo)
async def handle_skip_photo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await _save_quick_add_item(callback.message, state)

async def _save_quick_add_item(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    title = data.get("title") or "Без названия"
    price = float(data.get("price") or 0.0)
    url = data.get("url") or None
    description = data.get("description") or None
    photo_path = data.get("photo_path")
    photos = [photo_path] if photo_path else []
    
    item = await add_item(
        user_id=message.chat.id,
        title=title,
        price=price,
        url=url,
        description=description,
        photos=photos
    )
    
    text = (
        f"✅ <b>Добавлено в список!</b>\n\n"
        f"{format_item_text(item)}\n\n"
        f"<i>Открой приложение для настройки категории, приоритета и добавления ещё фото.</i>"
    )
    kb = get_item_card_keyboard(item["id"], "planned", url)
    
    if photo_path and item.get("cover_photo"):
        from app.config import DATA_DIR
        from pathlib import Path
        try:
            fp = DATA_DIR / photo_path
            if fp.exists():
                with open(fp, "rb") as f:
                    await message.answer_photo(
                        photo=types.BufferedInputFile(f.read(), filename="photo.jpg"),
                        caption=text,
                        reply_markup=kb
                    )
                return
        except Exception:
            pass
    
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("item_bought:"))
async def handle_item_bought(callback: types.CallbackQuery):
    item_id = int(callback.data.split(":")[1])
    await update_item(item_id=item_id, user_id=callback.from_user.id, status="bought")
    await callback.answer("✅ Отмечено как купленное!")
    await callback.message.edit_reply_markup(
        reply_markup=get_item_card_keyboard(item_id, "bought")
    )

@router.callback_query(F.data.startswith("item_plan:"))
async def handle_item_plan(callback: types.CallbackQuery):
    item_id = int(callback.data.split(":")[1])
    await update_item(item_id=item_id, user_id=callback.from_user.id, status="planned")
    await callback.answer("📋 Возвращено в план!")
    await callback.message.edit_reply_markup(
        reply_markup=get_item_card_keyboard(item_id, "planned")
    )

@router.callback_query(F.data.startswith("item_del:"))
async def handle_item_delete(callback: types.CallbackQuery):
    item_id = int(callback.data.split(":")[1])
    
    confirm_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"item_del_ok:{item_id}"),
            types.InlineKeyboardButton(text="❌ Отмена", callback_data="del_cancel")
        ]
    ])
    await callback.answer()
    await callback.message.answer("⚠️ Удалить этот товар из списка?", reply_markup=confirm_kb)

@router.callback_query(F.data.startswith("item_del_ok:"))
async def handle_item_delete_confirm(callback: types.CallbackQuery):
    item_id = int(callback.data.split(":")[1])
    success = await delete_item(item_id=item_id, user_id=callback.from_user.id)
    if success:
        await callback.answer("🗑 Удалено!")
        await callback.message.edit_text("🗑 <b>Товар удалён из списка.</b>")
    else:
        await callback.answer("❌ Ошибка при удалении")

@router.callback_query(F.data == "del_cancel")
async def handle_delete_cancel(callback: types.CallbackQuery):
    await callback.answer("Отменено")
    await callback.message.delete()

@router.callback_query(F.data == "bot_list_items")
async def handle_bot_list(callback: types.CallbackQuery):
    await callback.answer()
    await handle_list_command(callback.message)

@router.callback_query(F.data == "bot_stats")
async def handle_bot_stats_callback(callback: types.CallbackQuery):
    await callback.answer()
    await handle_stats_command(callback.message)

@router.callback_query(F.data == "bot_quick_add")
async def handle_bot_quick_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(QuickAddStates.waiting_title)
    await callback.message.answer(
        "➕ <b>Добавление товара</b>\n\nОтправь название или ссылку на товар:"
    )


# Auto-detect links sent to chat
@router.message(F.text.regexp(r"https?://\S+"))
async def handle_link_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return  # Already in a dialog
    
    url = message.text.strip().split()[0]
    await message.answer("🔄 Распознаю ссылку, загружаю данные о товаре...")
    meta = await extract_url_metadata(url)
    
    if meta.get("title"):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Добавить в список", callback_data=f"add_from_url:{url[:200]}"),
                types.InlineKeyboardButton(text="❌ Отмена", callback_data="del_cancel")
            ]
        ])
        preview_text = (
            f"🛍 <b>Найден товар:</b>\n\n"
            f"📌 <b>{meta['title']}</b>\n"
        )
        if meta.get("price"):
            preview_text += f"💰 {format_price(meta['price'], '₽')}\n"
        if meta.get("description"):
            preview_text += f"📝 {meta['description'][:150]}...\n"
        preview_text += f"\n🔗 <a href='{meta['url']}'>Открыть</a>"
        
        await message.answer(preview_text, reply_markup=kb)
    else:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="📱 Добавить в приложении",
                web_app=types.WebAppInfo(url=APP_URL)
            )]
        ])
        await message.answer(
            "⚠️ Не удалось загрузить данные о товаре по этой ссылке.\n"
            "Попробуй добавить через приложение вручную.",
            reply_markup=kb
        )

@router.callback_query(F.data.startswith("add_from_url:"))
async def handle_add_from_url(callback: types.CallbackQuery, state: FSMContext):
    url = callback.data[len("add_from_url:"):]
    await callback.answer("⏳ Добавляю...")
    
    meta = await extract_url_metadata(url)
    title = meta.get("title") or url
    price = float(meta.get("price") or 0.0)
    description = meta.get("description") or ""
    
    item = await add_item(
        user_id=callback.from_user.id,
        title=title[:200],
        price=price,
        url=meta.get("url") or url,
        description=description[:500] if description else None
    )
    
    text = (
        f"✅ <b>Добавлено в список покупок!</b>\n\n"
        f"{format_item_text(item)}"
    )
    kb = get_item_card_keyboard(item["id"], "planned", meta.get("url") or url)
    await callback.message.edit_text(text, reply_markup=kb)
