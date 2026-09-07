# Видео в Mini App — как устроено (ветка draft/sila-i-chest)

## Что добавлено
| Файл | Что |
|---|---|
| `miniapp/assets/video/hero-loop.mp4` | 720×924 (3:4), 17 с, без звука, 1.2 МБ — тихий цикл в hero вместо картинки |
| `miniapp/assets/video/hero-poster.jpg` | постер/фолбэк hero (первый кадр) |
| `miniapp/assets/video/teaser-720.mp4` | 720×1280, 30.8 с, стерео, 3.8 МБ — полный тизер в модалке |
| `miniapp/assets/video/teaser-poster.jpg` | постер карточки «FIELD NOTE 01 / ТИЗЕР» |
| `catalog.json → "media"` | URL всех роликов; фронт подхватывает из `/api/catalog`, менять можно без пересборки образа |

Мастера (1080×1920) лежат вне репозитория: `sila-i-chest/video/sila-i-chest-teaser.mp4` (для канала/сторис)
и `sila-i-chest-teaser-v2-film.mp4` (вариант «плёнка»). Hero-loop рендерится `SIC_MODE=hero python3 video/make_video.py`.

## Фронт (`miniapp/`)
- `index.html`: в `.hero-visual` — `<video muted loop playsinline preload="metadata" poster>` + `<img class="hero-fallback">` +
  кнопка `#heroPlay` (появляется, только если автоплей отклонён). В lookbook главная карточка `#teaserCard` с ▶,
  модалка `#teaserModal` с `<video controls>` и кнопками «В ВИТРИНУ» / «В СТОРИС».
- `app.js`: `setupHeroVideo()` — `play()` с `catch` (iOS WKWebView может отказать → показываем ▶);
  пауза, когда hero вне экрана (IntersectionObserver) и при `visibilitychange`; `saveData`/2g и
  `prefers-reduced-motion` → видео не грузится, только постер. `openTeaser()/closeTeaser()` — звук включается
  по тапу, при закрытии `pause()+currentTime=0`, hero-loop возобновляется. `shareTeaserToStory()` — `tg.shareToStory()`
  (Bot API 7.8+), кнопка скрыта на старых клиентах. `applyMedia()` — применяет URL из `catalog.json.media`.
- `styles.css`: `.hero-video` с тем же фильтром, что у картинок (`contrast(1.05) saturate(.72)`), `.play-badge`,
  `.teaser-sheet`, reduced-motion скрывает видео.

## Сервер (`bot.py`)
`StorefrontHandler` теперь отдаёт `.mp4/.m4v/.webm/.mov` потоково с поддержкой **HTTP Range** (206, `Accept-Ranges`,
`Content-Range`, 416 на невалидный диапазон), `Cache-Control: public, max-age=86400`, и корректно отвечает на `HEAD`.
Без этого `<video>` в iOS/Safari не стартует (первый запрос — `Range: bytes=0-1`). Тесты: `StorefrontVideoTests` в `test_bot.py`.

## Бот (`bot.py`)
- `TelegramAPI.send_video()` — `sendVideo`: строка = `file_id`/HTTPS-URL (JSON), `Path` = загрузка файла multipart
  (с `thumbnail=attach://thumb`, `width/height/duration`, `supports_streaming`).
- `BrandBot.send_teaser()` — источник по приоритету: кешированный `file_id` (таблица `kv`) → `media.teaser_story_url` →
  локальный `miniapp/assets/video/teaser-720.mp4` (≤50 МБ). После первой удачной отправки `file_id` сохраняется —
  дальше Telegram отдаёт ролик из своего кеша, файл не гоняется. Протухший `file_id` сбрасывается, ошибка не роняет диалог.
- Где используется: `/start` для **новых** пользователей (тизер перед приветствием) и карточка товара с флагом
  `"teaser": true` в `catalog.json` (сейчас — только футболка): вместо альбома уходит видео с подписью и inline-кнопками.
- Тесты: `TeaserTests` (4).

## Сторис
`tg.shareToStory(media_url)` требует **абсолютный публичный HTTPS-URL** — Telegram скачивает файл сам. Заполнить
`catalog.json → media.teaser_story_url` (можно CDN/объектное хранилище) и `media.story_link` (ссылка на бота; виджет-ссылка
показывается только премиум-пользователям). Пока поле пустое, фронт берёт `assets/video/teaser-720.mp4` относительно текущего origin.

## Прод
- За HTTPS-прокси лучше отдавать `/assets/video/` напрямую nginx/Caddy (Range и кеш из коробки, поток бота не занят видео).
- Образ вырос на ~5 МБ (`COPY miniapp ./miniapp` уже включает `assets/video`).
- Для сторис через Bot API (`InputStoryContentVideo`) формат другой: 720×1280, **H.265**, keyframe каждую секунду, ≤30 МБ — отдельный рендер.
