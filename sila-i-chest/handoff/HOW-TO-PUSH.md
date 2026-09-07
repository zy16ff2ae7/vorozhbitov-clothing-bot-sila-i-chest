# Как отправить ветку draft/sila-i-chest в GitHub

В песочнице нет доступа к репозиторию на запись (нет remote и токена), поэтому ветка упакована.
Основание — `main` = `f142641` (текущий upstream, не изменялся).

## Вариант 1 — bundle (сохраняет хеши коммитов)
```bash
git clone https://github.com/zy16ff2ae7/vorozhbitov-clothing-bot-update.git
cd vorozhbitov-clothing-bot-update
git fetch ../draft-sila-i-chest.bundle draft/sila-i-chest:draft/sila-i-chest
git push -u origin draft/sila-i-chest
```

## Вариант 2 — патчи
```bash
git checkout -b draft/sila-i-chest main
git am ../patches/*.patch
git push -u origin draft/sila-i-chest
```

Дальше — Pull Request `draft/sila-i-chest → main`; сливать только после согласования кадров, цены, размеров и ткани.
Проверка перед слиянием: `python3 -m unittest test_bot` (28 тестов), `python3 preview_server.py` → http://localhost:4173/.
