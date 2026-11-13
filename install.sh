#!/bin/sh
# Installs the lostchats command: a symlink in ~/.local/bin to cc-sessions.py.
set -e
dir=$(cd "$(dirname "$0")" && pwd)
bin="$HOME/.local/bin"
mkdir -p "$bin"
chmod +x "$dir/cc-sessions.py"
ln -sfn "$dir/cc-sessions.py" "$bin/lostchats"
echo "lostchats -> $dir/cc-sessions.py"
case ":$PATH:" in
    *":$bin:"*) ;;
    *) echo "Add $bin to your PATH: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc" ;;
esac
