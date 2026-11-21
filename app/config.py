import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Storage configuration
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "plancart.db"

# Telegram Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Web server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

# Base URL for Web App and public wishlist links
# e.g., https://my-app.ngrok-free.app or https://plancart.example.com
# If not specified, falls back to http://localhost:{PORT}
APP_URL = os.getenv("APP_URL", f"http://localhost:{PORT}").rstrip("/")

# Secret token / salt for verification
SECRET_KEY = os.getenv("SECRET_KEY", "plancart-default-secret-salt-key-2026")

DEBUG = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")

# Max image size for uploads in bytes (10MB)
MAX_IMAGE_SIZE = 10 * 1024 * 1024
