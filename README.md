# claude-interface

<img width="849" height="706" alt="claude-interface" src="https://github.com/user-attachments/assets/1b601c04-f9e3-457e-8fff-21f61ad59abf" />

**English** | [Русский](README.ru.md)

A handy list of all your Claude Code and Codex chats, right in the terminal.

**The main thing: no chat gets lost.** The Claude Code and Codex clients show only part of your history — chats from other directories, deleted or moved projects, archived threads are hard or impossible to find there. claude-interface shows every chat log on disk in one list and opens any of them.

Why it beats the built-in `/resume`:

- **All chats in one list** — from every directory at once, Claude Code and Codex together. Each shows its title, directory, time, main model, current context size, cost and lines added/removed — heavy chats stand out; the selected one also shows its first prompt.
- **Easy navigation** — arrows or `j`/`k`, paging, mouse wheel and clicks, sorting by any column and a quick word filter (`/`).
- **Hidden chats too** — every chat log on disk is listed, including ones the built-in interface doesn't show and archived Codex chats.
- **Any chat opens** — even if its directory was deleted or moved.

## Installation

Requires Python 3 on Linux or macOS (on Windows — via WSL: the standard `curses` module is not available there). No external dependencies.

One command, without cloning:

```bash
mkdir -p ~/.local/bin && curl -fsSL https://raw.githubusercontent.com/VitaliyCloudDev/claude-interface/main/cc-sessions.py -o ~/.local/bin/claude-interface && chmod +x ~/.local/bin/claude-interface
```

Or from a clone:

```bash
git clone https://github.com/VitaliyCloudDev/claude-interface.git
cd claude-interface && ./install.sh
```

The script creates a symlink `~/.local/bin/claude-interface` → `cc-sessions.py` (so `git pull` updates it) and warns if `~/.local/bin` is not in your `PATH`. Run it again after moving the repository.

## Usage

```bash
claude-interface          # TUI
claude-interface --list   # just print the list
```

Columns: last modification time, title, main model, context size, cost, lines added (or removed, if there are more of them) and directory. Codex logs have no cost or diff, so those cells are empty. A `✗` marks chats whose directory no longer exists. The bottom of the screen shows the id, full path and first prompt of the selected chat.

| Key | Action |
|---|---|
| ↑↓ / `j` `k`, mouse wheel | move |
| PgUp / PgDn, Home / End | page up/down, jump to start / end |
| click on a row | select |
| ←→, click on a column header | sort by column |
| `r`, click on the same header again | reverse order |
| `/` | filter: space-separated words are matched against title, first prompt, path and id; Enter or Esc finishes input |
| Enter | open chat |
| `q` / Esc | quit |

Enter runs `cd <directory> && claude --resume <id>` (for Codex — `codex resume <id>`). Claude looks up chats by the launch directory, so a deleted directory is recreated, empty.

## Where the data comes from

- Claude Code: `~/.claude/projects/<directory>/<session-id>.jsonl`. Only top-level files are read; subagent logs are skipped. The title is the one set via `/rename`, otherwise the auto-generated title, otherwise the first prompt.
- Codex: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` and `~/.codex/archived_sessions/` (`codex resume` offers to unarchive). Titles come from `~/.codex/session_index.jsonl`; a thread continued in a new file is shown as one chat.
- Empty chats with no messages are hidden.

By default Claude Code deletes logs older than 30 days. To keep history longer, raise `cleanupPeriodDays` in `~/.claude/settings.json`:

```json
{ "cleanupPeriodDays": 3650 }
```

## License

[GPL-3.0](LICENSE). Forks and modified versions may only be distributed as open source under the same license.
