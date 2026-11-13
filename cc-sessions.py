#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""TUI со списком всех чатов Claude Code из ~/.claude/projects.

Enter — продолжить чат (cd в его каталог + claude --resume; удалённый каталог
создаётся заново), / — фильтр, q/Esc — выход. --list — печать без TUI.
"""
import curses
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path.home() / '.claude' / 'projects'


def parse(path):
    """Достаёт из jsonl-лога cwd, заголовок, первый промпт и статистику."""
    s = {'id': path.stem, 'cwd': '', 'title': '', 'ai': '', 'first': '',
         'mtime': path.stat().st_mtime, 'cost': None, 'ctx': None}
    last = ''  # последний ответ модели: из его usage — текущий контекст
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if ('"type":"assistant"' in line and '"usage"' in line
                    and '"isSidechain":true' not in line
                    and '"model":"<synthetic>"' not in line):
                last = line
                continue
            # Быстрый фильтр: json.loads только для нужных строк.
            if not ('"cwd"' in line or 'title' in line
                    or '"cost-state"' in line):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = d.get('type')
            if t == 'cost-state':
                # Итог накопительный; после отката истории (rewind) он
                # уменьшается, а максимум — реально потраченное.
                if d.get('totalCostUSD', 0) >= (s['cost'] or {}).get(
                        'totalCostUSD', -1):
                    s['cost'] = d
            elif t == 'custom-title':
                s['title'] = d.get('customTitle') or s['title']
            elif t == 'ai-title':
                s['ai'] = d.get('aiTitle') or s['ai']
            elif t == 'user' and not s['first']:
                s['cwd'] = s['cwd'] or d.get('cwd', '')
                c = d.get('message', {}).get('content')
                if isinstance(c, list):
                    c = ' '.join(x.get('text', '') for x in c
                                 if isinstance(x, dict))
                s['first'] = ' '.join(str(c or '').split())
    try:
        u = json.loads(last)['message']['usage']
        s['ctx'] = sum(u.get(k, 0) for k in (
            'input_tokens', 'cache_read_input_tokens',
            'cache_creation_input_tokens'))
    except (ValueError, KeyError, TypeError):
        pass
    s['name'] = s['title'] or s['ai'] or s['first'] or '(без названия)'
    return s if s['cwd'] else None  # пустые сессии без сообщений не нужны


def load():
    # Только верхний уровень: */<id>/subagents/*.jsonl — это сабагенты.
    items = (parse(p) for p in ROOT.glob('*/*.jsonl'))
    return sorted((s for s in items if s), key=lambda s: -s['mtime'])


def row(s):
    mark = ' ' if os.path.isdir(s['cwd']) else '✗'
    when = time.strftime('%d.%m %H:%M', time.localtime(s['mtime']))
    cwd = s['cwd'].replace(str(Path.home()), '~')
    c = s['cost'] or {}
    usage = c.get('modelUsage') or {}
    # Основная модель — самая дорогая (haiku крутится в каждом чате фоном).
    model = max(usage, key=lambda m: usage[m].get('costUSD', 0), default='')
    model = model.split('-')[1] if model.count('-') else model
    ctx = f"{s['ctx'] / 1000:.0f}k" if s['ctx'] else ''
    cost = f"${c['totalCostUSD']:.2f}" if c else ''
    lines = (f"+{c.get('totalLinesAdded', 0)}/−{c.get('totalLinesRemoved', 0)}"
             if c else '')
    return (f"{when} {mark} {s['name'][:45]:<45} {model:>5} {ctx:>5} "
            f"{cost:>7} {lines:>11}  {cwd}")


def match(s, q):
    hay = ' '.join((s['name'], s['first'], s['cwd'], s['id'])).lower()
    return all(w in hay for w in q.lower().split())


def tui(scr, sessions):
    curses.curs_set(0)
    curses.use_default_colors()
    q, pos, top, typing = '', 0, 0, False
    while True:
        shown = [s for s in sessions if match(s, q)]
        pos = max(0, min(pos, len(shown) - 1))
        h, w = scr.getmaxyx()
        body = h - 4
        top = min(max(top, pos - body + 1), pos)
        scr.erase()
        head = f' Чаты Claude Code: {len(shown)}/{len(sessions)}   ✗ — каталога нет'
        scr.addnstr(0, 0, head.ljust(w), w - 1, curses.A_REVERSE)
        for i, s in enumerate(shown[top:top + body]):
            attr = curses.A_REVERSE if top + i == pos else 0
            scr.addnstr(1 + i, 0, row(s), w - 1, attr)
        if shown:
            cur = shown[pos]
            scr.addnstr(h - 3, 0, f" {cur['id']}  {cur['cwd']}", w - 1,
                        curses.A_DIM)
            scr.addnstr(h - 2, 0, ' > ' + cur['first'], w - 1, curses.A_DIM)
        foot = (f' /{q}_' if typing else
                f' ↑↓ PgUp/PgDn  Enter открыть  / фильтр [{q}]  q выход')
        scr.addnstr(h - 1, 0, foot, w - 1, curses.A_BOLD)
        k = scr.get_wch()
        if typing:
            if k in ('\n', '\x1b'):
                typing = False
            elif k in ('\x7f', '\b', curses.KEY_BACKSPACE):
                q = q[:-1]
            elif isinstance(k, str) and k.isprintable():
                q, pos = q + k, 0
            continue
        if k in ('q', '\x1b'):
            return None
        if k == '/':
            typing = True
        elif k in (curses.KEY_UP, 'k'):
            pos -= 1
        elif k in (curses.KEY_DOWN, 'j'):
            pos += 1
        elif k == curses.KEY_PPAGE:
            pos -= body
        elif k == curses.KEY_NPAGE:
            pos += body
        elif k == curses.KEY_HOME:
            pos = 0
        elif k == curses.KEY_END:
            pos = len(shown) - 1
        elif k == '\n' and shown:
            return shown[pos]


def resume(s):
    cwd = s['cwd']
    if not os.path.isdir(cwd):
        # claude ищет чат по каталогу запуска, поэтому воссоздаём его пустым.
        print(f'Каталог {cwd} удалён — создаю пустой, чтобы открыть чат.')
        os.makedirs(cwd)
    os.chdir(cwd)
    os.execvp('claude', ['claude', '--resume', s['id']])


def main():
    sessions = load()
    if '--list' in sys.argv:
        print('\n'.join(row(s) + '  ' + s['id'] for s in sessions))
        return
    os.environ.setdefault('ESCDELAY', '25')  # иначе Esc ждёт 1 с
    chosen = curses.wrapper(tui, sessions)
    if chosen:
        resume(chosen)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:  # Ctrl+C — тихий выход без трейса
        sys.exit(130)
