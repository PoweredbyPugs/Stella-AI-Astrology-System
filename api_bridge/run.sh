#!/bin/sh
set -eu
HERE="/Volumes/Shirahoshi/HermesNode/clawd/stella/api_bridge"
set -a
. "$HERE/.env.api"
set +a
cd "$HERE"
exec /Volumes/Shirahoshi/HermesNode/clawd/stella/.venv/bin/python app.py
