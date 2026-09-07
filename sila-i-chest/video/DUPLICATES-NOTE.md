# Дубликаты, не скопированные в проект

Эти файлы идентичны (md5 совпадает) уже подключённым ассетам витрины в
`miniapp/assets/video/` — чтобы не раздувать проект, они оставлены только там:

| исходник (архив) | копия в проекте |
|---|---|
| video/sila-i-chest-hero-loop.mp4 | miniapp/assets/video/hero-loop.mp4 |
| video/sila-i-chest-teaser-720.mp4 | miniapp/assets/video/teaser-720.mp4 |
| video/sila-i-chest-story-h265.mp4 | miniapp/assets/video/teaser-story-h265.mp4 |
| video/sila-i-chest-hero-poster.jpg | miniapp/assets/video/hero-poster.jpg |
| video/sila-i-chest-teaser-poster.jpg | miniapp/assets/video/teaser-poster.jpg |

Также в проект не копировались транспортные артефакты `handoff/draft-sila-i-chest.bundle`
и `handoff/patches/*.patch` — всё их содержимое теперь живёт в git-истории проекта
(ветка `draft/sila-i-chest`, коммиты 23d37e1…cb97dfc).
