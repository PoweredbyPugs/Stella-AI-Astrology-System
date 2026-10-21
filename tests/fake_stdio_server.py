"""Stand-in for stella_server.py in the WebSocket bridge tests.

Reads newline-delimited JSON-RPC from stdin and answers each request with a
result that echoes the method and this process's pid, so the tests can check
both the framing and that the child dies with its socket.
"""
import json
import os
import sys

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    reply = {"jsonrpc": "2.0", "id": msg.get("id"),
             "result": {"echo": msg.get("method"), "pid": os.getpid()}}
    if msg.get("method") == "big":
        # a tools/list from the real server is a few hundred KiB on one line
        reply["result"]["pad"] = "x" * 300_000
    sys.stdout.write(json.dumps(reply) + "\n")
    sys.stdout.flush()
