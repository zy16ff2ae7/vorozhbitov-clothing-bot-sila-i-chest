#!/usr/bin/env python3
"""Telegram storefront bot for a small clothing brand.

Thematic build: bold brand voice, hard contextual CTAs, channel-first funnel,
referral/giveaway viral loop, size waitlist, segmented broadcasts.

Python 3.11+, standard library only.
"""

from __future__ import annotations

import csv
import html
import io
import json
import logging
import mimetypes
import os
import random
import re
import signal
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent
LOG = logging.getLogger("brand_bot")
STOP_EVENT = threading.Event()
PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")
REF_RE = re.compile(r"^ref(\d{3,15})$")

# Attention markers used across the funnel. Kept in one place so the tone stays
# consistent and can be softened without hunting through the code.
FIRE = "\U0001F525"
BOLT = "⚡️"
BOX = "\U0001F4E6"
POINT = "\U0001F449"
CROWN = "\U0001F451"
SIREN = "\U0001F6A8"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def normalize_phone(value: str) -> str | None:
    phone = re.sub(r"[^0-9+]", "", value.strip())
    if phone.startswith("8") and len(re.sub(r"\D", "", phone)) == 11:
        phone = "+7" + phone[1:]
    elif not phone.startswith("+"):
        phone = "+" + phone
    return phone if PHONE_RE.fullmatch(phone) else None


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def ensure_catalog_exists(path: Path, seed_path: Path) -> bool:
    """Create a mutable catalog from the packaged seed on first start.

    Returns True when a new catalog was created. O_EXCL keeps parallel starts
    from overwriting a catalog another process has already initialized.
    """
    if path.exists():
        return False
    if not seed_path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}; seed not found: {seed_path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = seed_path.read_bytes()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "wb") as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())
    return True


def esc(value: Any) -> str:
    return html.escape(str(value))


TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", " ": "-", "_": "-",
}


def slugify(value: str, fallback: str = "item") -> str:
    """Build a callback-safe slug from a product name."""
    raw = value.strip().lower()
    slug = "".join(TRANSLIT.get(char, char) for char in raw)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")[:32]
    return slug or fallback


@dataclass(frozen=True)
class Settings:
    token: str
    admin_ids: frozenset[int]
    channel_url: str
    webapp_url: str
    manager_chat_id: int | None
    brand_name: str
    support_username: str
    database_path: Path
    catalog_path: Path
    health_port: int
    giveaway_min_invites: int
    privacy_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(BASE_DIR / ".env")
        token = os.getenv("BOT_TOKEN", "").strip()
        admin_ids = frozenset(
            int(item.strip())
            for item in os.getenv("ADMIN_IDS", "").split(",")
            if item.strip().isdigit()
        )
        manager_raw = os.getenv("MANAGER_CHAT_ID", "").strip()
        return cls(
            token=token,
            admin_ids=admin_ids,
            channel_url=os.getenv("CHANNEL_URL", "https://t.me/").strip(),
            webapp_url=os.getenv("WEBAPP_URL", "").strip(),
            manager_chat_id=int(manager_raw) if manager_raw.lstrip("-").isdigit() else None,
            brand_name=os.getenv("BRAND_NAME", "ВОРОЖБИТОВ | ОДЕЖДА").strip() or "ВОРОЖБИТОВ | ОДЕЖДА",
            support_username=os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@"),
            database_path=BASE_DIR / os.getenv("DATABASE_PATH", "data/bot.sqlite3"),
            catalog_path=BASE_DIR / os.getenv("CATALOG_PATH", "data/catalog.json"),
            health_port=int(os.getenv("PORT", "8080")),
            giveaway_min_invites=int(os.getenv("GIVEAWAY_MIN_INVITES", "3")),
            privacy_url=os.getenv("PRIVACY_URL", "").strip(),
        )


class Catalog:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, Any] = {}
        self.products_by_id: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw.get("categories"), list) or not isinstance(raw.get("products"), list):
            raise ValueError("catalog.json must contain categories and products arrays")
        category_ids: set[str] = set()
        for category in raw["categories"]:
            if not isinstance(category, dict) or not all(isinstance(category.get(key), str) for key in ("id", "name")):
                raise ValueError(f"Invalid category: {category}")
            category_id = category["id"]
            if not category_id or ":" in category_id or len(category_id.encode("utf-8")) > 48:
                raise ValueError(f"Category id is not callback-safe: {category_id}")
            if category_id in category_ids:
                raise ValueError(f"Duplicate category id: {category_id}")
            category_ids.add(category_id)
        products: dict[str, dict[str, Any]] = {}
        for product in raw["products"]:
            required = {"id", "category", "name", "price", "sizes", "description"}
            if not isinstance(product, dict) or not required.issubset(product):
                raise ValueError(f"Product is missing fields: {product}")
            product_id = str(product["id"])
            if not product_id or ":" in product_id or len(product_id.encode("utf-8")) > 40:
                raise ValueError(f"Product id is not callback-safe: {product_id}")
            if product_id in products:
                raise ValueError(f"Duplicate product id: {product_id}")
            if product["category"] not in category_ids:
                raise ValueError(f"Unknown category for product {product_id}: {product['category']}")
            if not all(isinstance(product.get(key), str) for key in ("name", "price", "description")):
                raise ValueError(f"Product text fields must be strings: {product_id}")
            if not isinstance(product["sizes"], list) or not product["sizes"]:
                raise ValueError(f"Product sizes must be a non-empty array: {product_id}")
            for size in product["sizes"]:
                callback = f"size:{product_id}:{size}"
                if ":" in str(size) or len(callback.encode("utf-8")) > 64:
                    raise ValueError(f"Size is not callback-safe for {product_id}: {size}")
            photo_url = str(product.get("photo_url", ""))
            if photo_url and not photo_url.startswith(("https://", "http://")):
                raise ValueError(f"photo_url must be HTTP(S) for {product_id}")
            products[product_id] = product
        raw.setdefault("lookbook", [])
        self.data = raw
        self.products_by_id = products

    @property
    def categories(self) -> list[dict[str, str]]:
        return self.data["categories"]

    @property
    def lookbook(self) -> list[dict[str, str]]:
        return [item for item in self.data.get("lookbook", []) if str(item.get("photo_url", "")).startswith("http")]

    def products_for_category(self, category: str) -> list[dict[str, Any]]:
        return [p for p in self.data["products"] if p["category"] == category and p.get("active", True)]

    def get(self, product_id: str) -> dict[str, Any] | None:
        product = self.products_by_id.get(product_id)
        return product if product and product.get("active", True) else None

    def get_any(self, product_id: str) -> dict[str, Any] | None:
        return self.products_by_id.get(product_id)

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def unique_id(self, name: str) -> str:
        base = slugify(name)
        candidate = base
        index = 2
        while candidate in self.products_by_id:
            candidate = f"{base}-{index}"
            index += 1
        return candidate

    def add_product(self, product: dict[str, Any]) -> dict[str, Any]:
        product = dict(product)
        product["id"] = self.unique_id(str(product["name"]))
        product.setdefault("active", True)
        product.setdefault("photo_url", "")
        self.data["products"].append(product)
        self.save()
        self.reload()
        return product

    def set_active(self, product_id: str, active: bool) -> bool:
        for product in self.data["products"]:
            if str(product.get("id")) == product_id:
                product["active"] = active
                self.save()
                self.reload()
                return True
        return False


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.local = threading.local()
        self._initialize()

    def connection(self) -> sqlite3.Connection:
        conn = getattr(self.local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=30000")
            self.local.conn = conn
        return conn

    def _initialize(self) -> None:
        conn = self.connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                phone TEXT,
                source TEXT,
                interest TEXT,
                referrer_id INTEGER,
                invited_count INTEGER NOT NULL DEFAULT 0,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                consent_at TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS states (
                user_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                size TEXT NOT NULL,
                phone TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                size TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, product_id, size)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
            CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);
            CREATE INDEX IF NOT EXISTS idx_users_interest ON users(interest);
            """
        )
        order_columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
        if "request_id" not in order_columns:
            conn.execute("ALTER TABLE orders ADD COLUMN request_id TEXT")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_request_id ON orders(request_id)")
        if "quantity" not in order_columns:
            conn.execute("ALTER TABLE orders ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
        user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "referrer_id" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        if "invited_count" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN invited_count INTEGER NOT NULL DEFAULT 0")
        if "consent_at" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN consent_at TEXT")

    def upsert_user(self, telegram_user: dict[str, Any], source: str | None = None) -> tuple[bool, int | None]:
        """Create or refresh a user. Returns (is_new, referrer_id).

        A referral is attributed only once: the first ref-source wins, so a
        repeated /start cannot inflate somebody's invite counter.
        """
        now = utc_now()
        user_id = int(telegram_user["id"])
        conn = self.connection()
        existing = conn.execute("SELECT user_id, referrer_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        is_new = existing is None
        referrer: int | None = None
        if source:
            match = REF_RE.match(source.strip())
            if match:
                candidate = int(match.group(1))
                if candidate != user_id:
                    referrer = candidate
        if not is_new and existing["referrer_id"] is not None:
            referrer = None
        if is_new:
            conn.execute(
                """
                INSERT INTO users(user_id, username, first_name, last_name, source, referrer_id, created_at, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    telegram_user.get("username"),
                    telegram_user.get("first_name", ""),
                    telegram_user.get("last_name", ""),
                    source,
                    referrer,
                    now,
                    now,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE users SET
                    username=?,
                    first_name=?,
                    last_name=?,
                    source=COALESCE(users.source, ?),
                    referrer_id=COALESCE(users.referrer_id, ?),
                    last_seen=?,
                    is_blocked=0
                WHERE user_id=?
                """,
                (
                    telegram_user.get("username"),
                    telegram_user.get("first_name", ""),
                    telegram_user.get("last_name", ""),
                    source,
                    referrer,
                    now,
                    user_id,
                ),
            )
        if referrer:
            conn.execute("UPDATE users SET invited_count=invited_count+1 WHERE user_id=?", (referrer,))
        return is_new, referrer

    def set_phone(self, user_id: int, phone: str) -> None:
        self.connection().execute("UPDATE users SET phone=? WHERE user_id=?", (phone, user_id))

    def set_interest(self, user_id: int, interest: str) -> None:
        self.connection().execute("UPDATE users SET interest=? WHERE user_id=?", (interest, user_id))

    def set_consent(self, user_id: int) -> None:
        self.connection().execute("UPDATE users SET consent_at=? WHERE user_id=?", (utc_now(), user_id))

    def has_consent(self, user_id: int) -> bool:
        row = self.connection().execute("SELECT consent_at FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and row["consent_at"])

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        return self.connection().execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

    def set_state(self, user_id: int, state: str, data: dict[str, Any] | None = None) -> None:
        self.connection().execute(
            """
            INSERT INTO states(user_id, state, data, updated_at) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET state=excluded.state, data=excluded.data, updated_at=excluded.updated_at
            """,
            (user_id, state, compact_json(data or {}), utc_now()),
        )

    def get_state(self, user_id: int) -> tuple[str, dict[str, Any]] | None:
        row = self.connection().execute("SELECT state, data FROM states WHERE user_id=?", (user_id,)).fetchone()
        return (row["state"], json.loads(row["data"])) if row else None

    def clear_state(self, user_id: int) -> None:
        self.connection().execute("DELETE FROM states WHERE user_id=?", (user_id,))

    def create_order(
        self,
        request_id: str,
        user_id: int,
        product: dict[str, Any],
        size: str,
        phone: str,
        quantity: int = 1,
    ) -> tuple[int, bool]:
        conn = self.connection()
        now = utc_now()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT id FROM orders WHERE request_id=?", (request_id,)).fetchone()
            if existing:
                conn.execute("COMMIT")
                return int(existing["id"]), False
            try:
                safe_quantity = max(1, min(int(quantity), 20))
            except (TypeError, ValueError):
                safe_quantity = 1
            cursor = conn.execute(
                """
                INSERT INTO orders(request_id, user_id, product_id, product_name, size, phone, quantity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (request_id, user_id, str(product["id"]), product["name"], size, phone, safe_quantity, now),
            )
            order_id = int(cursor.lastrowid)
            conn.execute("DELETE FROM states WHERE user_id=?", (user_id,))
            conn.execute(
                "INSERT INTO events(user_id, event, payload, created_at) VALUES (?, ?, ?, ?)",
                (user_id, "order_created", compact_json({"order_id": order_id, "product_id": product["id"]}), now),
            )
            conn.execute("COMMIT")
            return order_id, True
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise

    def add_to_waitlist(self, user_id: int, product: dict[str, Any], size: str) -> bool:
        conn = self.connection()
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO waitlist(user_id, product_id, product_name, size, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, str(product["id"]), product["name"], size, utc_now()),
        )
        return cursor.rowcount > 0

    def waitlist_rows(self, limit: int = 20) -> list[sqlite3.Row]:
        return list(
            self.connection().execute(
                """
                SELECT w.*, u.username, u.first_name, u.phone
                FROM waitlist w JOIN users u ON u.user_id=w.user_id
                ORDER BY w.id DESC LIMIT ?
                """,
                (limit,),
            )
        )

    def waitlist_user_ids(self, product_id: str, size: str) -> list[int]:
        return [
            row[0]
            for row in self.connection().execute(
                "SELECT user_id FROM waitlist WHERE product_id=? AND size=?", (product_id, size)
            )
        ]

    def event(self, user_id: int | None, event: str, payload: dict[str, Any] | None = None) -> None:
        self.connection().execute(
            "INSERT INTO events(user_id, event, payload, created_at) VALUES (?, ?, ?, ?)",
            (user_id, event, compact_json(payload or {}), utc_now()),
        )

    def stats(self) -> dict[str, int]:
        conn = self.connection()
        return {
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "contacts": conn.execute("SELECT COUNT(*) FROM users WHERE phone IS NOT NULL").fetchone()[0],
            "orders": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            "orders_today": conn.execute(
                "SELECT COUNT(*) FROM orders WHERE substr(created_at, 1, 10)=?", (utc_now()[:10],)
            ).fetchone()[0],
            "referrals": conn.execute("SELECT COALESCE(SUM(invited_count), 0) FROM users").fetchone()[0],
            "waitlist": conn.execute("SELECT COUNT(*) FROM waitlist").fetchone()[0],
            "consents": conn.execute("SELECT COUNT(*) FROM users WHERE consent_at IS NOT NULL").fetchone()[0],
        }

    def recent_orders(self, limit: int = 10) -> list[sqlite3.Row]:
        return list(
            self.connection().execute(
                """
                SELECT o.*, u.username, u.first_name
                FROM orders o JOIN users u ON u.user_id=o.user_id
                ORDER BY o.id DESC LIMIT ?
                """,
                (limit,),
            )
        )

    def get_order(self, order_id: int) -> sqlite3.Row | None:
        return self.connection().execute(
            """
            SELECT o.*, u.username, u.first_name
            FROM orders o JOIN users u ON u.user_id=o.user_id
            WHERE o.id=?
            """,
            (order_id,),
        ).fetchone()

    def set_order_status(self, order_id: int, status: str) -> tuple[sqlite3.Row | None, bool]:
        allowed = {"new", "confirmed", "completed", "cancelled"}
        transitions = {
            "new": {"confirmed", "cancelled"},
            "confirmed": {"completed", "cancelled"},
            "completed": set(),
            "cancelled": set(),
        }
        if status not in allowed:
            raise ValueError(f"Unsupported order status: {status}")
        conn = self.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None, False
            current = str(row["status"])
            if current == status:
                conn.execute("COMMIT")
                return row, False
            if status not in transitions.get(current, set()):
                conn.execute("COMMIT")
                raise ValueError(f"Invalid order transition: {current} -> {status}")
            conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
            conn.execute(
                "INSERT INTO events(user_id, event, payload, created_at) VALUES (?, ?, ?, ?)",
                (row["user_id"], "order_status_changed", compact_json({"order_id": order_id, "status": status}), utc_now()),
            )
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return self.get_order(order_id), True

    def top_referrers(self, limit: int = 10) -> list[sqlite3.Row]:
        return list(
            self.connection().execute(
                """
                SELECT user_id, username, first_name, invited_count
                FROM users WHERE invited_count > 0
                ORDER BY invited_count DESC, user_id LIMIT ?
                """,
                (limit,),
            )
        )

    def broadcast_audience(self, segment: str) -> list[int]:
        conn = self.connection()
        if segment == "consent":
            rows = conn.execute("SELECT user_id FROM users WHERE is_blocked=0 AND consent_at IS NOT NULL")
        elif segment == "contacts":
            rows = conn.execute("SELECT user_id FROM users WHERE is_blocked=0 AND phone IS NOT NULL")
        elif segment == "buyers":
            rows = conn.execute(
                "SELECT DISTINCT user_id FROM orders WHERE user_id IN (SELECT user_id FROM users WHERE is_blocked=0)"
            )
        elif segment == "fresh":
            rows = conn.execute(
                "SELECT user_id FROM users WHERE is_blocked=0 AND phone IS NULL ORDER BY created_at DESC LIMIT 500"
            )
        elif segment.startswith("interest:"):
            interest = segment.split(":", 1)[1]
            rows = conn.execute("SELECT user_id FROM users WHERE is_blocked=0 AND interest=?", (interest,))
        else:
            rows = conn.execute("SELECT user_id FROM users WHERE is_blocked=0")
        return [row[0] for row in rows]

    def active_user_ids(self) -> list[int]:
        return [row[0] for row in self.connection().execute("SELECT user_id FROM users WHERE is_blocked=0")]

    def giveaway_pool(self, min_invites: int) -> list[int]:
        return [
            row[0]
            for row in self.connection().execute(
                "SELECT user_id FROM users WHERE is_blocked=0 AND invited_count >= ?", (min_invites,)
            )
        ]

    def mark_blocked(self, user_id: int) -> None:
        self.connection().execute("UPDATE users SET is_blocked=1 WHERE user_id=?", (user_id,))

    def export_users_csv(self) -> bytes:
        def safe_cell(value: Any) -> Any:
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
                return "'" + value
            return value

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "user_id",
                "username",
                "first_name",
                "last_name",
                "phone",
                "interest",
                "source",
                "referrer_id",
                "invited_count",
                "consent_at",
                "created_at",
                "last_seen",
            ]
        )
        for row in self.connection().execute(
            """
            SELECT user_id, username, first_name, last_name, phone, interest, source,
                   referrer_id, invited_count, consent_at, created_at, last_seen
            FROM users ORDER BY created_at
            """
        ):
            writer.writerow([safe_cell(value) for value in tuple(row)])
        return output.getvalue().encode("utf-8-sig")


class TelegramAPI:
    def __init__(self, token: str):
        self.base_url = f"https://api.telegram.org/bot{token}/"

    def call(self, method: str, payload: dict[str, Any] | None = None, timeout: int = 70) -> Any:
        body = json.dumps(payload or {}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + method,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram HTTP {exc.code}: {details}") from exc
        if not result.get("ok"):
            raise RuntimeError(f"Telegram API error: {result}")
        return result.get("result")

    def send_message(self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call("sendMessage", payload)

    def send_photo(self, chat_id: int, photo: str, caption: str, reply_markup: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call("sendPhoto", payload)

    def send_media_group(self, chat_id: int, photos: list[str], caption: str = "") -> Any:
        media = []
        for index, photo in enumerate(photos[:10]):
            item: dict[str, Any] = {"type": "photo", "media": photo}
            if index == 0 and caption:
                item["caption"] = caption
                item["parse_mode"] = "HTML"
            media.append(item)
        return self.call("sendMediaGroup", {"chat_id": chat_id, "media": media})

    def answer_callback(self, callback_id: str, text: str = "") -> None:
        self.call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})

    def send_document(self, chat_id: int, filename: str, content: bytes, caption: str = "") -> Any:
        boundary = "----WorkBuddyBoundary7MA4YWxk"
        fields = {"chat_id": str(chat_id), "caption": caption}
        chunks: list[bytes] = []
        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    value.encode("utf-8"),
                    b"\r\n",
                ]
            )
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode(),
                b"Content-Type: text/csv\r\n\r\n",
                content,
                b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )
        request = urllib.request.Request(
            self.base_url + "sendDocument",
            data=b"".join(chunks),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError(f"Telegram API error: {result}")
        return result.get("result")


def inline_keyboard(rows: Iterable[Iterable[tuple[str, str]]]) -> dict[str, Any]:
    keyboard = []
    for row in rows:
        buttons = []
        for label, target in row:
            if target.startswith("webapp:"):
                buttons.append({"text": label, "web_app": {"url": target.removeprefix("webapp:")}})
                continue
            key = "url" if target.startswith(("https://", "http://", "tg://")) else "callback_data"
            buttons.append({"text": label, key: target})
        keyboard.append(buttons)
    return {"inline_keyboard": keyboard}


def contact_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [[{"text": f"{BOX} Отправить номер", "request_contact": True}], [{"text": "Отмена"}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def remove_keyboard() -> dict[str, Any]:
    return {"remove_keyboard": True}


SEGMENT_LABELS = {
    "consent": "Дали согласие (безопасно)",
    "contacts": "Только с контактом",
    "buyers": "Только покупавшие",
    "fresh": "Новые без контакта",
    "all": "Вся база (есть и без согласия)",
}

ORDER_STATUS_LABELS = {
    "new": "новая",
    "confirmed": "подтверждена",
    "completed": "завершена",
    "cancelled": "отменена",
}

ORDER_STATUS_MESSAGES = {
    "confirmed": "Менеджер подтвердил наличие. Скоро с тобой свяжутся по оплате и доставке.",
    "completed": "Заказ завершён. Спасибо, что выбрал наш дроп.",
    "cancelled": "Заявка отменена. Если это ошибка — создай новую заявку из карточки вещи.",
}

# Шаги мастера добавления товара: что спрашиваем и в каком порядке.
ADD_STEPS = [
    ("name", "Название вещи? Например: DROP 002 HOODIE"),
    ("price", "Цена? Например: 9 900 ₽"),
    ("sizes", "Размеры через запятую. Например: S, M, L, XL"),
    ("description", "Описание — 1–2 фразы, чем цепляет вещь."),
    ("photo_url", "Ссылка на фото (HTTP/HTTPS). Или /skip, чтобы добавить позже."),
]
ADD_KEYS = [key for key, _ in ADD_STEPS]


class BrandBot:
    def __init__(self, settings: Settings, api: TelegramAPI, db: Database, catalog: Catalog):
        self.settings = settings
        self.api = api
        self.db = db
        self.catalog = catalog
        self.bot_username: str = ""

    # ------------------------------------------------------------------ utils

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.settings.admin_ids

    def cta(self, kind: str = "menu") -> str:
        brand = esc(self.settings.brand_name)
        if kind == "drop":
            return f"\n\n{FIRE} <b>ЖМИ: СМОТРЕТЬ ДРОП</b> — тираж маленький, потом не будет."
        if kind == "channel":
            return f"\n\n{POINT} Первым узнаешь всё в канале <b>{brand}</b>. Подпишись, иначе пропустишь."
        if kind == "size":
            return f"\n\n{SIREN} Нет твоего размера? <b>ЗАБРАТЬ РАЗМЕР</b> — вернётся, напишем первыми."
        return f"\n\n{BOLT} <b>ЗАЙТИ В ВИТРИНУ</b> и смотреть, что осталось."

    def ref_link(self, user_id: int) -> str:
        if not self.bot_username:
            return ""
        return f"https://t.me/{self.bot_username}?start=ref{user_id}"

    def public_asset_url(self, value: Any) -> str:
        """Turn a Mini App asset path into a public Telegram-readable URL."""
        asset = str(value or "").strip()
        if asset.startswith(("https://", "http://")):
            return asset
        if asset and self.settings.webapp_url.startswith("https://"):
            parsed = urllib.parse.urlparse(self.settings.webapp_url)
            base = f"{parsed.scheme}://{parsed.netloc}/"
            return urllib.parse.urljoin(base, asset.lstrip("/"))
        return ""

    # ------------------------------------------------------------------ menus

    def main_menu(self) -> dict[str, Any]:
        rows: list[list[tuple[str, str]]] = [
            [(f"{FIRE} СМОТРЕТЬ ДРОП", "catalog"), (f"{CROWN} LOOKBOOK", "lookbook")],
            [("Подобрать размер", "size_guide"), ("О бренде", "about")],
            [(f"{POINT} КАНАЛ БРЕНДА", self.settings.channel_url)],
            [("\U0001F514 УЗНАТЬ ПЕРВЫМ", "profile"), (f"{BOX} ПРИВЕСТИ ДРУГА", "referral")],
        ]
        if self.settings.webapp_url.startswith("https://"):
            rows.insert(0, [(f"{BOLT} ОТКРЫТЬ MINIAPP", f"webapp:{self.settings.webapp_url}")])
        return inline_keyboard(rows)

    def interest_menu(self) -> dict[str, Any]:
        rows = [[(category["name"].upper(), f"intr:{category['id']}")] for category in self.catalog.categories[:6]]
        rows.append([("Не знаю пока", "intr:skip")])
        return inline_keyboard(rows)

    # ------------------------------------------------------------------ flows

    def start(self, chat_id: int, user: dict[str, Any], payload: str = "") -> None:
        source = payload[:64] if payload else None
        is_new, referrer = self.db.upsert_user(user, source)
        user_id = int(user["id"])
        self.db.event(user_id, "start", {"source": source, "is_new": is_new})
        if referrer:
            self.db.event(referrer, "referral_joined", {"user_id": user_id})
            try:
                self.api.send_message(
                    referrer,
                    f"{FIRE} По твоей ссылке зашёл новый человек. Так держать — до розыгрыша один шаг.",
                )
            except Exception:
                LOG.debug("Could not notify referrer %s", referrer)
        name = esc(user.get("first_name") or "друг")

        if is_new:
            text = (
                f"{FIRE} <b>{esc(self.settings.brand_name)}</b>\n\n"
                f"{name}, ты попал в закрытую территорию бренда.\n"
                "Здесь первыми разбирают дропы. Тираж маленький, очередь — нет, "
                "берёт тот, кто успел.\n\n"
                "<b>ЧТО ТЕБЕ БЛИЖЕ?</b> Отметишь — будем бить точно в тебя, а не спамить всем подряд."
            )
            self.api.send_message(chat_id, text, self.interest_menu())
        else:
            text = (
                f"{BOLT} <b>{esc(self.settings.brand_name)}</b>\n\n"
                f"{name}, ты уже в базе. Значит, видишь дропы раньше остальных."
                + self.cta("drop")
            )
            self.api.send_message(chat_id, text, self.main_menu())

    def save_interest(self, chat_id: int, user_id: int, interest: str) -> None:
        if interest != "skip":
            self.db.set_interest(user_id, interest)
            self.db.event(user_id, "interest_set", {"interest": interest})
        text = (
            f"{FIRE} Принято.\n\n"
            "Теперь по делу. Вещи разбирают быстро — смотри, что осталось, "
            "и забирай размер, пока он есть."
            + self.cta("drop")
        )
        self.api.send_message(chat_id, text, self.main_menu())

    def show_catalog(self, chat_id: int, user_id: int) -> None:
        self.db.event(user_id, "catalog_open")
        rows = [[(category["name"].upper(), f"cat:{category['id']}")] for category in self.catalog.categories]
        rows.append([("Главное меню", "menu")])
        self.api.send_message(
            chat_id, f"{FIRE} <b>ВИТРИНА</b>\n\nВыбирай, что смотреть. Остатки — честные.", inline_keyboard(rows)
        )

    def show_category(self, chat_id: int, user_id: int, category_id: str) -> None:
        products = self.catalog.products_for_category(category_id)
        self.db.event(user_id, "category_open", {"category": category_id})
        if not products:
            self.api.send_message(
                chat_id,
                f"{SIREN} Здесь пока пусто. Дроп готовится.\n"
                "Подпишись на канал — узнаешь первым, а не когда всё разберут."
                + self.cta("channel"),
                inline_keyboard([[("Канал бренда", self.settings.channel_url)], [("Назад", "catalog")]]),
            )
            return
        rows = [[(f"{p['name']} — {p['price']}", f"product:{p['id']}")] for p in products]
        rows.append([("Назад к витрине", "catalog")])
        self.api.send_message(chat_id, f"{BOX} <b>В НАЛИЧИИ</b> — бери, пока есть:", inline_keyboard(rows))

    def show_product(self, chat_id: int, user_id: int, product_id: str) -> None:
        product = self.catalog.get(product_id)
        if not product:
            self.api.send_message(chat_id, "Вещь снята с продажи или уже разобрана.", self.main_menu())
            return
        self.db.event(user_id, "product_open", {"product_id": product_id})
        sizes = " · ".join(esc(str(size)) for size in product["sizes"])
        caption = (
            f"<b>{esc(product['name'])}</b>\n"
            f"<b>{esc(str(product['price']))}</b>\n\n"
            f"{esc(product['description'])}\n\n"
            f"Размеры: {sizes}"
            + self.cta("size")
        )
        keyboard = inline_keyboard(
            [
                [("ЗАБРАТЬ РАЗМЕР", f"want:{product_id}")],
                [("Нет моего размера", f"wait:{product_id}")],
                [("Назад", f"cat:{product['category']}")],
            ]
        )
        gallery = self.product_gallery(product)
        if len(gallery) > 1:
            # Альбом (перед / спина / раскладка), затем текст с кнопками:
            # sendMediaGroup не умеет inline-клавиатуру.
            try:
                self.api.send_media_group(chat_id, gallery)
            except Exception:
                LOG.exception("Failed to send product album %s", product_id)
                self.api.send_photo(chat_id, gallery[0], caption, keyboard)
                return
            self.api.send_message(chat_id, caption, keyboard)
            return
        photo = gallery[0] if gallery else ""
        if photo:
            self.api.send_photo(chat_id, photo, caption, keyboard)
        else:
            self.api.send_message(chat_id, caption, keyboard)

    def product_gallery(self, product: dict[str, Any]) -> list[str]:
        """Публичные URL фото товара: photo_url, затем images[], затем image. Без дублей, максимум 10."""
        seen: list[str] = []
        candidates: list[Any] = [product.get("photo_url")]
        images = product.get("images")
        if isinstance(images, list):
            candidates.extend(images)
        candidates.append(product.get("image"))
        for candidate in candidates:
            url = self.public_asset_url(candidate)
            if url and url not in seen:
                seen.append(url)
        return seen[:10]

    def choose_size(self, chat_id: int, user_id: int, product_id: str) -> None:
        product = self.catalog.get(product_id)
        if not product:
            self.api.send_message(chat_id, "Вещь больше недоступна.", self.main_menu())
            return
        sizes = [str(size) for size in product["sizes"]]
        rows = [[(size, f"size:{product_id}:{size}") for size in sizes[index:index + 4]] for index in range(0, len(sizes), 4)]
        rows.append([("Назад", f"product:{product_id}")])
        self.api.send_message(chat_id, f"{FIRE} Твой размер? Жми — и он твой.", inline_keyboard(rows))

    def select_size(self, chat_id: int, user_id: int, product_id: str, size: str, request_id: str) -> None:
        product = self.catalog.get(product_id)
        if not product or size not in [str(item) for item in product["sizes"]]:
            self.api.send_message(chat_id, "Этот вариант уже разобрали.", self.main_menu())
            return
        user = self.db.get_user(user_id)
        if user and user["phone"]:
            self.finish_order(chat_id, user_id, product, size, user["phone"], request_id)
            return
        self.ask_phone(
            chat_id,
            user_id,
            "awaiting_order_phone",
            {"product_id": product_id, "size": size, "request_id": request_id},
        )

    def ask_waitlist_size(self, chat_id: int, product_id: str) -> None:
        product = self.catalog.get(product_id)
        if not product:
            self.api.send_message(chat_id, "Вещь больше недоступна.", self.main_menu())
            return
        sizes = [str(size) for size in product["sizes"]]
        rows = [[(size, f"wsize:{product_id}:{size}") for size in sizes[index:index + 4]] for index in range(0, len(sizes), 4)]
        rows.append([("Назад", f"product:{product_id}")])
        self.api.send_message(
            chat_id,
            f"{SIREN} Какой размер ждёшь?\nВернётся — напишем первыми, до рассылки в канал.",
            inline_keyboard(rows),
        )

    def confirm_waitlist(self, chat_id: int, user_id: int, product_id: str, size: str) -> None:
        product = self.catalog.get(product_id)
        if not product:
            self.api.send_message(chat_id, "Вещь больше недоступна.", self.main_menu())
            return
        self.db.add_to_waitlist(user_id, product, size)
        self.db.event(user_id, "waitlist_add", {"product_id": product_id, "size": size})
        self.api.send_message(
            chat_id,
            f"{FIRE} Записал: <b>{esc(product['name'])}</b>, размер {esc(size)}.\n"
            "Как только вернётся — получишь сообщение раньше всех." + self.cta("channel"),
            self.main_menu(),
        )

    def finish_order(
        self,
        chat_id: int,
        user_id: int,
        product: dict[str, Any],
        size: str,
        phone: str,
        request_id: str,
    ) -> None:
        order_id, created = self.db.create_order(request_id, user_id, product, size, phone)
        if not created:
            self.api.send_message(chat_id, f"Заявка #{order_id} уже принята.", self.main_menu())
            return
        self.api.send_message(
            chat_id,
            f"{FIRE} <b>ЗАЯВКА #{order_id} ПРИНЯТА</b>\n\n"
            f"{esc(product['name'])}\n"
            f"Размер: {esc(size)}\n"
            f"Стоимость: {esc(str(product['price']))}\n\n"
            "Менеджер на связи — подтвердит наличие и оплату. Не отключай уведомления.",
            remove_keyboard(),
        )
        self.api.send_message(
            chat_id,
            "Пока ждёшь — глянь, что ещё живо:" + self.cta("drop"),
            self.main_menu(),
        )
        notify_chat = self.settings.manager_chat_id
        if notify_chat:
            user = self.db.get_user(user_id)
            username = f"@{user['username']}" if user and user["username"] else str(user_id)
            self.api.send_message(
                notify_chat,
                f"{FIRE} <b>НОВАЯ ЗАЯВКА #{order_id}</b>\n"
                f"Клиент: {esc(username)}\n"
                f"Вещь: {esc(product['name'])}\n"
                f"Размер: {esc(size)}\n"
                f"Телефон: {esc(phone)}",
            )

    def request_profile(self, chat_id: int, user_id: int) -> None:
        self.ask_phone(chat_id, user_id, "awaiting_profile_phone", {})

    def consent_text(self) -> str:
        text = (
            f"{BOX} <b>ОДНО ДЕЛО ПЕРЕД КОНТАКТОМ</b>\n\n"
            "Чтобы принять заявку и написать про дроп, нам нужны твой номер и "
            "согласие на обработку данных и на сообщения от бренда.\n\n"
            "Используем данные только для оформления заявки и связи по ней в рамках опубликованной политики. Отписаться можно одной кнопкой в любой момент."
        )
        if self.settings.privacy_url:
            text += f"\n\n{POINT} Политика: {esc(self.settings.privacy_url)}"
        return text

    def ask_phone(self, chat_id: int, user_id: int, next_state: str, next_data: dict[str, Any]) -> None:
        """Ask for a phone number, but demand consent first if we do not have it yet."""
        if self.db.has_consent(user_id):
            self.db.set_state(user_id, next_state, next_data)
            self.api.send_message(
                chat_id,
                f"{BOX} Оставь номер — менеджер подтвердит наличие, оплату и доставку.\n\n"
                "Можно кнопкой или просто написать цифрами.",
                contact_keyboard(),
            )
            return
        self.db.set_state(
            user_id,
            "awaiting_consent",
            {"next_state": next_state, "next_data": next_data},
        )
        self.api.send_message(
            chat_id,
            self.consent_text(),
            inline_keyboard([[("Согласен", "consent:yes")], [("Не сейчас", "consent:no")]]),
        )

    def accept_consent(self, chat_id: int, user_id: int) -> None:
        state = self.db.get_state(user_id)
        if not state or state[0] != "awaiting_consent":
            self.api.send_message(chat_id, "Не нашёл, к чему это относилось. Зайди заново.", self.main_menu())
            return
        next_state = str(state[1].get("next_state", "awaiting_profile_phone"))
        next_data = dict(state[1].get("next_data") or {})
        self.db.set_consent(user_id)
        self.db.event(user_id, "consent_given")
        self.db.set_state(user_id, next_state, next_data)
        self.api.send_message(
            chat_id,
            f"{FIRE} Принято. Теперь нужен номер."
            if next_state == "awaiting_order_phone"
            else f"{FIRE} Принято. Напишем про дроп и про твой размер.",
            contact_keyboard(),
        )

    def decline_consent(self, chat_id: int, user_id: int) -> None:
        state = self.db.get_state(user_id)
        was_order = bool(state and state[0] == "awaiting_consent"
                         and state[1].get("next_state") == "awaiting_order_phone")
        self.db.clear_state(user_id)
        if was_order:
            self.api.send_message(
                chat_id,
                "Без согласия мы не сможем принять заявку — номер хранить не имеем права.\n\n"
                "Каталог открыт, смотри спокойно. Если передумаешь — кнопка ниже." + self.cta("channel"),
                self.main_menu(),
            )
        else:
            self.api.send_message(
                chat_id,
                "Ок, контакт не храним. Дропы всё равно выходят в канале — там ничего не пропустишь."
                + self.cta("channel"),
                self.main_menu(),
            )

    def save_phone_and_continue(self, chat_id: int, user_id: int, phone: str) -> None:
        self.db.set_phone(user_id, phone)
        state = self.db.get_state(user_id)
        if state and state[0] == "awaiting_order_phone":
            product = self.catalog.get(str(state[1].get("product_id", "")))
            size = str(state[1].get("size", ""))
            request_id = str(state[1].get("request_id", f"phone:{user_id}:{product['id'] if product else ''}:{size}"))
            if product:
                self.finish_order(chat_id, user_id, product, size, phone, request_id)
                return
        self.db.clear_state(user_id)
        self.db.event(user_id, "contact_saved")
        self.api.send_message(
            chat_id,
            f"{FIRE} Контакт в базе.\nТеперь ты в списке тех, кто узнаёт первым." + self.cta("channel"),
            remove_keyboard(),
        )
        self.api.send_message(chat_id, "Главное меню:", self.main_menu())

    def show_referral(self, chat_id: int, user_id: int) -> None:
        user = self.db.get_user(user_id)
        invited = int(user["invited_count"]) if user else 0
        threshold = max(1, self.settings.giveaway_min_invites)
        link = self.ref_link(user_id)
        text = (
            f"{CROWN} <b>ПРИВЕДИ ДРУГА — ЗАБЕРИ ДРОП ПЕРВЫМ</b>\n\n"
            f"Приглашено: <b>{invited}</b>\n"
            f"До приоритета: <b>{max(0, threshold - invited)}</b>\n\n"
            "Кидаешь ссылку другу → он заходит в бота → ты поднимаешься в списке. "
            f"Набрал {threshold} — получаешь приоритет на следующий дроп и участие в розыгрыше."
        )
        if link:
            text += f"\n\n{POINT} Твоя ссылка:\n<code>{esc(link)}</code>"
        self.api.send_message(
            chat_id,
            text,
            inline_keyboard(
                [
                    [("Отправить другу", f"https://t.me/share/url?url={urllib.parse.quote(link or '', safe='')}")],
                    [("Главное меню", "menu")],
                ]
            ),
        )

    def show_lookbook(self, chat_id: int, user_id: int) -> None:
        self.db.event(user_id, "lookbook_open")
        photos = [
            photo
            for item in self.catalog.data.get("lookbook", [])
            if (photo := self.public_asset_url(item.get("photo_url") or item.get("image")))
        ]
        if not photos:
            self.api.send_message(
                chat_id,
                f"{CROWN} <b>LOOKBOOK</b>\n\nПервые образы снимаются. Они выйдут в канале раньше открытого релиза."
                + self.cta("channel"),
                inline_keyboard([[("Канал бренда", self.settings.channel_url)], [("Главное меню", "menu")]]),
            )
            return
        try:
            self.api.send_media_group(chat_id, photos, f"{CROWN} <b>LOOKBOOK</b>")
        except Exception:
            LOG.exception("Failed to send lookbook album")
            self.api.send_message(chat_id, "Не получилось отправить альбом. Загляни в канал — там всё выложим.", self.main_menu())
            return
        self.api.send_message(chat_id, "Понравилось? Тогда не жди — размеры разбирают." + self.cta("drop"), self.main_menu())

    def notify_waitlist(self, product_id: str, size: str) -> int:
        """Admin-triggered ping for a restocked size. Returns number of notified users."""
        delivered = 0
        product = self.catalog.get(product_id)
        if not product:
            return 0
        for recipient in self.db.waitlist_user_ids(product_id, size):
            try:
                self.api.send_message(
                    recipient,
                    f"{SIREN} <b>РАЗМЕР ВЕРНУЛСЯ</b>\n\n{esc(product['name'])} — размер {esc(size)} снова в наличии.\n"
                    "Бери сейчас: на всю базу написали одновременно.",
                    inline_keyboard([[("ЗАБРАТЬ", f"want:{product_id}")]]),
                )
                delivered += 1
                time.sleep(0.04)
            except Exception as exc:
                LOG.warning("Waitlist notify failed for %s: %s", recipient, exc)
        return delivered

    # ------------------------------------------------------------------ admin

    def order_status_keyboard(self, order_id: int, status: str) -> dict[str, Any] | None:
        rows: list[list[tuple[str, str]]] = []
        if status == "new":
            rows.append([("Подтвердить", f"order:{order_id}:confirmed")])
            rows.append([("Отменить", f"order:{order_id}:cancelled")])
        elif status == "confirmed":
            rows.append([("Завершить", f"order:{order_id}:completed")])
            rows.append([("Отменить", f"order:{order_id}:cancelled")])
        return inline_keyboard(rows) if rows else None

    def update_order_status(self, chat_id: int, order_id: int, status: str) -> None:
        try:
            order, changed = self.db.set_order_status(order_id, status)
        except ValueError as exc:
            self.api.send_message(chat_id, f"Не могу изменить заявку: {esc(exc)}")
            return
        if not order:
            self.api.send_message(chat_id, "Заявка не найдена.")
            return
        label = ORDER_STATUS_LABELS.get(status, status)
        if not changed:
            self.api.send_message(chat_id, f"Заявка #{order_id} уже имеет статус «{esc(label)}».")
            return
        try:
            self.api.send_message(
                int(order["user_id"]),
                f"{BOX} <b>ЗАЯВКА #{order_id}: {esc(label.upper())}</b>\n\n"
                f"{esc(order['product_name'])} · размер {esc(order['size'])} · {int(order['quantity'] or 1)} шт.\n"
                f"{esc(ORDER_STATUS_MESSAGES.get(status, 'Статус заявки обновлён.'))}",
                self.main_menu(),
            )
        except Exception as exc:
            LOG.warning("Could not notify user %s about order %s: %s", order["user_id"], order_id, exc)
        self.api.send_message(chat_id, f"Заявка #{order_id}: статус «{esc(label)}» сохранён.")

    def admin_panel(self, chat_id: int) -> None:
        self.api.send_message(
            chat_id,
            f"{BOLT} <b>ПАНЕЛЬ</b>\n\nЧто делаем?",
            inline_keyboard(
                [
                    [("Статистика", "adm:stats"), ("Заявки", "adm:orders")],
                    [(f"{BOX} Добавить вещь", "adm:add"), ("Лист ожидания", "adm:waitlist")],
                    [("Топ рефералов", "adm:top"), ("Экспорт базы", "adm:export")],
                    [("Перечитать каталог", "adm:reload")],
                ]
            ),
        )

    def admin_command(self, chat_id: int, user_id: int, text: str) -> bool:
        if not self.is_admin(user_id):
            return False
        command, _, argument = text.partition(" ")
        argument = argument.strip()
        if command == "/stats":
            stats = self.db.stats()
            self.api.send_message(
                chat_id,
                "<b>Статистика</b>\n\n"
                f"В базе: {stats['users']}\n"
                f"С контактом: {stats['contacts']}\n"
                f"Заявок всего: {stats['orders']}\n"
                f"Заявок сегодня: {stats['orders_today']}\n"
                f"Приведено друзей: {stats['referrals']}\n"
                f"В листе ожидания: {stats['waitlist']}\n"
                f"Дали согласие: {stats['consents']}",
            )
        elif command == "/orders":
            orders = self.db.recent_orders()
            if not orders:
                self.api.send_message(chat_id, "Заявок пока нет.")
            else:
                self.api.send_message(chat_id, "<b>Последние заявки</b>")
                for row in orders:
                    username = f"@{row['username']}" if row["username"] else row["first_name"]
                    status = str(row["status"])
                    label = ORDER_STATUS_LABELS.get(status, status)
                    text = (
                        f"<b>#{row['id']} · {esc(label.upper())}</b>\n"
                        f"{esc(row['product_name'])} · размер {esc(row['size'])} · {int(row['quantity'] or 1)} шт.\n"
                        f"Клиент: {esc(username or str(row['user_id']))}\n"
                        f"Телефон: {esc(row['phone'])}"
                    )
                    self.api.send_message(chat_id, text, self.order_status_keyboard(int(row["id"]), status))
        elif command == "/broadcast":
            if not argument:
                self.api.send_message(chat_id, "Использование: <code>/broadcast текст рассылки</code>")
            else:
                self.db.set_state(user_id, "broadcast_pending", {"text": argument})
                self.api.send_message(
                    chat_id,
                    f"<b>КОМУ ШЛЁМ?</b>\n\n{esc(argument)}",
                    self.segment_keyboard(),
                )
        elif command == "/restock":
            parts = argument.split()
            if len(parts) != 2:
                self.api.send_message(chat_id, "Использование: <code>/restock id_товара размер</code>")
            else:
                delivered = self.notify_waitlist(parts[0], parts[1])
                self.api.send_message(chat_id, f"Уведомлено по листу ожидания: {delivered}.")
        elif command == "/waitlist":
            rows = self.db.waitlist_rows()
            if not rows:
                self.api.send_message(chat_id, "Лист ожидания пуст.")
            else:
                lines = ["<b>Ждут размер</b>", ""]
                for row in rows:
                    username = f"@{row['username']}" if row["username"] else row["first_name"]
                    lines.append(f"{esc(row['product_name'])} · {esc(row['size'])} · {esc(username or row['user_id'])}")
                self.api.send_message(chat_id, "\n".join(lines))
        elif command == "/top":
            rows = self.db.top_referrers()
            if not rows:
                self.api.send_message(chat_id, "Никто пока никого не привёл.")
            else:
                lines = ["<b>Топ по приведённым друзьям</b>", ""]
                for index, row in enumerate(rows, start=1):
                    username = f"@{row['username']}" if row["username"] else row["first_name"]
                    lines.append(f"{index}. {esc(username or row['user_id'])} — {row['invited_count']}")
                self.api.send_message(chat_id, "\n".join(lines))
        elif command == "/giveaway":
            count = int(argument) if argument.isdigit() else 1
            pool = self.db.giveaway_pool(self.settings.giveaway_min_invites)
            if not pool:
                self.api.send_message(
                    chat_id,
                    f"Никто ещё не набрал {self.settings.giveaway_min_invites} приглашённых.",
                )
            else:
                winners = random.sample(pool, min(count, len(pool)))
                lines = [f"<b>Победители ({len(winners)})</b>", ""]
                for winner_id in winners:
                    user = self.db.get_user(winner_id)
                    username = f"@{user['username']}" if user and user["username"] else str(winner_id)
                    lines.append(f"{esc(username)} — id {winner_id}")
                    try:
                        self.api.send_message(
                            winner_id,
                            f"{CROWN} <b>ТЫ ВЫИГРАЛ</b>\n\n"
                            "Твоя ссылка сработала. Напиши менеджеру — заберёшь вещь из дропа первым.",
                        )
                    except Exception:
                        LOG.warning("Could not notify winner %s", winner_id)
                self.api.send_message(chat_id, "\n".join(lines))
        elif command in ("/add", "/new"):
            self.start_add_product(chat_id, user_id)
        elif command == "/hide":
            if not argument:
                self.api.send_message(chat_id, "Использование: <code>/hide id_товара</code>")
            elif self.catalog.set_active(argument, False):
                self.api.send_message(chat_id, f"Вещь {esc(argument)} скрыта из витрины.")
            else:
                self.api.send_message(chat_id, "Не нашёл такой id.")
        elif command == "/show":
            if not argument:
                self.api.send_message(chat_id, "Использование: <code>/show id_товара</code>")
            elif self.catalog.set_active(argument, True):
                self.api.send_message(chat_id, f"Вещь {esc(argument)} снова в витрине.")
            else:
                self.api.send_message(chat_id, "Не нашёл такой id.")
        elif command == "/export":
            self.api.send_document(chat_id, "users.csv", self.db.export_users_csv(), "Экспорт базы")
        elif command == "/reload":
            self.catalog.reload()
            self.api.send_message(chat_id, "Каталог перечитан без перезапуска.")
        elif command in ("/admin", "/panel"):
            self.admin_panel(chat_id)
        else:
            return False
        return True

    # ------------------------------------------------- добавление товара

    def start_add_product(self, chat_id: int, user_id: int) -> None:
        self.db.set_state(user_id, "admin_add", {"step": "category"})
        rows = [[(category["name"], f"addcat:{category['id']}")] for category in self.catalog.categories]
        rows.append([("Новая категория", "addcat:new")])
        rows.append([("Отмена", "admin:cancel")])
        self.api.send_message(chat_id, f"{BOX} Новая вещь. Куда её положим?", inline_keyboard(rows))

    def pick_add_category(self, chat_id: int, user_id: int, category_id: str) -> None:
        if category_id == "new":
            self.db.set_state(user_id, "admin_add", {"step": "new_category"})
            self.api.send_message(chat_id, "Название новой категории? Например: Верхняя одежда")
            return
        if not any(category["id"] == category_id for category in self.catalog.categories):
            self.api.send_message(chat_id, "Такой категории нет.", self.main_menu())
            return
        self.db.set_state(user_id, "admin_add", {"step": "name", "category": category_id})
        self.api.send_message(chat_id, ADD_STEPS[0][1])

    def handle_add_product_text(self, chat_id: int, user_id: int, text: str) -> bool:
        state = self.db.get_state(user_id)
        if not state or state[0] != "admin_add":
            return False
        data = dict(state[1])
        step = str(data.get("step", ""))

        if text.lower() in ("отмена", "cancel"):
            self.db.clear_state(user_id)
            self.api.send_message(chat_id, "Черновик выброшен.", self.main_menu())
            return True
        if text.startswith("/") and text.lower() != "/skip":
            # не путаем команды администратора с ответами мастера
            return False

        if step == "new_category":
            name = text.strip()
            if not name:
                return True
            base = slugify(name, "category")
            category_id = base
            index = 2
            existing = {category["id"] for category in self.catalog.categories}
            while category_id in existing:
                category_id = f"{base}-{index}"
                index += 1
            self.catalog.data["categories"].append({"id": category_id, "name": name})
            self.catalog.save()
            self.catalog.reload()
            data = {"step": "name", "category": category_id}
            self.db.set_state(user_id, "admin_add", data)
            self.api.send_message(chat_id, f"Категория «{esc(name)}» создана.\n\n{ADD_STEPS[0][1]}")
            return True

        if step not in ADD_KEYS:
            return False
        value = text.strip()
        if step == "photo_url" and value.lower() in ("/skip", "пропустить"):
            value = ""
        elif not value:
            self.api.send_message(chat_id, "Пусто не подойдёт. Напиши ещё раз или «Отмена».")
            return True
        if step == "sizes":
            sizes = [item.strip() for item in re.split(r"[,;/]", value) if item.strip()]
            if not sizes:
                self.api.send_message(chat_id, "Ни одного размера не распознал. Формат: S, M, L, XL")
                return True
            if any(":" in size or len(f"size:x:{size}".encode("utf-8")) > 64 for size in sizes):
                self.api.send_message(chat_id, "Слишком длинный размер или двоеточие. Напиши короче.")
                return True
            data["sizes"] = sizes
        else:
            data[step] = value

        position = ADD_KEYS.index(step) + 1
        if position < len(ADD_STEPS):
            data["step"] = ADD_KEYS[position]
            self.db.set_state(user_id, "admin_add", data)
            self.api.send_message(chat_id, ADD_STEPS[position][1])
            return True

        product = {
            "category": data.get("category", ""),
            "name": data.get("name", ""),
            "price": data.get("price", ""),
            "sizes": data.get("sizes", []),
            "description": data.get("description", ""),
            "photo_url": data.get("photo_url", ""),
            "active": True,
        }
        data["preview"] = product
        data["step"] = "confirm"
        self.db.set_state(user_id, "admin_add", data)
        sizes = " · ".join(esc(size) for size in product["sizes"])
        self.api.send_message(
            chat_id,
            f"<b>ПРОВЕРЬ ПЕРЕД ПУБЛИКАЦИЕЙ</b>\n\n"
            f"<b>{esc(product['name'])}</b>\n<b>{esc(product['price'])}</b>\n\n"
            f"{esc(product['description'])}\n\nРазмеры: {sizes}",
            inline_keyboard([[("ОПУБЛИКОВАТЬ", "add:publish")], [("Отмена", "admin:cancel")]]),
        )
        return True

    def publish_product(self, chat_id: int, user_id: int) -> None:
        state = self.db.get_state(user_id)
        if not state or state[0] != "admin_add" or not state[1].get("preview"):
            self.api.send_message(chat_id, "Черновик не найден. Начни заново: /add")
            return
        product = self.catalog.add_product(dict(state[1]["preview"]))
        self.db.clear_state(user_id)
        self.db.event(user_id, "product_added", {"product_id": product["id"]})
        self.api.send_message(
            chat_id,
            f"{FIRE} Опубликовано: <b>{esc(product['name'])}</b>\n"
            f"id: <code>{esc(product['id'])}</code>\n\n"
            "Вещь уже в витрине. Скрыть — <code>/hide id</code>.",
            inline_keyboard([[("Смотреть в витрине", f"product:{product['id']}")], [("Панель", "adm:panel")]]),
        )

    def segment_keyboard(self) -> dict[str, Any]:
        rows = [[(label, f"seg:{key}")] for key, label in SEGMENT_LABELS.items()]
        for category in self.catalog.categories[:6]:
            rows.append([(f"Интерес: {category['name']}", f"seg:interest:{category['id']}")])
        rows.append([("Отмена", "admin:cancel")])
        return inline_keyboard(rows)

    def preview_broadcast(self, chat_id: int, user_id: int, segment: str) -> None:
        state = self.db.get_state(user_id)
        if not state or state[0] != "broadcast_pending":
            self.api.send_message(chat_id, "Черновик рассылки не найден.")
            return
        text = str(state[1].get("text", "")).strip()
        audience = self.db.broadcast_audience(segment)
        self.db.set_state(user_id, "broadcast_pending", {"text": text, "segment": segment})
        label = SEGMENT_LABELS.get(segment, segment)
        self.api.send_message(
            chat_id,
            f"<b>ПРЕДПРОСМОТР</b>\n\n{esc(text)}\n\nАудитория: {label}\nПолучателей: {len(audience)}",
            inline_keyboard([[("ОТПРАВИТЬ", "admin:broadcast_confirm")], [("Отмена", "admin:cancel")]]),
        )

    def confirm_broadcast(self, chat_id: int, user_id: int) -> None:
        state = self.db.get_state(user_id)
        if not state or state[0] != "broadcast_pending":
            self.api.send_message(chat_id, "Черновик рассылки не найден.")
            return
        text = str(state[1].get("text", "")).strip()
        segment = str(state[1].get("segment", "all"))
        self.db.clear_state(user_id)
        delivered = 0
        failed = 0
        for recipient in self.db.broadcast_audience(segment):
            try:
                self.api.send_message(recipient, esc(text), self.main_menu())
                delivered += 1
                time.sleep(0.04)
            except Exception as exc:
                failed += 1
                if "blocked" in str(exc).lower() or "chat not found" in str(exc).lower():
                    self.db.mark_blocked(recipient)
                LOG.warning("Broadcast failed for %s: %s", recipient, exc)
        self.db.event(user_id, "broadcast_sent", {"delivered": delivered, "failed": failed, "segment": segment})
        self.api.send_message(chat_id, f"Готово. Доставлено: {delivered}. Ошибок: {failed}.")

    # ------------------------------------------------------------------ miniapp + input

    def handle_web_app_data(self, chat_id: int, user: dict[str, Any], raw_data: str) -> None:
        """Accept an order sent by Telegram Web App ``sendData``.

        The browser is never trusted with the price or product details: only
        active product ids and sizes from the server-side catalog are accepted.
        This keeps the miniapp convenient while the bot remains the source of
        truth for the order and manager notification.
        """
        user_id = int(user["id"])
        try:
            payload = json.loads(raw_data)
        except (TypeError, ValueError, json.JSONDecodeError):
            self.api.send_message(chat_id, "Не получилось прочитать заявку из витрины. Открой её ещё раз.", self.main_menu())
            return
        if not isinstance(payload, dict) or payload.get("type") != "order":
            self.api.send_message(chat_id, "Неизвестный формат заявки. Открой витрину заново.", self.main_menu())
            return
        if payload.get("consent") is not True:
            self.api.send_message(chat_id, "Без согласия на обработку данных заявку принять нельзя.", self.main_menu())
            return
        customer = payload.get("customer") if isinstance(payload.get("customer"), dict) else {}
        phone = normalize_phone(str(customer.get("phone", "")))
        if not phone:
            self.api.send_message(chat_id, "Проверь номер телефона в витрине и отправь заявку ещё раз.", self.main_menu())
            return
        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or not raw_items or len(raw_items) > 20:
            self.api.send_message(chat_id, "В заявке нет вещей или их слишком много. Проверь корзину.", self.main_menu())
            return

        valid_items: list[tuple[dict[str, Any], str, int]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            product = self.catalog.get(str(raw_item.get("product_id", "")))
            size = str(raw_item.get("size", ""))
            if not product or size not in {str(item) for item in product.get("sizes", [])}:
                continue
            try:
                quantity = max(1, min(int(raw_item.get("quantity", 1)), 20))
            except (TypeError, ValueError):
                quantity = 1
            valid_items.append((product, size, quantity))
        if not valid_items:
            self.api.send_message(chat_id, "Некоторые вещи уже закончились. Обнови витрину и выбери снова.", self.main_menu())
            return

        self.db.set_phone(user_id, phone)
        self.db.set_consent(user_id)
        self.db.event(
            user_id,
            "webapp_order_submitted",
            {"city": str(customer.get("city", ""))[:160], "items": len(valid_items), "name": str(customer.get("name", ""))[:80]},
        )
        request_base = re.sub(r"[^a-zA-Z0-9_-]", "", str(payload.get("request_id", "")))[:80] or f"web-{user_id}-{int(time.time())}"
        created_orders: list[tuple[int, dict[str, Any], str, int]] = []
        for index, (product, size, quantity) in enumerate(valid_items, start=1):
            order_id, created = self.db.create_order(
                f"{request_base}-{index}-{product['id']}-{size}",
                user_id,
                product,
                size,
                phone,
                quantity,
            )
            if created:
                created_orders.append((order_id, product, size, quantity))

        if not created_orders:
            self.api.send_message(chat_id, "Эта заявка уже была принята. Менеджер скоро свяжется с тобой.", self.main_menu())
            return
        order_lines = [
            f"• {esc(product['name'])} · {esc(size)} · {quantity} шт."
            for _, product, size, quantity in created_orders
        ]
        self.api.send_message(
            chat_id,
            f"{FIRE} <b>ЗАЯВКА ИЗ MINIAPP ПРИНЯТА</b>\n\n"
            + "\n".join(order_lines)
            + "\n\nМенеджер подтвердит наличие, оплату и доставку.",
            self.main_menu(),
        )
        if self.settings.manager_chat_id:
            name = str(customer.get("name", ""))[:80]
            city = str(customer.get("city", ""))[:160]
            manager_lines = [
                f"{FIRE} <b>НОВАЯ MINIAPP-ЗАЯВКА</b>",
                f"Клиент: {esc(name or user.get('first_name') or user_id)}",
                f"Телефон: {esc(phone)}",
                f"Город / доставка: {esc(city or 'не указано')}",
                "",
                *order_lines,
            ]
            try:
                self.api.send_message(self.settings.manager_chat_id, "\n".join(manager_lines))
            except Exception as exc:
                LOG.warning("Could not notify manager about Web App order: %s", exc)

    def handle_callback(self, callback: dict[str, Any]) -> None:
        callback_id = callback["id"]
        data = callback.get("data", "")
        user = callback["from"]
        chat = callback["message"]["chat"]
        chat_id = chat["id"]
        user_id = int(user["id"])
        if chat.get("type") != "private":
            self.api.answer_callback(callback_id, "Открой бота в личке")
            return
        self.db.upsert_user(user)
        self.api.answer_callback(callback_id)

        if data == "menu":
            self.api.send_message(chat_id, "Главное меню:", self.main_menu())
        elif data == "catalog":
            self.show_catalog(chat_id, user_id)
        elif data.startswith("intr:"):
            self.save_interest(chat_id, user_id, data.split(":", 1)[1])
        elif data.startswith("cat:"):
            self.show_category(chat_id, user_id, data.split(":", 1)[1])
        elif data.startswith("product:"):
            self.show_product(chat_id, user_id, data.split(":", 1)[1])
        elif data.startswith("want:"):
            self.choose_size(chat_id, user_id, data.split(":", 1)[1])
        elif data.startswith("size:"):
            _, product_id, size = data.split(":", 2)
            self.select_size(chat_id, user_id, product_id, size, f"callback:{callback_id}")
        elif data.startswith("wait:"):
            self.ask_waitlist_size(chat_id, data.split(":", 1)[1])
        elif data.startswith("wsize:"):
            _, product_id, size = data.split(":", 2)
            self.confirm_waitlist(chat_id, user_id, product_id, size)
        elif data == "profile":
            self.request_profile(chat_id, user_id)
        elif data == "consent:yes":
            self.accept_consent(chat_id, user_id)
        elif data == "consent:no":
            self.decline_consent(chat_id, user_id)
        elif data == "add:publish" and self.is_admin(user_id):
            self.publish_product(chat_id, user_id)
        elif data.startswith("addcat:") and self.is_admin(user_id):
            self.pick_add_category(chat_id, user_id, data.split(":", 1)[1])
        elif data == "referral":
            self.show_referral(chat_id, user_id)
        elif data == "lookbook":
            self.show_lookbook(chat_id, user_id)
        elif data == "about":
            self.api.send_message(
                chat_id,
                f"<b>{esc(self.settings.brand_name)}</b>\n\n"
                "Одежда для тех, кто не спрашивает разрешения быть заметным. "
                "Малые тиражи, городская форма, дропы без лишнего шума." + self.cta("channel"),
                self.main_menu(),
            )
        elif data == "size_guide":
            self.api.send_message(
                chat_id,
                "<b>КАК ВЗЯТЬ СВОЙ РАЗМЕР</b>\n\n"
                "Сними обхват груди и талии, сравни с сеткой в карточке вещи. "
                "Застрял между двумя — оставь заявку, менеджер подберёт по параметрам." + self.cta("size"),
                self.main_menu(),
            )
        elif data.startswith("seg:") and self.is_admin(user_id):
            self.preview_broadcast(chat_id, user_id, data.split(":", 1)[1])
        elif data == "admin:broadcast_confirm" and self.is_admin(user_id):
            self.confirm_broadcast(chat_id, user_id)
        elif data.startswith("order:") and self.is_admin(user_id):
            try:
                _, order_id, status = data.split(":", 2)
                self.update_order_status(chat_id, int(order_id), status)
            except (TypeError, ValueError):
                self.api.send_message(chat_id, "Некорректная команда для заявки.")
        elif data == "admin:cancel" and self.is_admin(user_id):
            self.db.clear_state(user_id)
            self.api.send_message(chat_id, "Отменено.")
        elif data.startswith("adm:") and self.is_admin(user_id):
            action = data.split(":", 1)[1]
            if action == "add":
                self.start_add_product(chat_id, user_id)
            elif action == "panel":
                self.admin_panel(chat_id)
            elif action == "stats":
                self.admin_command(chat_id, user_id, "/stats")
            elif action == "orders":
                self.admin_command(chat_id, user_id, "/orders")
            elif action == "waitlist":
                self.admin_command(chat_id, user_id, "/waitlist")
            elif action == "top":
                self.admin_command(chat_id, user_id, "/top")
            elif action == "export":
                self.admin_command(chat_id, user_id, "/export")
            elif action == "reload":
                self.admin_command(chat_id, user_id, "/reload")

    def handle_message(self, message: dict[str, Any]) -> None:
        if "from" not in message or "chat" not in message:
            return
        user = message["from"]
        user_id = int(user["id"])
        chat_id = int(message["chat"]["id"])
        if message["chat"].get("type") != "private":
            if str(message.get("text", "")).startswith("/start"):
                self.api.send_message(chat_id, "Открой бота в личке — там витрина и размеры.")
            return
        web_app_data = message.get("web_app_data")
        if isinstance(web_app_data, dict):
            self.db.upsert_user(user)
            self.handle_web_app_data(chat_id, user, str(web_app_data.get("data", "")))
            return
        text = str(message.get("text", "")).strip()
        if text.startswith("/start"):
            # start() decides whether the user is new, so it must run the upsert itself.
            self.start(chat_id, user, text.partition(" ")[2].strip())
            return
        self.db.upsert_user(user)
        if self.db.get_state(user_id) and self.handle_add_product_text(chat_id, user_id, text):
            return
        if text.startswith("/") and self.admin_command(chat_id, user_id, text):
            return
        if text == "/menu":
            self.api.send_message(chat_id, "Главное меню:", self.main_menu())
            return
        if text.lower() in ("отмена", "cancel"):
            self.db.clear_state(user_id)
            self.api.send_message(chat_id, "Отменили.", remove_keyboard())
            self.api.send_message(chat_id, "Главное меню:", self.main_menu())
            return
        phone: str | None = None
        contact = message.get("contact")
        if contact and int(contact.get("user_id", user_id)) == user_id:
            phone = normalize_phone(str(contact.get("phone_number", "")))
        elif self.db.get_state(user_id):
            phone = normalize_phone(text)
        if phone:
            self.save_phone_and_continue(chat_id, user_id, phone)
            return
        if self.db.get_state(user_id):
            self.api.send_message(chat_id, "Номер не распознан. Формат: +79991234567")
            return
        self.api.send_message(
            chat_id,
            f"{BOLT} Жми кнопки — так быстрее. Витрина, размеры и дропы там." + self.cta("drop"),
            self.main_menu(),
        )

    def handle_update(self, update: dict[str, Any]) -> bool:
        try:
            if "callback_query" in update:
                self.handle_callback(update["callback_query"])
            elif "message" in update:
                self.handle_message(update["message"])
            return True
        except Exception:
            LOG.exception("Failed to process update %s", update.get("update_id"))
            return False


VIDEO_SUFFIXES = {".mp4", ".m4v", ".webm", ".mov"}
VIDEO_CHUNK = 256 * 1024
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class StorefrontHandler(BaseHTTPRequestHandler):
    """Serve the Telegram Mini App and a read-only catalog endpoint.

    Keeping the storefront on the same origin as the bot's health server means
    the browser never needs to call localhost or a second private service. The
    catalog endpoint exposes only active products; product validation for orders
    still happens in ``BrandBot.handle_web_app_data``.
    """

    catalog: Catalog | None = None
    settings: Settings | None = None
    static_root = BASE_DIR / "miniapp"

    def _write(self, body: bytes, content_type: str, status: int = 200, cache_control: str = "no-cache") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _not_found(self) -> None:
        self._write(b"Not found", "text/plain; charset=utf-8", 404, "no-store")

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/health":
            self._write(b'{"status":"ok","service":"vorozhbitov-shop"}', "application/json; charset=utf-8")
            return
        if path == "/api/catalog":
            catalog = self.catalog
            settings = self.settings
            if not catalog:
                self._not_found()
                return
            payload = {
                "brand": catalog.data.get("brand", {"name": settings.brand_name if settings else "ВОРОЖБИТОВ"}),
                "channel_url": settings.channel_url if settings else "",
                "products": [product for product in catalog.data.get("products", []) if product.get("active", True)],
                "categories": catalog.categories,
                "lookbook": catalog.data.get("lookbook", []),
                "media": catalog.data.get("media", {}),
            }
            self._write(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            return

        relative = path.lstrip("/")
        if relative in ("", "app", "app/"):
            relative = "index.html"
        elif relative.startswith("miniapp/"):
            relative = relative.removeprefix("miniapp/") or "index.html"
        candidate = (self.static_root / relative).resolve()
        try:
            candidate.relative_to(self.static_root.resolve())
        except ValueError:
            self._not_found()
            return
        if not candidate.is_file():
            self._not_found()
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "image/svg+xml"}:
            content_type += "; charset=utf-8"
        suffix = candidate.suffix.lower()
        if suffix in VIDEO_SUFFIXES:
            self._send_file_ranged(candidate, content_type, "public, max-age=86400")
            return
        try:
            body = candidate.read_bytes()
        except OSError:
            self._not_found()
            return
        cache = "public, max-age=3600" if suffix in {".jpg", ".jpeg", ".png", ".webp", ".svg"} else "no-cache"
        self._write(body, content_type, 200, cache)

    def _send_file_ranged(self, path: Path, content_type: str, cache_control: str) -> None:
        """Отдаёт файл с поддержкой HTTP Range (206) и потоково, не читая его целиком.

        Без этого <video> в iOS/Safari WKWebView не стартует и не перематывается:
        первый запрос идёт как ``Range: bytes=0-1``, и сервер обязан ответить 206.
        """
        try:
            size = path.stat().st_size
        except OSError:
            self._not_found()
            return
        start, end = 0, size - 1
        status = 200
        range_header = self.headers.get("Range", "")
        match = RANGE_RE.match(range_header.strip()) if range_header else None
        if match:
            raw_start, raw_end = match.group(1), match.group(2)
            if raw_start == "" and raw_end == "":
                match = None
            elif raw_start == "":  # suffix range: last N bytes
                length = min(int(raw_end), size)
                start, end = size - length, size - 1
            else:
                start = int(raw_start)
                end = min(int(raw_end), size - 1) if raw_end else size - 1
            if match and (start > end or start >= size):
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if match:
                status = 206
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command == "HEAD":
            return
        try:
            with path.open("rb") as handle:
                handle.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = handle.read(min(VIDEO_CHUNK, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def do_HEAD(self) -> None:
        self.do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return


# Backwards-compatible name for health-check imports in small deployments.
HealthHandler = StorefrontHandler


def start_health_server(port: int, catalog: Catalog | None = None, settings: Settings | None = None) -> ThreadingHTTPServer:
    handler = type("ConfiguredStorefrontHandler", (StorefrontHandler,), {"catalog": catalog, "settings": settings})
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    threading.Thread(target=server.serve_forever, name="storefront-server", daemon=True).start()
    return server


def polling_loop(api: TelegramAPI, bot: BrandBot) -> None:
    offset = 0
    retry_delay = 1
    while not STOP_EVENT.is_set():
        try:
            updates = api.call(
                "getUpdates",
                {"offset": offset, "timeout": 10, "allowed_updates": ["message", "callback_query"]},
                timeout=15,
            )
            retry_delay = 1
            for update in updates:
                if bot.handle_update(update):
                    offset = max(offset, int(update["update_id"]) + 1)
                else:
                    break
        except Exception as exc:
            LOG.warning("Polling error: %s", exc)
            STOP_EVENT.wait(retry_delay)
            retry_delay = min(retry_delay * 2, 30)


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = Settings.from_env()
    except (TypeError, ValueError) as exc:
        LOG.error("Invalid configuration: %s", exc)
        return 2
    if not settings.token:
        LOG.error("BOT_TOKEN is not configured. Copy .env.example to .env and set the token.")
        return 2
    if not (1 <= settings.health_port <= 65535):
        LOG.error("PORT must be between 1 and 65535")
        return 2
    if not settings.channel_url.startswith(("https://", "http://", "tg://")):
        LOG.error("CHANNEL_URL must be a valid HTTP(S) or tg:// URL")
        return 2
    try:
        ensure_catalog_exists(settings.catalog_path, BASE_DIR / "catalog.json")
        catalog = Catalog(settings.catalog_path)
        db = Database(settings.database_path)
        api = TelegramAPI(settings.token)
        identity = api.call("getMe")
        api.call("deleteWebhook", {"drop_pending_updates": False})
    except Exception as exc:
        LOG.error("Startup failed: %s", exc)
        return 1
    bot = BrandBot(settings, api, db, catalog)
    bot.bot_username = str(identity.get("username") or "")
    LOG.info("Starting @%s for brand %s", bot.bot_username, settings.brand_name)
    health_server = start_health_server(settings.health_port, catalog, settings)

    def stop(*_: Any) -> None:
        STOP_EVENT.set()
        health_server.shutdown()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        polling_loop(api, bot)
    finally:
        health_server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
