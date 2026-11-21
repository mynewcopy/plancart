import hmac
import hashlib
import json
import urllib.parse
from typing import Optional, Dict, Any
from aiohttp import web
from app.config import BOT_TOKEN, DEBUG

def validate_telegram_init_data(init_data: str, bot_token: str) -> Optional[Dict[str, Any]]:
    """
    Validates Telegram WebApp initData string using HMAC-SHA256.
    Returns user dict if valid, None otherwise.
    """
    if not init_data or not bot_token:
        return None
        
    try:
        parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
        if "hash" not in parsed:
            return None
            
        received_hash = parsed["hash"][0]
        
        # Prepare data-check-string
        items = []
        for k, v in parsed.items():
            if k != "hash":
                items.append(f"{k}={v[0]}")
        items.sort()
        data_check_string = "\n".join(items)
        
        # secret_key = HMAC_SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if hmac.compare_digest(received_hash, calculated_hash):
            user_json = parsed.get("user", [None])[0]
            if user_json:
                return json.loads(user_json)
        return None
    except Exception:
        return None

async def authenticate_request(request: web.Request) -> Optional[Dict[str, Any]]:
    """
    Extracts and authenticates user from request headers or query params.
    Supports Telegram initData as well as fallback dev mode.
    """
    init_data = (
        request.headers.get("X-Telegram-Init-Data")
        or request.query.get("initData")
    )
    
    # Check Telegram initData with bot token
    if init_data and BOT_TOKEN:
        user_info = validate_telegram_init_data(init_data, BOT_TOKEN)
        if user_info:
            return user_info
            
    # Try parsing unverified user in dev / test mode
    if DEBUG:
        # If init_data is provided without valid bot token in dev mode
        if init_data:
            try:
                parsed = urllib.parse.parse_qs(init_data)
                if "user" in parsed:
                    return json.loads(parsed["user"][0])
            except Exception:
                pass
                
        # Dev user header / query param
        dev_user_id = request.headers.get("X-Dev-User-Id") or request.query.get("dev_user_id")
        if dev_user_id:
            try:
                uid = int(dev_user_id)
                return {
                    "id": uid,
                    "first_name": "Тестовый",
                    "last_name": "Пользователь",
                    "username": "test_user"
                }
            except ValueError:
                pass

    return None
