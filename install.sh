#!/bin/sh
# Ставит команду claude-interface: симлинк в ~/.local/bin на cc-sessions.py.
set -e
dir=$(cd "$(dirname "$0")" && pwd)
bin="$HOME/.local/bin"
mkdir -p "$bin"
chmod +x "$dir/cc-sessions.py"
ln -sfn "$dir/cc-sessions.py" "$bin/claude-interface"
echo "claude-interface -> $dir/cc-sessions.py"
case ":$PATH:" in
    *":$bin:"*) ;;
    *) echo "Добавьте $bin в PATH: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc" ;;
esac
