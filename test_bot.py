import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from bot import BASE_DIR, BrandBot, Catalog, Database, REF_RE, Settings, TelegramAPI, ensure_catalog_exists, normalize_phone, slugify


def make_db(directory: str) -> Database:
    return Database(Path(directory) / "test.sqlite3")


class BotTests(unittest.TestCase):
    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("8 (999) 123-45-67"), "+79991234567")
        self.assertEqual(normalize_phone("+380 99 123 45 67"), "+380991234567")
        self.assertIsNone(normalize_phone("123"))

    def test_catalog_loads_and_resolves_products(self):
        catalog = Catalog(Path(__file__).with_name("catalog.json"))
        self.assertGreaterEqual(len(catalog.categories), 1)
        self.assertIsNotNone(catalog.get("drop-tee-001"))
        self.assertEqual(catalog.get("drop-tee-001")["category"], "drop")
        self.assertEqual(catalog.lookbook, [])

    def test_catalog_seed_is_copied_once_to_mutable_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            seed = Path(__file__).with_name("catalog.json")
            target = Path(directory) / "data" / "catalog.json"
            self.assertTrue(ensure_catalog_exists(target, seed))
            self.assertEqual(target.read_bytes(), seed.read_bytes())
            target.write_text('{"custom": true}\n', encoding="utf-8")
            self.assertFalse(ensure_catalog_exists(target, seed))
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"custom": True})

    def test_catalog_seed_requires_an_existing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with self.assertRaises(FileNotFoundError):
                ensure_catalog_exists(base / "data/catalog.json", base / "missing.json")

    def test_default_catalog_is_in_persistent_data_directory(self):
        env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"CATALOG_PATH", "DATABASE_PATH", "PORT", "GIVEAWAY_MIN_INVITES"}
        }
        with patch.dict(os.environ, env, clear=True), patch("bot.load_dotenv"):
            settings = Settings.from_env()
        self.assertEqual(settings.catalog_path, BASE_DIR / "data/catalog.json")
        self.assertEqual(settings.database_path, BASE_DIR / "data/bot.sqlite3")

    def test_database_uses_wal_and_deduplicates_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            db.upsert_user({"id": 42, "username": "buyer", "first_name": "N", "last_name": ""})
            product = {"id": "test-product", "name": "Test Product"}
            order_id, created = db.create_order("callback:abc", 42, product, "M", "+79991234567")
            repeated_id, repeated_created = db.create_order("callback:abc", 42, product, "M", "+79991234567")
            self.assertTrue(created)
            self.assertFalse(repeated_created)
            self.assertEqual(order_id, repeated_id)
            self.assertEqual(db.stats()["orders"], 1)
            journal_mode = db.connection().execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(journal_mode.lower(), "wal")

    def test_order_status_lifecycle_and_invalid_transitions(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            db.upsert_user({"id": 42, "username": "buyer", "first_name": "N"})
            order_id, _ = db.create_order(
                "status-flow", 42, {"id": "p1", "name": "P1"}, "M", "+79991234567"
            )
            order, changed = db.set_order_status(order_id, "confirmed")
            self.assertTrue(changed)
            self.assertEqual(order["status"], "confirmed")
            repeated, repeated_changed = db.set_order_status(order_id, "confirmed")
            self.assertFalse(repeated_changed)
            self.assertEqual(repeated["status"], "confirmed")
            completed, completed_changed = db.set_order_status(order_id, "completed")
            self.assertTrue(completed_changed)
            self.assertEqual(completed["status"], "completed")
            with self.assertRaises(ValueError):
                db.set_order_status(order_id, "cancelled")
            self.assertEqual(db.get_order(order_id)["status"], "completed")
            self.assertEqual(db.set_order_status(99999, "confirmed"), (None, False))

    def test_order_can_be_cancelled_before_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            db.upsert_user({"id": 43, "username": "buyer2", "first_name": "B"})
            order_id, _ = db.create_order(
                "cancel-flow", 43, {"id": "p2", "name": "P2"}, "L", "+79991234568"
            )
            cancelled, changed = db.set_order_status(order_id, "cancelled")
            self.assertTrue(changed)
            self.assertEqual(cancelled["status"], "cancelled")
            with self.assertRaises(ValueError):
                db.set_order_status(order_id, "confirmed")

    def test_referral_registers_and_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            is_new, referrer = db.upsert_user({"id": 100, "username": "inviter", "first_name": "A"})
            self.assertTrue(is_new)
            self.assertIsNone(referrer)
            self.assertTrue(REF_RE.match("ref100"))
            is_new_guest, guest_referrer = db.upsert_user(
                {"id": 200, "username": "guest", "first_name": "B"}, source="ref100"
            )
            self.assertTrue(is_new_guest)
            self.assertEqual(guest_referrer, 100)
            # повторный /start не должен дублировать приглашённого
            db.upsert_user({"id": 200, "username": "guest", "first_name": "B"}, source="ref100")
            self.assertEqual(db.get_user(100)["invited_count"], 1)
            self.assertIn(100, db.giveaway_pool(1))
            self.assertNotIn(200, db.giveaway_pool(1))
            self.assertEqual(db.top_referrers()[0]["user_id"], 100)

    def test_self_referral_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            _, referrer = db.upsert_user({"id": 7, "username": "solo"}, source="ref7")
            self.assertIsNone(referrer)
            self.assertEqual(db.get_user(7)["invited_count"], 0)

    def test_segments_and_interest(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            db.upsert_user({"id": 1, "username": "anon"})
            db.upsert_user({"id": 2, "username": "withphone"})
            db.set_phone(2, "+79990000000")
            db.upsert_user({"id": 3, "username": "hoodie_fan"})
            db.set_interest(3, "hoodie")
            db.create_order("r1", 2, {"id": "p1", "name": "P1"}, "M", "+79990000000")
            self.assertEqual(sorted(db.broadcast_audience("all")), [1, 2, 3])
            self.assertEqual(db.broadcast_audience("contacts"), [2])
            self.assertEqual(db.broadcast_audience("buyers"), [2])
            self.assertEqual(db.broadcast_audience("interest:hoodie"), [3])
            self.assertEqual(db.broadcast_audience("interest:tee"), [])

    def test_waitlist_is_unique_and_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            db.upsert_user({"id": 5, "username": "waiter"})
            product = {"id": "drop-tee-001", "name": "DROP 001 TEE"}
            self.assertTrue(db.add_to_waitlist(5, product, "L"))
            self.assertFalse(db.add_to_waitlist(5, product, "L"))
            self.assertEqual(db.stats()["waitlist"], 1)
            self.assertEqual(db.waitlist_user_ids("drop-tee-001", "L"), [5])
            self.assertEqual(db.waitlist_user_ids("drop-tee-001", "M"), [])
            self.assertEqual(db.waitlist_rows()[0]["product_name"], "DROP 001 TEE")

    def test_csv_export_escapes_formulas(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            db.upsert_user({"id": 7, "username": "=FORMULA", "first_name": "+SUM", "last_name": ""})
            exported = db.export_users_csv().decode("utf-8-sig")
            self.assertIn("'=FORMULA", exported)
            self.assertIn("'+SUM", exported)

    def test_slugify_and_unique_ids(self):
        self.assertEqual(slugify("DROP 002 HOODIE"), "drop-002-hoodie")
        self.assertEqual(slugify("Худи «Город»"), "hudi-gorod")
        self.assertEqual(slugify("!!!"), "item")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            shutil.copy(Path(__file__).with_name("catalog.json"), path)
            catalog = Catalog(path)
            first = catalog.add_product(
                {
                    "category": "hoodie",
                    "name": "DROP 002 HOODIE",
                    "price": "1 ₽",
                    "sizes": ["M"],
                    "description": "Тест",
                }
            )
            second = catalog.add_product(
                {
                    "category": "hoodie",
                    "name": "DROP 002 HOODIE",
                    "price": "2 ₽",
                    "sizes": ["L"],
                    "description": "Тест",
                }
            )
            self.assertEqual(first["id"], "drop-002-hoodie")
            self.assertEqual(second["id"], "drop-002-hoodie-2")
            self.assertIsNotNone(catalog.get(first["id"]))
            self.assertTrue(catalog.set_active(first["id"], False))
            self.assertIsNone(catalog.get(first["id"]))
            self.assertIsNotNone(catalog.get_any(first["id"]))
            # после перечитывания с диска скрытая вещь остаётся скрытой
            reloaded = Catalog(path)
            self.assertIsNone(reloaded.get(first["id"]))

    def test_consent_is_recorded_once_and_filters_audience(self):
        with tempfile.TemporaryDirectory() as directory:
            db = make_db(directory)
            db.upsert_user({"id": 11, "username": "a"})
            db.upsert_user({"id": 12, "username": "b"})
            self.assertFalse(db.has_consent(11))
            db.set_consent(11)
            self.assertTrue(db.has_consent(11))
            self.assertEqual(db.broadcast_audience("consent"), [11])
            self.assertEqual(sorted(db.broadcast_audience("all")), [11, 12])
            self.assertEqual(db.stats()["consents"], 1)

    def test_webapp_order_is_validated_against_catalog_and_stored(self):
        class FakeAPI(TelegramAPI):
            def __init__(self):
                self.sent = []

            def send_message(self, chat_id, text, reply_markup=None):
                self.sent.append((chat_id, text, reply_markup))
                return {"message_id": len(self.sent)}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            shutil.copy(Path(__file__).with_name("catalog.json"), catalog_path)
            settings = Settings(
                token="fake",
                admin_ids=frozenset(),
                channel_url="https://t.me/channel",
                webapp_url="",
                manager_chat_id=None,
                brand_name="ВОРОЖБИТОВ",
                support_username="",
                database_path=root / "bot.sqlite3",
                catalog_path=catalog_path,
                health_port=8080,
                giveaway_min_invites=3,
                privacy_url="",
            )
            db = make_db(directory)
            catalog = Catalog(catalog_path)
            api = FakeAPI()
            brand_bot = BrandBot(settings, api, db, catalog)
            user = {"id": 77, "first_name": "Buyer", "username": "buyer"}
            payload = {
                "type": "order",
                "request_id": "web-test-001",
                "consent": True,
                "customer": {"name": "Buyer", "phone": "8 (999) 123-45-67", "city": "Могилёв"},
                "items": [
                    {"product_id": "drop-tee-001", "size": "M", "quantity": 2},
                    {"product_id": "missing", "size": "M", "quantity": 99},
                ],
            }
            brand_bot.handle_update({
                "update_id": 1,
                "message": {
                    "chat": {"id": 77, "type": "private"},
                    "from": user,
                    "web_app_data": {"data": json.dumps(payload, ensure_ascii=False)},
                },
            })
            self.assertEqual(db.stats()["orders"], 1)
            order = db.recent_orders(1)[0]
            self.assertEqual(order["product_id"], "drop-tee-001")
            self.assertEqual(order["quantity"], 2)
            self.assertEqual(order["phone"], "+79991234567")
            self.assertTrue(db.has_consent(77))
            self.assertIn("MINIAPP", api.sent[-1][1])

    def test_invalid_catalog_category_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(
                json.dumps(
                    {
                        "categories": [{"id": "valid", "name": "Valid"}],
                        "products": [
                            {
                                "id": "item",
                                "category": "missing",
                                "name": "Item",
                                "price": "1 ₽",
                                "sizes": ["M"],
                                "description": "Description",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                Catalog(path)


    def test_product_with_images_is_sent_as_album(self):
        class FakeAPI(TelegramAPI):
            def __init__(self):
                self.calls = []

            def call(self, method, payload=None, timeout=70):
                self.calls.append((method, payload or {}))
                return [{"message_id": 1}] if method == "sendMediaGroup" else {"message_id": len(self.calls)}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            shutil.copy(Path(__file__).with_name("catalog.json"), catalog_path)
            settings = Settings(
                token="fake", admin_ids=frozenset(), channel_url="https://t.me/channel",
                webapp_url="https://shop.example.com", manager_chat_id=None, brand_name="ВОРОЖБИТОВ",
                support_username="", database_path=root / "bot.sqlite3", catalog_path=catalog_path,
                health_port=8080, giveaway_min_invites=3, privacy_url="",
            )
            api = FakeAPI()
            brand_bot = BrandBot(settings, api, make_db(directory), Catalog(catalog_path))
            brand_bot.db.upsert_user({"id": 5, "first_name": "N"})
            gallery = brand_bot.product_gallery(brand_bot.catalog.get("tee-sila-i-chest-001"))
            self.assertEqual(len(gallery), 7)
            self.assertTrue(all(url.startswith("https://shop.example.com/assets/img/") for url in gallery))
            brand_bot.show_product(5, 5, "tee-sila-i-chest-001")
            methods = [method for method, _ in api.calls]
            self.assertEqual(methods, ["sendMediaGroup", "sendMessage"])
            album = api.calls[0][1]["media"]
            self.assertEqual(len(album), 7)
            self.assertIn("ЗАБРАТЬ РАЗМЕР", str(api.calls[1][1]["reply_markup"]))
            # без WEBAPP_URL локальные ассеты недоступны Telegram — карточка уходит текстом, без падения
            offline = Settings(**{**settings.__dict__, "webapp_url": ""})
            api2 = FakeAPI()
            bot2 = BrandBot(offline, api2, brand_bot.db, brand_bot.catalog)
            bot2.show_product(5, 5, "tee-sila-i-chest-001")
            self.assertEqual([m for m, _ in api2.calls], ["sendMessage"])


if __name__ == "__main__":
    unittest.main()


class StorefrontVideoTests(unittest.TestCase):
    """Видео для Mini App должно отдаваться с поддержкой Range — иначе iOS не играет."""

    @classmethod
    def setUpClass(cls):
        import http.client
        from bot import StorefrontHandler, start_health_server

        cls.tmp = tempfile.mkdtemp()
        root = Path(cls.tmp)
        (root / "assets" / "video").mkdir(parents=True)
        cls.payload = bytes(range(256)) * 40  # 10 240 байт
        (root / "assets" / "video" / "clip.mp4").write_bytes(cls.payload)
        (root / "index.html").write_text("<!doctype html><title>t</title>", encoding="utf-8")
        cls._orig_root = StorefrontHandler.static_root
        StorefrontHandler.static_root = root
        cls.server = start_health_server(0)
        cls.port = cls.server.server_address[1]
        cls.http = http.client

    @classmethod
    def tearDownClass(cls):
        from bot import StorefrontHandler

        cls.server.shutdown()
        cls.server.server_close()
        StorefrontHandler.static_root = cls._orig_root
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def request(self, method, path, headers=None):
        conn = self.http.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, headers=headers or {})
        response = conn.getresponse()
        body = response.read()
        conn.close()
        return response, body

    def test_full_video_response_advertises_ranges(self):
        response, body = self.request("GET", "/assets/video/clip.mp4")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Accept-Ranges"), "bytes")
        self.assertEqual(response.getheader("Content-Type"), "video/mp4")
        self.assertIn("max-age=86400", response.getheader("Cache-Control"))
        self.assertEqual(body, self.payload)

    def test_safari_probe_range_gets_206(self):
        response, body = self.request("GET", "/assets/video/clip.mp4", {"Range": "bytes=0-1"})
        self.assertEqual(response.status, 206)
        self.assertEqual(response.getheader("Content-Range"), f"bytes 0-1/{len(self.payload)}")
        self.assertEqual(body, self.payload[:2])

    def test_open_ended_and_suffix_ranges(self):
        response, body = self.request("GET", "/assets/video/clip.mp4", {"Range": "bytes=10000-"})
        self.assertEqual(response.status, 206)
        self.assertEqual(body, self.payload[10000:])
        response, body = self.request("GET", "/assets/video/clip.mp4", {"Range": "bytes=-100"})
        self.assertEqual(response.status, 206)
        self.assertEqual(body, self.payload[-100:])
        self.assertEqual(response.getheader("Content-Range"), f"bytes {len(self.payload) - 100}-{len(self.payload) - 1}/{len(self.payload)}")

    def test_unsatisfiable_range_is_416(self):
        response, body = self.request("GET", "/assets/video/clip.mp4", {"Range": "bytes=999999-"})
        self.assertEqual(response.status, 416)
        self.assertEqual(response.getheader("Content-Range"), f"bytes */{len(self.payload)}")

    def test_head_has_headers_and_no_body(self):
        response, body = self.request("HEAD", "/assets/video/clip.mp4")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Length"), str(len(self.payload)))
        self.assertEqual(body, b"")
        response, body = self.request("HEAD", "/index.html")
        self.assertEqual(response.status, 200)
        self.assertEqual(body, b"")

    def test_path_traversal_is_still_blocked(self):
        response, _ = self.request("GET", "/assets/video/../../bot.py")
        self.assertEqual(response.status, 404)


class TeaserTests(unittest.TestCase):
    """Тизер: первый раз — загрузка файла, дальше — кешированный file_id; сбой не роняет диалог."""

    class FakeAPI:
        def __init__(self, fail_first=False):
            self.calls = []
            self.fail_first = fail_first

        def send_video(self, chat_id, video, caption="", reply_markup=None, **kwargs):
            self.calls.append((chat_id, video, caption, kwargs))
            if self.fail_first and len(self.calls) == 1:
                raise RuntimeError("Telegram API error: Bad Request: wrong file identifier")
            return {"message_id": len(self.calls), "video": {"file_id": "FILE_ID_123"}}

        def send_message(self, *args, **kwargs):
            self.calls.append(("send_message", args))

        def send_photo(self, *args, **kwargs):
            self.calls.append(("send_photo", args))

        def send_media_group(self, *args, **kwargs):
            self.calls.append(("send_media_group", args))

    def make_bot(self, api):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory, True)
        db = make_db(directory)
        catalog = Catalog(Path(__file__).with_name("catalog.json"))
        settings = Settings(
            token="", admin_ids=frozenset(), channel_url="https://t.me/x", webapp_url="", manager_chat_id=None,
            brand_name="ВОРОЖБИТОВ", support_username="", database_path=Path(directory) / "t.sqlite3",
            catalog_path=Path(__file__).with_name("catalog.json"), health_port=0, giveaway_min_invites=3, privacy_url="",
        )
        return BrandBot(settings, api, db, catalog), db

    def test_teaser_uploads_once_then_uses_file_id(self):
        api = self.FakeAPI()
        bot, db = self.make_bot(api)
        db.upsert_user({"id": 1, "first_name": "A"})
        self.assertTrue(bot.send_teaser(100, 1, "cap"))
        self.assertIsInstance(api.calls[0][1], Path, "first send must upload the local file")
        self.assertTrue(str(api.calls[0][1]).endswith("teaser-720.mp4"))
        self.assertEqual(api.calls[0][3]["width"], 720)
        self.assertEqual(db.get_kv(BrandBot.TEASER_KEY), "FILE_ID_123")
        self.assertTrue(bot.send_teaser(101, 1, "cap"))
        self.assertEqual(api.calls[1][1], "FILE_ID_123", "second send must reuse cached file_id")

    def test_stale_file_id_is_dropped_and_failure_is_soft(self):
        api = self.FakeAPI(fail_first=True)
        bot, db = self.make_bot(api)
        db.upsert_user({"id": 2, "first_name": "B"})
        db.set_kv(BrandBot.TEASER_KEY, "STALE")
        self.assertFalse(bot.send_teaser(100, 2))
        self.assertEqual(db.get_kv(BrandBot.TEASER_KEY), "")
        self.assertTrue(bot.send_teaser(100, 2))
        self.assertIsInstance(api.calls[1][1], Path)

    def test_product_card_with_teaser_flag_sends_video_with_keyboard(self):
        api = self.FakeAPI()
        bot, db = self.make_bot(api)
        db.upsert_user({"id": 3, "first_name": "C"})
        bot.show_product(100, 3, "tee-sila-i-chest-001")
        video_calls = [c for c in api.calls if c[0] == 100]
        self.assertEqual(len(video_calls), 1)
        _, _, caption, kwargs = video_calls[0]
        self.assertIn("СИЛА И ЧЕСТЬ", caption)
        self.assertNotIn(("send_media_group",), [c[:1] for c in api.calls])

    def test_start_for_new_user_sends_teaser_first(self):
        api = self.FakeAPI()
        bot, db = self.make_bot(api)
        bot.start(100, {"id": 4, "first_name": "D"})
        self.assertEqual(api.calls[0][0], 100)
        self.assertIsInstance(api.calls[0][1], Path)
        self.assertEqual(api.calls[1][0], "send_message")


class WebAppOrderTests(unittest.TestCase):
    """POST /api/order: подпись initData, заявка с номером жетона, отказ без подписи."""

    TOKEN = "123456:TEST-TOKEN"

    @staticmethod
    def sign(token, fields):
        import hashlib
        import hmac
        import urllib.parse

        check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        fields = dict(fields, hash=hmac.new(secret, check.encode(), hashlib.sha256).hexdigest())
        return urllib.parse.urlencode(fields)

    def init_data(self, token=None, age=0, user_id=77):
        import time

        return self.sign(token or self.TOKEN, {
            "query_id": "AAE",
            "user": json.dumps({"id": user_id, "first_name": "Никита", "username": "vv"}, ensure_ascii=False, separators=(",", ":")),
            "auth_date": str(int(time.time()) - age),
        })

    def test_verify_init_data(self):
        from bot import verify_init_data

        good = verify_init_data(self.init_data(), self.TOKEN)
        self.assertIsNotNone(good)
        self.assertEqual(good["user"]["id"], 77)
        self.assertIsNone(verify_init_data(self.init_data(token="999:OTHER"), self.TOKEN), "чужой токен")
        self.assertIsNone(verify_init_data(self.init_data() + "x", self.TOKEN), "испорченная подпись")
        self.assertIsNone(verify_init_data(self.init_data(age=48 * 3600), self.TOKEN), "просроченный auth_date")
        self.assertIsNone(verify_init_data("", self.TOKEN))
        self.assertIsNone(verify_init_data(self.init_data(), ""))

    def make_bot(self, directory):
        from bot import BrandBot, Catalog, Settings, TelegramAPI

        root = Path(directory)
        catalog_path = root / "catalog.json"
        shutil.copy(Path(__file__).with_name("catalog.json"), catalog_path)
        settings = Settings(
            token=self.TOKEN, admin_ids=frozenset(), channel_url="https://t.me/channel",
            webapp_url="https://shop.example.com", manager_chat_id=900, brand_name="ВОРОЖБИТОВ",
            support_username="", database_path=root / "bot.sqlite3", catalog_path=catalog_path,
            health_port=8080, giveaway_min_invites=3, privacy_url="",
        )

        class FakeAPI(TelegramAPI):
            def __init__(self):
                super().__init__("fake")
                self.sent = []

            def call(self, method, payload=None, timeout=70):
                self.sent.append((method, payload))
                return {"message_id": len(self.sent)}

        api = FakeAPI()
        return BrandBot(settings, api, make_db(directory), Catalog(catalog_path)), api, settings

    def test_http_order_with_tag_number(self):
        import http.client
        from bot import start_health_server

        with tempfile.TemporaryDirectory() as directory:
            brand_bot, api, settings = self.make_bot(directory)
            server = start_health_server(0, brand_bot.catalog, settings, brand_bot)
            port = server.server_address[1]
            try:
                def post(body, headers):
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                    conn.request("POST", "/api/order", body=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
                    response = conn.getresponse()
                    data = json.loads(response.read().decode())
                    conn.close()
                    return response.status, data

                order = {
                    "type": "order", "request_id": "web-1", "consent": True,
                    "customer": {"name": "Тест", "phone": "+79990000000", "city": "Москва"},
                    "items": [
                        {"product_id": "tag-sila-i-chest-001", "size": "ONE SIZE", "quantity": 1, "note": "63"},
                        {"product_id": "tee-sila-i-chest-001", "size": "L", "quantity": 1, "note": "<script>"},
                    ],
                }
                # 1) без подписи — 401, ничего не создано
                status, data = post({"order": order}, {})
                self.assertEqual(status, 401)
                self.assertFalse(data["ok"])
                self.assertEqual(brand_bot.db.stats().get("orders", 0), 0)

                # 2) с подписью — 200, два заказа, номер жетона в уведомлении менеджеру
                status, data = post({"order": order}, {"X-Telegram-Init-Data": self.init_data()})
                self.assertEqual(status, 200, data)
                self.assertTrue(data["ok"])
                self.assertEqual(len(data["orders"]), 2)
                self.assertEqual(data["orders"][0]["code"], f"{data['orders'][0]['id']:05d}")
                user = brand_bot.db.get_user(77)
                self.assertEqual(user["phone"], "+79990000000")
                self.assertTrue(brand_bot.db.has_consent(77))
                texts = [payload.get("text", "") for method, payload in api.sent if method == "sendMessage"]
                manager = [payload.get("text", "") for method, payload in api.sent if method == "sendMessage" and payload.get("chat_id") == 900]
                self.assertTrue(manager and "НОМЕР ЖЕТОНА: 63" in manager[0], manager)
                self.assertNotIn("<script>", "".join(texts), "невалидная заметка для футболки отброшена")
                notes = brand_bot.db.connection().execute("SELECT payload FROM events WHERE event='order_note'").fetchall()
                self.assertEqual(len(notes), 1)

                # 3) повтор того же request_id — идемпотентно
                status, data = post({"order": order}, {"X-Telegram-Init-Data": self.init_data()})
                self.assertEqual(status, 200)
                self.assertTrue(data.get("duplicate"))
                self.assertEqual(brand_bot.db.stats().get("orders", 0), 2)

                # 4) мусор — 400/413, сервер жив
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("POST", "/api/order", body=b"{not json", headers={"Content-Type": "application/json", "X-Telegram-Init-Data": self.init_data()})
                self.assertEqual(conn.getresponse().status, 400)
                conn.close()
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("GET", "/api/catalog")
                catalog = json.loads(conn.getresponse().read().decode())
                conn.close()
                self.assertTrue(catalog["orders_endpoint"])
                self.assertIn("tag-sila-i-chest-001", [p["id"] for p in catalog["products"]])
            finally:
                server.shutdown()
                server.server_close()

    def test_order_endpoint_disabled_without_token(self):
        import http.client
        from bot import start_health_server

        server = start_health_server(0)  # как preview_server: без бота и токена
        port = server.server_address[1]
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("POST", "/api/order", body=b"{}", headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            self.assertEqual(response.status, 503)
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
