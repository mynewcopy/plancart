import json
from aiohttp import web
from app.config import APP_URL, MAX_IMAGE_SIZE
from app.database import (
    get_or_create_user,
    get_user_by_id,
    get_user_by_public_token,
    update_user_profile,
    add_item,
    update_item,
    delete_item,
    get_item,
    get_user_items,
    add_item_photo,
    delete_item_photo,
    set_cover_photo,
    reserve_item,
    cancel_reservation,
    get_user_stats
)
from app.web.auth import authenticate_request
from app.web.metadata import extract_url_metadata
from app.utils.images import process_and_save_image

async def handle_get_me(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    db_user = await get_or_create_user(
        telegram_id=user["id"],
        username=user.get("username"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        photo_url=user.get("photo_url")
    )
    
    db_user["public_url"] = f"{APP_URL}/w/{db_user['public_token']}"
    return web.json_response({"ok": True, "user": db_user})

async def handle_update_me(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    updated = await update_user_profile(
        telegram_id=user["id"],
        is_public=data.get("is_public"),
        wishlist_title=data.get("wishlist_title"),
        wishlist_description=data.get("wishlist_description"),
        currency_pref=data.get("currency_pref"),
        regenerate_token=bool(data.get("regenerate_token", False))
    )
    updated["public_url"] = f"{APP_URL}/w/{updated['public_token']}"
    return web.json_response({"ok": True, "user": updated})

async def handle_get_items(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    status = request.query.get("status")
    category = request.query.get("category")
    search = request.query.get("search")
    
    items = await get_user_items(
        user_id=user["id"],
        status=status,
        category=category,
        search=search,
        include_private=True
    )
    return web.json_response({"ok": True, "items": items})

async def handle_create_item(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    title = (data.get("title") or "").strip()
    if not title:
        return web.json_response({"error": "Название предмета обязательно"}, status=400)
        
    price = float(data.get("price") or 0.0)
    currency = data.get("currency") or "₽"
    url = data.get("url")
    description = data.get("description")
    category = data.get("category") or "Другое"
    priority = int(data.get("priority") or 2)
    status = data.get("status") or "planned"
    is_private = bool(data.get("is_private", False))
    target_date = data.get("target_date")
    photos = data.get("photos") or []
    
    item = await add_item(
        user_id=user["id"],
        title=title,
        price=price,
        currency=currency,
        url=url,
        description=description,
        category=category,
        priority=priority,
        status=status,
        is_private=is_private,
        target_date=target_date,
        photos=photos
    )
    return web.json_response({"ok": True, "item": item})

async def handle_get_item(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    item_id = int(request.match_info["id"])
    item = await get_item(item_id)
    if not item or item["user_id"] != user["id"]:
        return web.json_response({"error": "Not found"}, status=404)
        
    return web.json_response({"ok": True, "item": item})

async def handle_update_item(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    item_id = int(request.match_info["id"])
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    updated = await update_item(
        item_id=item_id,
        user_id=user["id"],
        title=data.get("title"),
        price=data.get("price"),
        currency=data.get("currency"),
        url=data.get("url"),
        description=data.get("description"),
        category=data.get("category"),
        priority=data.get("priority"),
        status=data.get("status"),
        is_private=data.get("is_private"),
        target_date=data.get("target_date")
    )
    if not updated:
        return web.json_response({"error": "Предмет не найден или нет прав"}, status=404)
        
    return web.json_response({"ok": True, "item": updated})

async def handle_delete_item(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    item_id = int(request.match_info["id"])
    success = await delete_item(item_id=item_id, user_id=user["id"])
    if not success:
        return web.json_response({"error": "Предмет не найден или нет прав"}, status=404)
        
    return web.json_response({"ok": True, "deleted": True})

async def handle_upload_image(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    reader = await request.multipart()
    field = await reader.next()
    
    if not field:
        return web.json_response({"error": "Файл не передан"}, status=400)
        
    content = await field.read()
    if len(content) > MAX_IMAGE_SIZE:
        return web.json_response({"error": "Файл превышает 10 МБ"}, status=400)
        
    try:
        saved_rel_path = process_and_save_image(content)
        return web.json_response({"ok": True, "path": saved_rel_path, "url": f"/{saved_rel_path}"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def handle_parse_link(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    url = data.get("url")
    if not url:
        return web.json_response({"error": "URL обязателен"}, status=400)
        
    meta = await extract_url_metadata(url)
    return web.json_response({"ok": True, "metadata": meta})

async def handle_get_stats(request: web.Request) -> web.Response:
    user = await authenticate_request(request)
    if not user:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    stats = await get_user_stats(user["id"])
    return web.json_response({"ok": True, "stats": stats})

# Public endpoints
async def handle_get_public_wishlist(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    user = await get_user_by_public_token(token)
    if not user:
        return web.json_response({"error": "Вишлист не найден"}, status=404)
        
    if not user["is_public"]:
        return web.json_response({"error": "Этот вишлист скрыт владельцем"}, status=403)
        
    items = await get_user_items(
        user_id=user["id"],
        status="planned",
        include_private=False
    )
    
    # Hide private user details, leave only public info
    public_user = {
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "username": user["username"],
        "photo_url": user["photo_url"],
        "wishlist_title": user["wishlist_title"],
        "wishlist_description": user["wishlist_description"],
        "currency_pref": user["currency_pref"]
    }
    
    return web.json_response({
        "ok": True,
        "owner": public_user,
        "items": items
    })

async def handle_reserve_item(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    user = await get_user_by_public_token(token)
    if not user or not user["is_public"]:
        return web.json_response({"error": "Доступ запрещен"}, status=403)
        
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    item_id = int(data.get("item_id") or 0)
    name = (data.get("name") or "Друг").strip()
    comment = (data.get("comment") or "").strip()
    is_anonymous = bool(data.get("is_anonymous", False))
    
    item = await get_item(item_id)
    if not item or item["user_id"] != user["id"] or item["is_private"]:
        return web.json_response({"error": "Предмет не найден"}, status=404)
        
    if item["is_reserved"]:
        return web.json_response({"error": "Этот предмет уже забронирован кем-то другим"}, status=400)
        
    reservation = await reserve_item(
        item_id=item_id,
        reserved_by_name=name,
        reserved_comment=comment,
        is_anonymous=is_anonymous
    )
    return web.json_response({"ok": True, "reservation": reservation})

async def handle_unreserve_item(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    user = await get_user_by_public_token(token)
    if not user or not user["is_public"]:
        return web.json_response({"error": "Доступ запрещен"}, status=403)
        
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    item_id = int(data.get("item_id") or 0)
    item = await get_item(item_id)
    if not item or item["user_id"] != user["id"]:
        return web.json_response({"error": "Предмет не найден"}, status=404)
        
    await cancel_reservation(item_id)
    return web.json_response({"ok": True, "unreserved": True})
