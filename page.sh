#!/bin/sh
# Serve the board as a web page at http://127.0.0.1:8765
#
#   ./page.sh          start it (foreground; Ctrl-C stops it)
#   ./page.sh 9000     ... on another port, if 8765 is taken
#   ./page.sh --build  render index.html once and exit, no server
#
# It draws every project beside this workshop, straight from their docs/PLAN.md.
# The page holds NO state of its own -- it renders the files. If it ever
# disagrees with a PLAN.md, the PLAN.md is right.
#
# FIRST RENDER IS SLOW. It replays every revision of every plan file and shells
# out per project. Give it a minute before deciding it is broken.
set -eu
SHOP="$(cd "$(dirname "$0")" && pwd)"
case "${1:-}" in
    --build)
        echo "rendering once …"
        python3 "$SHOP/dashboard/collect_all.py" "$SHOP" > "$SHOP/dashboard/workshop.json.tmp"
        mv "$SHOP/dashboard/workshop.json.tmp" "$SHOP/dashboard/workshop.json"
        python3 "$SHOP/dashboard/render_workshop.py" "$SHOP/dashboard/workshop.json" > "$SHOP/index.html.tmp"
        mv "$SHOP/index.html.tmp" "$SHOP/index.html"
        echo "ok    $SHOP/index.html — open it in a browser"
        ;;
    *)
        PORT="${1:-8765}"
        echo "serving http://127.0.0.1:$PORT   (Ctrl-C to stop)"
        exec python3 "$SHOP/serve.py" "$PORT"
        ;;
esac
