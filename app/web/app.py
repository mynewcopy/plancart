from pathlib import Path
from aiohttp import web
from app.config import UPLOADS_DIR, BASE_DIR
from app.web.api import (
    handle_get_me,
    handle_update_me,
    handle_get_items,
    handle_create_item,
    handle_get_item,
    handle_update_item,
    handle_delete_item,
    handle_upload_image,
    handle_parse_link,
    handle_get_stats,
    handle_get_public_wishlist,
    handle_reserve_item,
    handle_unreserve_item
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

async def index_handler(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")

async def public_wishlist_handler(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "public.html")

def create_web_app() -> web.Application:
    app = web.Application()
    
    # API endpoints
    app.router.add_get("/api/me", handle_get_me)
    app.router.add_post("/api/me", handle_update_me)
    app.router.add_get("/api/items", handle_get_items)
    app.router.add_post("/api/items", handle_create_item)
    app.router.add_get("/api/items/{id}", handle_get_item)
    app.router.add_put("/api/items/{id}", handle_update_item)
    app.router.add_patch("/api/items/{id}", handle_update_item)
    app.router.add_delete("/api/items/{id}", handle_delete_item)
    app.router.add_post("/api/upload", handle_upload_image)
    app.router.add_post("/api/parse-link", handle_parse_link)
    app.router.add_get("/api/stats", handle_get_stats)
    
    # Public wishlist endpoints
    app.router.add_get("/api/public/{token}", handle_get_public_wishlist)
    app.router.add_post("/api/public/{token}/reserve", handle_reserve_item)
    app.router.add_post("/api/public/{token}/unreserve", handle_unreserve_item)
    
    # HTML views
    app.router.add_get("/", index_handler)
    app.router.add_get("/w/{token}", public_wishlist_handler)
    
    # Static & Upload files
    app.router.add_static("/static/", path=STATIC_DIR, name="static")
    app.router.add_static("/uploads/", path=UPLOADS_DIR, name="uploads")
    
    return app
