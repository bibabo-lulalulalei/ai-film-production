# -*- coding: utf-8 -*-
"""Web search via a Smart Search endpoint.

Standalone synchronous script with no framework dependencies.

Usage:
  python tools/search/web_search.py <query> [-n 8] [--json]

Configuration (environment variables, or an --config KEY=VALUE file):
  SEARCH_ENGINE_HOST            full search endpoint URL
  SEARCH_ENGINE_SUBSCRIPTION_KEY

Default output is a readable markdown list (title / url / snippet);
--json prints the raw result items. This tool does text research only —
the pipeline no longer collects reference images, so there is no image
answer or download mode.
"""
import argparse
import json
import os
import sys

import httpx


def load_env_file(path):
    if not path or not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            key, sep, value = line.partition("=")
            if sep:
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def die(msg, code=1):
    print(f"ERROR: {msg}")
    sys.exit(code)


def search_config():
    host, key = os.environ.get("SEARCH_ENGINE_HOST"), \
                 os.environ.get("SEARCH_ENGINE_SUBSCRIPTION_KEY")
    if not host or not key:
        die("缺少配置 SEARCH_ENGINE_HOST / SEARCH_ENGINE_SUBSCRIPTION_KEY"
            "（或用 --config 指定文件）。")
    return host, key


def web_search(query, count):
    host, key = search_config()
    resp = httpx.get(
        host, headers={"Authorization": f"Bearer {key}"},
        params={"q": query, "count": count}, timeout=60.0,
        follow_redirects=True)
    resp.raise_for_status()
    return resp.json().get("webPages", {}).get("value", [])


def main():
    ap = argparse.ArgumentParser(description="Smart Search 联网文本搜索")
    ap.add_argument("query")
    ap.add_argument("-n", "--count", type=int, default=8, help="返回条数（默认 8）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--config", help="KEY=VALUE 配置文件")
    args = ap.parse_args()

    load_env_file(args.config)
    results = web_search(args.query, args.count)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    for i, item in enumerate(results, 1):
        print(f"{i}. {item.get('name', '')}\n"
              f"   {item.get('url', '')}\n"
              f"   {item.get('snippet', '')}\n")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
