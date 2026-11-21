import secrets
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import DB_PATH

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_connection():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db

async def init_db():
    async with get_db_connection() as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            photo_url TEXT,
            public_token TEXT UNIQUE NOT NULL,
            is_public INTEGER NOT NULL DEFAULT 1,
            wishlist_title TEXT NOT NULL DEFAULT 'Мой вишлист и покупки',
            wishlist_description TEXT DEFAULT 'Здесь собраны мои желанные покупки и идеи для подарков!',
            currency_pref TEXT NOT NULL DEFAULT '₽',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0.0,
            currency TEXT NOT NULL DEFAULT '₽',
            url TEXT,
            description TEXT,
            category TEXT NOT NULL DEFAULT 'Другое',
            priority INTEGER NOT NULL DEFAULT 2, -- 1: 💡 Идея, 2: ⭐️ Желательно, 3: 🔥 Очень хочу
            status TEXT NOT NULL DEFAULT 'planned', -- 'planned', 'bought', 'archived'
            is_private INTEGER NOT NULL DEFAULT 0, -- 0: видно в публичном списке, 1: скрыто
            target_date TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS item_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            original_url TEXT,
            telegram_file_id TEXT,
            is_cover INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL UNIQUE,
            reserved_by_name TEXT NOT NULL,
            reserved_by_user_id INTEGER,
            reserved_comment TEXT,
            is_anonymous INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_items_user_id ON items(user_id);
        CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
        CREATE INDEX IF NOT EXISTS idx_users_public_token ON users(public_token);
        CREATE INDEX IF NOT EXISTS idx_item_photos_item_id ON item_photos(item_id);
        """)
        await db.commit()

def generate_public_token() -> str:
    return secrets.token_urlsafe(10).replace("-", "").replace("_", "")[:12]

async def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    photo_url: Optional[str] = None
) -> Dict[str, Any]:
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (telegram_id,))
        row = await cursor.fetchone()
        
        if row:
            # Update user info if changed
            await db.execute("""
                UPDATE users 
                SET username = COALESCE(?, username),
                    first_name = COALESCE(?, first_name),
                    last_name = COALESCE(?, last_name),
                    photo_url = COALESCE(?, photo_url),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (username, first_name, last_name, photo_url, telegram_id))
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (telegram_id,))
            updated_row = await cursor.fetchone()
            return dict(updated_row)
        
        # Create new user
        token = generate_public_token()
        title = f"Вишлист {first_name or 'пользователя'}"
        await db.execute("""
            INSERT INTO users (id, username, first_name, last_name, photo_url, public_token, wishlist_title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (telegram_id, username, first_name, last_name, photo_url, token, title))
        await db.commit()
        
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (telegram_id,))
        new_row = await cursor.fetchone()
        return dict(new_row)

async def get_user_by_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_user_by_public_token(token: str) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT * FROM users WHERE public_token = ?", (token,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_user_profile(
    telegram_id: int,
    is_public: Optional[bool] = None,
    wishlist_title: Optional[str] = None,
    wishlist_description: Optional[str] = None,
    currency_pref: Optional[str] = None,
    regenerate_token: bool = False
) -> Dict[str, Any]:
    async with get_db_connection() as db:
        user = await get_user_by_id(telegram_id)
        if not user:
            raise ValueError(f"User {telegram_id} not found")
        
        new_token = generate_public_token() if regenerate_token else user["public_token"]
        new_is_public = int(is_public) if is_public is not None else user["is_public"]
        new_title = wishlist_title if wishlist_title is not None else user["wishlist_title"]
        new_desc = wishlist_description if wishlist_description is not None else user["wishlist_description"]
        new_curr = currency_pref if currency_pref is not None else user["currency_pref"]
        
        await db.execute("""
            UPDATE users 
            SET public_token = ?,
                is_public = ?,
                wishlist_title = ?,
                wishlist_description = ?,
                currency_pref = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_token, new_is_public, new_title, new_desc, new_curr, telegram_id))
        await db.commit()
        
        return await get_user_by_id(telegram_id)

async def add_item(
    user_id: int,
    title: str,
    price: float = 0.0,
    currency: str = "₽",
    url: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "Другое",
    priority: int = 2,
    status: str = "planned",
    is_private: bool = False,
    target_date: Optional[str] = None,
    photos: Optional[List[str]] = None
) -> Dict[str, Any]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            INSERT INTO items (
                user_id, title, price, currency, url, description,
                category, priority, status, is_private, target_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, title.strip(), float(price), currency.strip(),
            url.strip() if url else None,
            description.strip() if description else None,
            category.strip() or "Другое",
            int(priority), status, int(is_private),
            target_date.strip() if target_date else None
        ))
        item_id = cursor.lastrowid
        
        if photos:
            for idx, photo_path in enumerate(photos):
                is_cover = 1 if idx == 0 else 0
                await db.execute("""
                    INSERT INTO item_photos (item_id, file_path, is_cover, sort_order)
                    VALUES (?, ?, ?, ?)
                """, (item_id, photo_path, is_cover, idx))
        
        await db.commit()
        return await get_item(item_id)

async def update_item(
    item_id: int,
    user_id: int,
    title: Optional[str] = None,
    price: Optional[float] = None,
    currency: Optional[str] = None,
    url: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[int] = None,
    status: Optional[str] = None,
    is_private: Optional[bool] = None,
    target_date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT * FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
        item = await cursor.fetchone()
        if not item:
            return None
        
        new_title = title.strip() if title is not None else item["title"]
        new_price = float(price) if price is not None else item["price"]
        new_currency = currency.strip() if currency is not None else item["currency"]
        new_url = url.strip() if url is not None else item["url"]
        new_desc = description.strip() if description is not None else item["description"]
        new_cat = category.strip() if category is not None else item["category"]
        new_prio = int(priority) if priority is not None else item["priority"]
        new_status = status.strip() if status is not None else item["status"]
        new_priv = int(is_private) if is_private is not None else item["is_private"]
        new_target = target_date.strip() if target_date is not None else item["target_date"]
        
        await db.execute("""
            UPDATE items
            SET title = ?, price = ?, currency = ?, url = ?, description = ?,
                category = ?, priority = ?, status = ?, is_private = ?, target_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (new_title, new_price, new_currency, new_url, new_desc, new_cat, new_prio, new_status, new_priv, new_target, item_id, user_id))
        await db.commit()
        
        return await get_item(item_id)

async def delete_item(item_id: int, user_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
        await db.commit()
        return cursor.rowcount > 0

async def get_item(item_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT i.*, 
                   r.id as reservation_id,
                   r.reserved_by_name,
                   r.reserved_by_user_id,
                   r.reserved_comment,
                   r.is_anonymous,
                   r.created_at as reserved_at
            FROM items i
            LEFT JOIN reservations r ON i.id = r.item_id
            WHERE i.id = ?
        """, (item_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        
        item_dict = dict(row)
        
        # Load photos
        p_cursor = await db.execute("""
            SELECT * FROM item_photos WHERE item_id = ? ORDER BY is_cover DESC, sort_order ASC, id ASC
        """, (item_id,))
        p_rows = await p_cursor.fetchall()
        item_dict["photos"] = [dict(p) for p in p_rows]
        item_dict["cover_photo"] = item_dict["photos"][0]["file_path"] if item_dict["photos"] else None
        
        # Format reservation
        if item_dict.get("reservation_id"):
            item_dict["is_reserved"] = True
            item_dict["reservation"] = {
                "id": item_dict["reservation_id"],
                "by_name": item_dict["reserved_by_name"],
                "by_user_id": item_dict["reserved_by_user_id"],
                "comment": item_dict["reserved_comment"],
                "is_anonymous": bool(item_dict["is_anonymous"]),
                "reserved_at": item_dict["reserved_at"]
            }
        else:
            item_dict["is_reserved"] = False
            item_dict["reservation"] = None
            
        return item_dict

async def get_user_items(
    user_id: int,
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    include_private: bool = True
) -> List[Dict[str, Any]]:
    async with get_db_connection() as db:
        query = """
            SELECT i.*, 
                   r.id as reservation_id,
                   r.reserved_by_name,
                   r.reserved_by_user_id,
                   r.reserved_comment,
                   r.is_anonymous,
                   r.created_at as reserved_at
            FROM items i
            LEFT JOIN reservations r ON i.id = r.item_id
            WHERE i.user_id = ?
        """
        params: List[Any] = [user_id]
        
        if not include_private:
            query += " AND i.is_private = 0"
            
        if status:
            query += " AND i.status = ?"
            params.append(status)
            
        if category and category != "Все":
            query += " AND i.category = ?"
            params.append(category)
            
        if search:
            query += " AND (i.title LIKE ? OR i.description LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])
            
        query += " ORDER BY i.priority DESC, i.created_at DESC"
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        
        items = []
        for row in rows:
            it = dict(row)
            p_cursor = await db.execute("""
                SELECT * FROM item_photos WHERE item_id = ? ORDER BY is_cover DESC, sort_order ASC, id ASC
            """, (it["id"],))
            p_rows = await p_cursor.fetchall()
            it["photos"] = [dict(p) for p in p_rows]
            it["cover_photo"] = it["photos"][0]["file_path"] if it["photos"] else None
            
            if it.get("reservation_id"):
                it["is_reserved"] = True
                it["reservation"] = {
                    "id": it["reservation_id"],
                    "by_name": it["reserved_by_name"],
                    "by_user_id": it["reserved_by_user_id"],
                    "comment": it["reserved_comment"],
                    "is_anonymous": bool(it["is_anonymous"]),
                    "reserved_at": it["reserved_at"]
                }
            else:
                it["is_reserved"] = False
                it["reservation"] = None
                
            items.append(it)
            
        return items

async def add_item_photo(
    item_id: int,
    file_path: str,
    original_url: Optional[str] = None,
    telegram_file_id: Optional[str] = None,
    is_cover: bool = False
) -> Dict[str, Any]:
    async with get_db_connection() as db:
        if is_cover:
            await db.execute("UPDATE item_photos SET is_cover = 0 WHERE item_id = ?", (item_id,))
            
        cursor = await db.execute("""
            INSERT INTO item_photos (item_id, file_path, original_url, telegram_file_id, is_cover)
            VALUES (?, ?, ?, ?, ?)
        """, (item_id, file_path, original_url, telegram_file_id, 1 if is_cover else 0))
        await db.commit()
        photo_id = cursor.lastrowid
        
        p_cursor = await db.execute("SELECT * FROM item_photos WHERE id = ?", (photo_id,))
        row = await p_cursor.fetchone()
        return dict(row)

async def delete_item_photo(photo_id: int, item_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM item_photos WHERE id = ? AND item_id = ?", (photo_id, item_id))
        await db.commit()
        return cursor.rowcount > 0

async def set_cover_photo(photo_id: int, item_id: int) -> bool:
    async with get_db_connection() as db:
        await db.execute("UPDATE item_photos SET is_cover = 0 WHERE item_id = ?", (item_id,))
        cursor = await db.execute("UPDATE item_photos SET is_cover = 1 WHERE id = ? AND item_id = ?", (photo_id, item_id))
        await db.commit()
        return cursor.rowcount > 0

async def reserve_item(
    item_id: int,
    reserved_by_name: str,
    reserved_by_user_id: Optional[int] = None,
    reserved_comment: str = "",
    is_anonymous: bool = False
) -> Dict[str, Any]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            INSERT INTO reservations (item_id, reserved_by_name, reserved_by_user_id, reserved_comment, is_anonymous)
            VALUES (?, ?, ?, ?, ?)
        """, (item_id, reserved_by_name.strip(), reserved_by_user_id, reserved_comment.strip(), 1 if is_anonymous else 0))
        await db.commit()
        res_id = cursor.lastrowid
        
        r_cursor = await db.execute("SELECT * FROM reservations WHERE id = ?", (res_id,))
        row = await r_cursor.fetchone()
        return dict(row)

async def cancel_reservation(item_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM reservations WHERE item_id = ?", (item_id,))
        await db.commit()
        return cursor.rowcount > 0

async def get_user_stats(user_id: int) -> Dict[str, Any]:
    async with get_db_connection() as db:
        # Total counts and sums
        cursor = await db.execute("""
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN status = 'planned' THEN 1 ELSE 0 END) as planned_count,
                SUM(CASE WHEN status = 'bought' THEN 1 ELSE 0 END) as bought_count,
                SUM(CASE WHEN status = 'planned' THEN price ELSE 0 END) as planned_sum,
                SUM(CASE WHEN status = 'bought' THEN price ELSE 0 END) as bought_sum
            FROM items 
            WHERE user_id = ?
        """, (user_id,))
        stats = dict(await cursor.fetchone() or {})
        
        # Categories breakdown
        cat_cursor = await db.execute("""
            SELECT category, COUNT(*) as count, SUM(price) as total_price
            FROM items
            WHERE user_id = ?
            GROUP BY category
            ORDER BY count DESC
        """, (user_id,))
        cat_rows = await cat_cursor.fetchall()
        stats["categories"] = [dict(c) for c in cat_rows]
        
        # Reserved count
        res_cursor = await db.execute("""
            SELECT COUNT(*) as reserved_count
            FROM reservations r
            JOIN items i ON r.item_id = i.id
            WHERE i.user_id = ?
        """, (user_id,))
        res_row = await res_cursor.fetchone()
        stats["reserved_count"] = res_row["reserved_count"] if res_row else 0
        
        return stats
