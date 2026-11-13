# claude-interface

TUI со списком всех чатов Claude Code из всех каталогов, чтобы находить и продолжать их, даже если каталог удалён или перемещён.

- `cc-sessions.py` — единственный файл, только stdlib (curses), без зависимостей.
- Команда `claude-interface` — симлинк `~/.local/bin/claude-interface` → `cc-sessions.py`, создаёт `install.sh`.
- Лицензия GPL-3.0 (`LICENSE`).
- Режимы: без аргументов — TUI (↑↓/PgUp/PgDn, `/` фильтр, Enter открыть, q/Esc выход); `--list` — печать списка.

## Как устроено

- Чаты: `~/.claude/projects/<slug каталога>/<session-id>.jsonl`, берутся только файлы верхнего уровня (`<id>/subagents/` — логи сабагентов).
- Из jsonl: `cwd` и первый промпт — из первой записи `type: user`; название — последняя `custom-title` (`/rename`), иначе последняя `ai-title`.
- Колонки статистики: модель, $ и +/− строк — из записи `cost-state` с максимальным `totalCostUSD` (итог накопительный, после rewind уменьшается; модель — самая дорогая в `modelUsage`); контекст — сумма input+cache токенов в `usage` последнего ответа `assistant` (без сабагентов и `<synthetic>`).
- Enter: `cd <cwd> && exec claude --resume <id>`. Claude ищет чат по slug каталога запуска, поэтому удалённый каталог создаётся заново пустым.
- Встроенная альтернатива: `/resume` → Ctrl+A показывает все проекты, но чат из удалённого каталога так не открыть.
- Логи хранятся `cleanupPeriodDays` дней (по умолчанию 30); в `~/.claude/settings.json` выставлено 3650.

## Проверка

`./cc-sessions.py --list` должен вывести чаты без ошибок; TUI проверять в tmux через `send-keys`/`capture-pane`.
