# termius-dynamic-tab-titles

Понятные названия вкладок для Termius.

HTTP/HTTPS-ссылки открываются во внешнем браузере по умолчанию. Для ссылки в терминале используйте Ctrl + клик.

## Примеры

| Состояние                                                     | Название                      |
|---------------------------------------------------------------|-------------------------------|
| Открыт путь `~/projects/backend`                              | `~/projects/backend`          |
| Запущена команда `npm run start:dev`                          | `backend · npm run start:dev` |
| Выполнен snippet `cd ~/projects/backend && npm run start:dev` | `backend · npm run start:dev` |
| Команда с аргументами `ciadpi -Kt,h -d1 …`                    | `backend · ciadpi`            |
| Команда через SSH                                             | `server · npm run start:dev`  |

## Требования

Linux, **Termius 9.37.2**, **Electron 21**, Python 3.10+ и **fish**. Для обновления названий нужна работающая
интеграция Termius с оболочкой, в том числе на SSH-сервере. Другие версии Termius, Windows и macOS пока не
поддерживаются.

## Установка

```bash
git clone https://github.com/klishin16/termius-dynamic-tab-titles.git
cd termius-dynamic-tab-titles
./install.sh
```

Установщик создаёт отдельную копию в `~/.local/share/termius-dynamic-tab-titles` (или в `$XDG_DATA_HOME`) и ярлык *
*Termius Dynamic Tab Titles**. Копия использует существующий профиль с подключениями и сниппетами.

Полностью закройте Termius, запустите новый ярлык и откройте новую локальную вкладку.

По умолчанию используются `/opt/termius/app.asar` и `electron21`. Свои пути можно указать так:

```bash
./install.sh --source /path/to/app.asar --electron /path/to/electron21
```

Дополнительно доступны `--prefix` для каталога копии и `--desktop-dir` для ярлыка.

## Обновление и удаление

Для обновления закройте приложение и выполните:

```bash
git pull
./install.sh
```

Для удаления копии и ярлыка:

```bash
./uninstall.sh
```

Если при установке задавали параметры, повторите их при обновлении; при удалении укажите тот же `--prefix`. Оригинальный
Termius и его профиль сохраняются.

## Проверки

Нужен Node.js; для интеграционной проверки — также fish и установленный Termius.

```bash
python3 -m unittest discover -s tests -v
python3 tests/integration.py --source /opt/termius/app.asar
```
