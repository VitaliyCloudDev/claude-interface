#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""TUI listing all Claude Code (~/.claude/projects) and Codex
(~/.codex/sessions) chats.

Enter — resume the chat (cd into its directory + claude --resume / codex
resume; a deleted directory is recreated), / — filter, ←→ or header click —
sort (click again or r — reverse order), q/Esc — quit.
--list — print without TUI.
"""
import bisect
import curses
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path.home() / '.claude' / 'projects'
CODEX = Path.home() / '.codex'


def parse(path):
    """Extract cwd, title, first prompt and stats from a jsonl log."""
    s = {'app': 'claude', 'id': path.stem, 'cwd': '', 'title': '', 'ai': '', 'first': '',
         'mtime': path.stat().st_mtime, 'cost': None, 'ctx': None}
    last = ''  # last model reply: its usage gives the current context
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if ('"type":"assistant"' in line and '"usage"' in line
                    and '"isSidechain":true' not in line
                    and '"model":"<synthetic>"' not in line):
                last = line
                continue
            # Fast filter: json.loads only the lines we need.
            if not ('"cwd"' in line or 'title' in line
                    or '"cost-state"' in line):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = d.get('type')
            if t == 'cost-state':
                # The total is cumulative; after a rewind it drops, so the
                # maximum is what was actually spent.
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
    usage = (s['cost'] or {}).get('modelUsage') or {}
    # Main model is the costliest one (haiku runs in every chat in background).
    m = max(usage, key=lambda m: usage[m].get('costUSD', 0), default='')
    s['model'] = m.split('-')[1] if m.count('-') else m
    s['name'] = s['title'] or s['ai'] or s['first'] or '(untitled)'
    return s if s['cwd'] else None  # skip empty sessions


def parse_codex(path):
    """Same for a Codex rollout log; it has no cost or diff."""
    s = {'app': 'codex', 'id': '', 'cwd': '', 'title': '', 'ai': '',
         'first': '', 'mtime': path.stat().st_mtime, 'cost': None,
         'ctx': None, 'model': ''}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not ('"session_meta"' in line or '"turn_context"' in line
                    or '"token_count"' in line or 'UserMessage' in line):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            p = d.get('payload') or {}
            if d.get('type') == 'session_meta':
                s['id'] = s['id'] or p.get('id', '')
                s['cwd'] = s['cwd'] or p.get('cwd', '')
            elif d.get('type') == 'turn_context':
                s['model'] = (p.get('model') or '').split('-')[-1]
            elif p.get('type') == 'token_count' and p.get('info'):
                s['ctx'] = p['info']['last_token_usage']['input_tokens']
            # Real input is UserMessage; role=user in response_item also
            # includes injected AGENTS.md and environment_context.
            elif (p.get('type') == 'item_completed' and not s['first']
                  and p.get('item', {}).get('type') == 'UserMessage'):
                c = p['item'].get('content') or []
                s['first'] = ' '.join(' '.join(
                    x.get('text', '') for x in c if isinstance(x, dict)).split())
    return s if s['id'] and s['first'] else None  # skip empty ones


def load_codex():
    names = {}
    try:
        with open(CODEX / 'session_index.jsonl', encoding='utf-8') as f:
            for line in f:  # the last record is the current name
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                names[d.get('id')] = d.get('thread_name') or ''
    except OSError:
        pass
    # A thread may continue in a new file with the same id: go in creation
    # order and take the first prompt from the earliest file.
    out = {}
    files = [*CODEX.glob('sessions/*/*/*/*.jsonl'),
             *CODEX.glob('archived_sessions/*.jsonl')]
    for p in sorted(files, key=lambda p: p.name):
        s = parse_codex(p)
        if s:
            s['first'] = out.get(s['id'], s)['first']
            s['name'] = names.get(s['id']) or s['first']
            out[s['id']] = s
    return list(out.values())


def load():
    # Top level only: */<id>/subagents/*.jsonl are subagents.
    items = [parse(p) for p in ROOT.glob('*/*.jsonl')] + load_codex()
    return sorted((s for s in items if s), key=lambda s: -s['mtime'])


def cols(when, mark, name, model, ctx, cost, lines, cwd):
    return (f"{when:<11} {mark} {name[:45]:<45} │ {model:<6} │ {ctx:>5} │ "
            f"{cost:>6} │ {lines:>5} │ {cwd}")


LABELS = ('Modified', 'Title', 'Model', 'Ctx', 'Cost', 'Diff', 'Directory')
# Sort key of each column and default order (numbers descending).
SORTS = (
    (lambda s: s['mtime'], True),
    (lambda s: s['name'].lower(), False),
    (lambda s: s['model'], False),
    (lambda s: s['ctx'] or 0, True),
    (lambda s: (s['cost'] or {}).get('totalCostUSD', 0), True),
    (lambda s: max((s['cost'] or {}).get(k, 0)  # as shown in the column
                   for k in ('totalLinesAdded', 'totalLinesRemoved')), True),
    (lambda s: s['cwd'], False),
)


def header(sort=None, rev=False):
    lbl = list(LABELS)
    if sort is not None:
        lbl[sort] += '▼' if rev else '▲'
    return cols(lbl[0], ' ', *lbl[1:])


HEADER = header()
BARS = [i for i, c in enumerate(HEADER) if c == '│']


def column(x):
    """Header column index under screen position x."""
    i = bisect.bisect(BARS, x)
    return i + 1 if i else int(x > 12)  # left of first │: Modified, Title


def row(s):
    mark = ' ' if os.path.isdir(s['cwd']) else '✗'
    when = time.strftime('%d.%m %H:%M', time.localtime(s['mtime']))
    cwd = s['cwd'].replace(str(Path.home()), '~')
    c = s['cost'] or {}
    ctx = f"{s['ctx'] / 1000:.0f}k" if s['ctx'] else ''
    cost = f"${c['totalCostUSD']:.2f}" if c else ''
    # Show removed lines only if there are more of them than added.
    add, rm = c.get('totalLinesAdded', 0), c.get('totalLinesRemoved', 0)
    lines = f'+{add}' if add >= rm else f'-{rm}'
    lines = lines if add or rm else ''
    return cols(when, mark, s['name'], s['model'], ctx, cost, lines, cwd)


def match(s, q):
    hay = ' '.join((s['name'], s['first'], s['cwd'], s['id'],
                    s['app'])).lower()
    return all(w in hay for w in q.lower().split())


def tui(scr, sessions):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.mousemask(curses.BUTTON1_CLICKED | curses.BUTTON4_PRESSED
                     | curses.BUTTON5_PRESSED)
    curses.mouseinterval(0)  # no delay for double-click detection
    q, pos, top, typing = '', 0, 0, False
    sort, rev, keep = 0, True, None
    while True:
        shown = sorted((s for s in sessions if match(s, q)),
                       key=SORTS[sort][0], reverse=rev)
        # Keep the same chat selected after re-sorting.
        pos = next((i for i, s in enumerate(shown) if s is keep), pos)
        keep = None
        pos = max(0, min(pos, len(shown) - 1))
        h, w = scr.getmaxyx()
        body = h - 5
        top = min(max(top, pos - body + 1), pos)
        scr.erase()
        head = f' Chats: {len(shown)}/{len(sessions)}'
        scr.addnstr(0, 0, head.ljust(w), w - 1, curses.A_REVERSE)
        scr.addnstr(1, 0, header(sort, rev), w - 1, curses.A_BOLD)
        for i, s in enumerate(shown[top:top + body]):
            attr = curses.A_REVERSE if top + i == pos else 0
            scr.addnstr(2 + i, 0, row(s).ljust(w), w - 1, attr)
        if shown:
            cur = shown[pos]
            scr.addnstr(h - 3, 0, f" {cur['id']}  {cur['cwd']}", w - 1,
                        curses.A_DIM)
            scr.addnstr(h - 2, 0, ' > ' + cur['first'], w - 1, curses.A_DIM)
        foot = (f' /{q}_' if typing else
                f' ↑↓ PgUp/PgDn  Enter open  ←→ sort  r reverse  / filter [{q}]'
                '  q quit')
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
        new = None  # new sort (column, order)
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
        elif k in (curses.KEY_LEFT, curses.KEY_RIGHT):
            c = (sort + (1 if k == curses.KEY_RIGHT else -1)) % len(SORTS)
            new = c, SORTS[c][1]
        elif k == 'r':
            new = sort, not rev
        elif k == curses.KEY_MOUSE:
            try:
                _, x, y, _, b = curses.getmouse()
            except curses.error:  # event outside the mask
                continue
            if b & curses.BUTTON4_PRESSED:
                pos -= 3
            elif b & curses.BUTTON5_PRESSED:
                pos += 3
            elif y == 1:
                c = column(x)
                new = c, (not rev if c == sort else SORTS[c][1])
            elif 2 <= y < 2 + body and top + y - 2 < len(shown):
                pos = top + y - 2
        elif k == '\n' and shown:
            return shown[pos]
        if new:
            keep, (sort, rev) = (shown[pos] if shown else None), new


def resume(s):
    cwd = s['cwd']
    if not os.path.isdir(cwd):
        # claude looks up the chat by launch directory, so recreate it empty
        # (codex finds it by id, but also runs in the launch directory).
        print(f'Directory {cwd} is gone — recreating it empty to open the chat.')
        os.makedirs(cwd)
    os.chdir(cwd)
    cmd = (['codex', 'resume', s['id']] if s['app'] == 'codex'
           else ['claude', '--resume', s['id']])
    os.execvp(cmd[0], cmd)


def main():
    sessions = load()
    if '--list' in sys.argv:
        print(HEADER + '  ID')
        print('\n'.join(row(s) + '  ' + s['id'] for s in sessions), flush=True)
        return
    os.environ.setdefault('ESCDELAY', '25')  # otherwise Esc waits 1 s
    chosen = curses.wrapper(tui, sessions)
    if chosen:
        resume(chosen)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:  # Ctrl+C — quiet exit without traceback
        sys.exit(130)
    except BrokenPipeError:  # --list | head: reader closed the pipe
        # Recipe from the signal docs: else the stdout flush tracebacks.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
