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


if __name__ == "__main__":
    unittest.main()
