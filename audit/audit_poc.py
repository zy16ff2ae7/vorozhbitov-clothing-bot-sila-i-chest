"""PoC-проверки гипотез аудита.

Запуск из корня проекта:
    PYTHONPATH=. python3 audit/audit_poc.py
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import bot as bot_module
from bot import BrandBot, Catalog, Database, Settings, TelegramAPI

ROOT = Path(__file__).resolve().parent.parent  # корень проекта (каталог с bot.py)
bot_module.LOG.disabled = True


class FakeAPI(TelegramAPI):
    def __init__(self, fail_methods: set[str] | None = None):
        self.base_url = "https://api.telegram.org/botfake/"
        self.sent: list[tuple[str, dict]] = []
        self.fail_methods = fail_methods or set()

    def call(self, method, payload=None, timeout=70):
        self.sent.append((method, payload or {}))
        if method in self.fail_methods:
            raise RuntimeError(f"Telegram HTTP 400: {{'ok':False,'description':'Bad Request: query is too old'}} ({method})")
        if method == "sendMediaGroup":
            return [{"message_id": 1}]
        return {"message_id": len(self.sent)}


def make_bot(api: FakeAPI, workdir: Path, admin_ids=frozenset({1})) -> BrandBot:
    catalog_path = workdir / "catalog.json"
    shutil.copy(ROOT / "catalog.json", catalog_path)
    settings = Settings(
        token="fake", admin_ids=admin_ids, channel_url="https://t.me/x", webapp_url="https://shop.example.com",
        manager_chat_id=1, brand_name="TEST", support_username="", database_path=workdir / "bot.sqlite3",
        catalog_path=catalog_path, health_port=8080, giveaway_min_invites=3, privacy_url="",
    )
    b = BrandBot(settings, api, Database(settings.database_path), Catalog(catalog_path))
    b.bot_username = "testbot"
    return b


def msg(uid, text=None, **extra):
    m = {"message_id": 1, "chat": {"id": uid, "type": "private"}, "from": {"id": uid, "first_name": "U"}}
    if text is not None:
        m["text"] = text
    m.update(extra)
    return {"update_id": 100, "message": m}


def cb(uid, data, cid="cb1"):
    return {"update_id": 101, "callback_query": {"id": cid, "data": data, "from": {"id": uid, "first_name": "U"},
                                                 "message": {"chat": {"id": uid, "type": "private"}}}}


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------- A
section("A. Poison pill: произвольный callback_data 'size:x' -> исключение -> offset не сдвигается")
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI()
    b = make_bot(api, Path(d))
    b.handle_update(msg(500, "/start"))
    ok = b.handle_update(cb(500, "size:x"))
    print("handle_update вернул:", ok, "(False => polling_loop делает break и НЕ сдвигает offset)")

    # Симулируем polling_loop: getUpdates всегда возвращает тот же апдейт
    class LoopAPI(FakeAPI):
        polls = 0
        def call(self, method, payload=None, timeout=70):
            if method == "getUpdates":
                LoopAPI.polls += 1
                if LoopAPI.polls >= 5:
                    bot_module.STOP_EVENT.set()
                print(f"  getUpdates #{LoopAPI.polls} offset={payload['offset']}")
                return [cb(500, "size:x")]
            return super().call(method, payload, timeout)

    bot_module.STOP_EVENT.clear()
    loop_api = LoopAPI()
    (Path(d) / "b2").mkdir()
    b2 = make_bot(loop_api, Path(d) / "b2")
    bot_module.polling_loop(loop_api, b2)
    bot_module.STOP_EVENT.clear()
    print("  => offset остался 0 все 5 итераций: бот навсегда завис на одном апдейте")

# ---------------------------------------------------------------- B
section("B. Poison pill №2 (реалистичный): протухший callback после рестарта -> answerCallbackQuery 400")
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI(fail_methods={"answerCallbackQuery"})
    b = make_bot(api, Path(d))
    b.handle_update(msg(500, "/start"))
    ok = b.handle_update(cb(500, "catalog"))
    print("Легитимный клик 'catalog' с истёкшим callback id -> handle_update:", ok)
    print("  => после любого рестарта с очередью кликов бот зависает на первом же старом callback")

# ---------------------------------------------------------------- C
section("C. Телефон сохраняется БЕЗ согласия: шаринг контакта вне сценария")
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI()
    b = make_bot(api, Path(d))
    b.handle_update(msg(500, "/start"))
    b.handle_update(msg(500, contact={"phone_number": "+79991112233", "user_id": 500, "first_name": "U"}))
    u = b.db.get_user(500)
    print("phone в БД:", u["phone"], "| consent_at:", u["consent_at"], "| has_consent:", b.db.has_consent(500))
    print("  => контакт сохранён, согласия нет; пользователь попадает в сегмент рассылки 'contacts'")

# ---------------------------------------------------------------- D
section("D. Телефон, введённый текстом в состоянии awaiting_consent -> сохраняется без согласия, заказ теряется")
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI()
    b = make_bot(api, Path(d))
    b.handle_update(msg(500, "/start"))
    b.handle_update(cb(500, "size:drop-tee-001:M"))          # бот просит согласие
    print("state после выбора размера:", b.db.get_state(500)[0])
    b.handle_update(msg(500, "+79991112233"))                 # юзер вместо кнопки пишет номер
    u = b.db.get_user(500)
    print("phone:", u["phone"], "| consent_at:", u["consent_at"], "| orders:", b.db.stats()["orders"],
          "| state:", b.db.get_state(500))
    print("  => номер записан без согласия, заявка на CORE TEE / M не создана, ответ бота:",
          repr(api.sent[-2][1].get("text", "")[:60]))

# ---------------------------------------------------------------- E
section("E. Чужой контакт (не-Telegram пользователь, поля user_id нет) принимается как свой")
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI()
    b = make_bot(api, Path(d))
    b.handle_update(msg(500, "/start"))
    b.handle_update(msg(500, contact={"phone_number": "+79990000001", "first_name": "Мама"}))
    print("phone юзера 500 в БД:", b.db.get_user(500)["phone"], "(это номер третьего лица)")

# ---------------------------------------------------------------- F
section("F. /add с невалидным photo_url портит data/catalog.json -> бот не стартует после рестарта")
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI()
    b = make_bot(api, Path(d))
    for u in [msg(1, "/add")]:
        b.handle_update(u)
    b.handle_update(cb(1, "addcat:tee"))
    for t in ["TEST TEE", "1 000 ₽", "M", "desc", "ftp://not-http"]:
        b.handle_update(msg(1, t))
    ok = b.handle_update(cb(1, "add:publish"))
    print("publish handle_update:", ok)
    try:
        Catalog(b.catalog.path)
        print("Catalog перечитан OK")
    except Exception as exc:
        print("Catalog() при рестарте падает:", type(exc).__name__, "-", exc)
    print("  => файл уже записан невалидным; ensure_catalog_exists его не пересоздаст (файл существует)")

# ---------------------------------------------------------------- G
section("G. Реферал 'захватывает' уже существующего пользователя без реферера")
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI()
    b = make_bot(api, Path(d))
    b.handle_update(msg(500, "/start"))          # старый юзер, пришёл сам
    b.handle_update(msg(999, "/start"))
    b.handle_update(msg(500, "/start ref999"))   # кликнул реф-ссылку в комментариях
    print("invited_count у 999:", b.db.get_user(999)["invited_count"], "| is_new был False")

# ---------------------------------------------------------------- H
section("H. Mini App: кнопка web_app находится в INLINE-клавиатуре")
b_menu = None
with tempfile.TemporaryDirectory() as d:
    b = make_bot(FakeAPI(), Path(d))
    print(json.dumps(b.main_menu(), ensure_ascii=False)[:160], "...")
    print("  => sendData() работает ТОЛЬКО из reply-keyboard web_app кнопки (см. docs) — заказы из Mini App не дойдут до бота")

# ---------------------------------------------------------------- I
section("I. send_photo с URL, который Telegram не может скачать -> исключение -> poison pill на карточке товара")
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI(fail_methods={"sendPhoto"})
    b = make_bot(api, Path(d))
    b.handle_update(msg(500, "/start"))
    ok = b.handle_update(cb(500, "product:drop-tee-001"))
    print("открытие карточки -> handle_update:", ok, "| photo url:", b.public_asset_url("assets/base-tee.jpg"))

# ---------------------------------------------------------------- J
section("J. Рассылка выполняется синхронно в polling-потоке")
import time
with tempfile.TemporaryDirectory() as d:
    api = FakeAPI()
    b = make_bot(api, Path(d))
    b.db.upsert_user({"id": 1, "first_name": "admin"})
    for uid in range(1000, 1050):
        b.db.upsert_user({"id": uid, "first_name": "x"})
    b.db.set_state(1, "broadcast_pending", {"text": "hi", "segment": "all"})
    t = time.perf_counter()
    b.confirm_broadcast(1, 1)
    dt = time.perf_counter() - t
    print(f"50 получателей -> {dt:.2f}s (0.04s sleep/сообщение). 10 000 юзеров => ~{10000*0.04/60:.0f} мин полной глухоты бота")
