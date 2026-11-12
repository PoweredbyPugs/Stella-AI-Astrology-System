"""Octave's two model clients and its forecast cache.

Jev (decision model, TypeSafe systemone) is reached through the `jevkit` package in the checkout named by
JEVKIT_PATH (default ~/hermes-jev-skills); the key is resolved by jevkit itself from TYPESAFE_API_KEY or the
jev keystore. The writer is any OpenAI-compatible chat endpoint: OPENROUTER_API_KEY, FORECAST_MODEL (default
deepseek/deepseek-v4.1-flash), FORECAST_URL (default OpenRouter). The cache is DATA_DIR/forecasts.json,
which the pipelines pass in as `data_dir`.
"""

import json
import math
import os
import socket
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------- Jev

_jevkit = None


def _load_jevkit():
    """Import jevkit.client once, adding JEVKIT_PATH to sys.path; None when it cannot be imported."""
    global _jevkit
    if _jevkit is None:
        path = os.environ.get("JEVKIT_PATH") or os.path.expanduser("~/hermes-jev-skills")
        if path not in sys.path:
            sys.path.insert(0, path)
        try:
            import jevkit.client as client
            _jevkit = client
        except Exception:
            return None
    return _jevkit


def choice(instructions, criteria):
    return {"type": "choice", "instructions": instructions, "criteria": dict(criteria)}


def score(instructions, levels):
    return {"type": "score", "instructions": instructions, "criteria": list(levels)}


def noul(instructions):
    return {"type": "noul", "instructions": instructions}


def level_word(answer):
    """The legend's word for a score answer (nearest level), else None."""
    if not isinstance(answer, dict) or answer.get("type") != "score" or not answer.get("legend"):
        return None
    legend = {str(k): v for k, v in answer["legend"].items()}
    i = min(len(legend) - 1, max(0, math.floor(answer["score"] + 0.5)))
    return legend.get(str(i))


def jev_ask(state, questions, *, timeout=8.0):
    """Ask Jev every question against one state. Never raises."""
    client = _load_jevkit()
    if client is None:
        return {"ok": False, "error": "no_jevkit", "message": "jevkit could not be imported from JEVKIT_PATH"}
    try:
        r = client.ask(state, questions, timeout=timeout, retries=1)
        return {"ok": True, "answers": r["answers"], "latency_ms": r.get("latency_ms"), "model": r.get("jev_model")}
    except client.JevError as e:
        return {"ok": False, "error": e.code, "message": str(e)}
    except Exception as e:
        return {"ok": False, "error": "transport", "message": str(e)}


# ---------------------------------------------------------------- the writer

def writer_config(key=None, model=None, url=None):
    return {
        "key": key if key is not None else os.environ.get("OPENROUTER_API_KEY"),
        "model": model or os.environ.get("FORECAST_MODEL") or "deepseek/deepseek-v4.1-flash",
        "url": url or os.environ.get("FORECAST_URL") or "https://openrouter.ai/api/v1/chat/completions",
    }


def _upstream(message):
    return {"ok": False, "status": 502, "error": "upstream", "message": message}


def _json_or_empty(raw):
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _post(timeout):
    def post(url, body, headers):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return res.status, _json_or_empty(res.read())
        except urllib.error.HTTPError as e:
            return e.code, _json_or_empty(e.read())
    return post


def write(system, prompt, *, max_tokens=1600, timeout=60.0, key=None, model=None, url=None, post=None):
    cfg = writer_config(key, model, url)
    if not cfg["key"]:
        return {"ok": False, "status": 503, "error": "no_key", "message": "no OPENROUTER_API_KEY on the server"}
    body = json.dumps({
        "model": cfg["model"], "max_tokens": max_tokens, "temperature": 0.7,
        # reasoning off: a thinking model would spend the budget on it and send no text
        "reasoning": {"enabled": False},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    }).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {cfg['key']}",
               "HTTP-Referer": "http://octave.lan", "X-Title": "Stella Octave"}
    try:
        status, data = (post or _post(timeout))(cfg["url"], body, headers)
    except Exception as e:
        timed_out = isinstance(e, (socket.timeout, TimeoutError)) or isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError))
        return _upstream("the model did not answer in time" if timed_out else str(e))
    if not 200 <= status < 300:
        err = data.get("error") if isinstance(data, dict) else None
        detail = err.get("message") if isinstance(err, dict) else None
        return _upstream(f"{status}: {detail or 'the model refused the call'}")
    try:
        m = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        m = None
    text = str((m or {}).get("content") or "").strip()
    if not text:
        return _upstream("the model spent its budget reasoning and sent no text" if (m or {}).get("reasoning") else "the model sent no text")
    return {"ok": True, "text": text}


# ---------------------------------------------------------------- the cache

_MEM = {}   # data_dir -> the cache dict, read once
_LOCK = threading.Lock()   # the writing tools run in worker threads


def load_cache(data_dir):
    d = str(data_dir)
    with _LOCK:
        if d not in _MEM:
            try:
                c = json.loads((Path(d) / "forecasts.json").read_text(encoding="utf-8"))
                if not isinstance(c, dict):
                    c = {}
            except Exception:
                c = {}
            _MEM[d] = c
        return _MEM[d]


def save_cache(data_dir, cache):
    d = Path(data_dir)
    with _LOCK:
        d.mkdir(parents=True, exist_ok=True)
        f = d / "forecasts.json"
        tmp = d / "forecasts.json.tmp"
        tmp.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, f)
