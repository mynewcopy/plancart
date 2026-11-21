import io
import uuid
from pathlib import Path
from PIL import Image, ImageOps
from app.config import UPLOADS_DIR

ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "GIF"}

def process_and_save_image(image_bytes: bytes, max_dim: int = 1400, quality: int = 85) -> str:
    """
    Validates, auto-orients, resizes, and saves image as optimized JPEG.
    Returns relative path from DATA_DIR (e.g., 'uploads/{filename}.jpg').
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Check format
        fmt = (img.format or "").upper()
        if fmt not in ALLOWED_FORMATS:
            raise ValueError(f"Неподдерживаемый формат изображения: {fmt}")
        
        # Auto-orient EXIF tag (critical for phone cameras!)
        img = ImageOps.exif_transpose(img)
        
        # Convert RGBA / P to RGB with white background if saving as JPEG
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # Resize if dimensions exceed max_dim while maintaining aspect ratio
        w, h = img.size
        if w > max_dim or h > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        
        # Unique filename
        filename = f"{uuid.uuid4().hex}.jpg"
        save_path = UPLOADS_DIR / filename
        
        # Save optimized JPEG
        img.save(save_path, "JPEG", quality=quality, optimize=True)
        
        return f"uploads/{filename}"
    except Exception as e:
        raise ValueError(f"Ошибка обработки изображения: {e}")
