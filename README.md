# claude-interface

<img width="849" height="706" alt="claude-interface" src="https://github.com/user-attachments/assets/1b601c04-f9e3-457e-8fff-21f61ad59abf" />


**English** | [Русский](README.ru.md)

A handy list of all your Claude Code chats, right in the terminal.

Why it beats the built-in `/resume`:

- **All chats in one list** — from every directory at once. Each shows its title, directory, time, main model, current context size, cost and lines added/removed — heavy chats stand out; the selected one also shows its first prompt.
- **Easy navigation** — arrows or `j`/`k`, paging, and a quick word filter (`/`).
- **Hidden chats too** — every chat log on disk is listed, including ones the built-in Claude Code interface doesn't show.
- **Any chat opens** — even if its directory was deleted or moved.

## Installation

Only Python 3 is required, no external dependencies.

```bash
./install.sh
```

The script creates a symlink `~/.local/bin/claude-interface` → `cc-sessions.py` and warns if `~/.local/bin` is not in your `PATH`. Run it again after moving the repository.

## Usage

```bash
claude-interface          # TUI
claude-interface --list   # just print the list
```

Each row shows the last modification time, chat title, directory and id. A `✗` marks chats whose directory no longer exists. The bottom of the screen shows the id, full path and first prompt of the selected chat.

| Key | Action |
|---|---|
| ↑↓ / `j` `k` | move |
| PgUp / PgDn, Home / End | page up/down, jump to start / end |
| `/` | filter: space-separated words are matched against title, first prompt, path and id; Enter or Esc finishes input |
| Enter | open chat |
| `q` / Esc | quit |

Enter runs `cd <directory> && claude --resume <id>`. Claude looks up chats by the launch directory, so a deleted directory is recreated, empty.

## Where the data comes from

- Logs live in `~/.claude/projects/<directory>/<session-id>.jsonl`. Only top-level files are read; subagent logs are skipped.
- Directory and first prompt come from the first user message. The title is the one set via `/rename`, otherwise the auto-generated title, otherwise the first prompt.
- Empty chats with no messages are hidden.

By default Claude Code deletes logs older than 30 days. To keep history longer, raise `cleanupPeriodDays` in `~/.claude/settings.json`:

```json
{ "cleanupPeriodDays": 3650 }
```

## License

[GPL-3.0](LICENSE). Forks and modified versions may only be distributed as open source under the same license.
