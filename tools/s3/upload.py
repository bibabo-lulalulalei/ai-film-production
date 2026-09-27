# -*- coding: utf-8 -*-
"""Upload a local file or a remote URL to S3 and print the CDN URL.

Standalone script with no framework dependencies.

Usage:
  python tools/s3/upload.py <path-or-url> [<path-or-url> ...]
  python tools/s3/upload.py <path-or-url> --prefix shots/ --config path/to/s3.env

Configuration (endpoint / bucket / keys / CDN host) is read, in order, from:
  1. --config <file>            simple KEY=VALUE file
  2. environment variables
  3. tools/s3/s3.env             optional local file (never commit secrets)
Variables:
  OSS_ENDPOINT_URL, OSS_BUCKET_NAME, OSS_ACCESS_KEY_ID,
  OSS_SECRET_KEY_SECRET, OSS_ANTI_THEFT_CHAIN.

The object key is the MD5 of the file *content*, so uploading the same file
twice is idempotent and returns the same URL. Requires boto3 (pip install boto3).
"""
import argparse
import hashlib
import io
import mimetypes
import os
import sys

try:
    import boto3
    from botocore.config import Config
except ImportError:
    print("ERROR: 缺少依赖 boto3，请先运行: pip install boto3")
    sys.exit(1)

ENV_VARS = ("OSS_ENDPOINT_URL", "OSS_BUCKET_NAME", "OSS_ACCESS_KEY_ID",
            "OSS_SECRET_KEY_SECRET", "OSS_ANTI_THEFT_CHAIN")


def load_env_file(path):
    """Parse a minimal KEY=VALUE file (no python-dotenv dependency)."""
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


def s3_config():
    missing = [name for name in ENV_VARS if not os.environ.get(name)]
    if missing:
        die("缺少 S3 配置: " + ", ".join(missing)
            + "。设置环境变量，或复制 s3.env.example 为 tools/s3/s3.env 填写"
              "（也可用 --config 指定）。")
    return {
        "endpoint_url": os.environ["OSS_ENDPOINT_URL"],
        "bucket_name": os.environ["OSS_BUCKET_NAME"],
        "access_key_id": os.environ["OSS_ACCESS_KEY_ID"],
        "secret_key": os.environ["OSS_SECRET_KEY_SECRET"],
        "cdn_base": os.environ["OSS_ANTI_THEFT_CHAIN"].rstrip("/"),
    }


def fetch(path_or_url):
    """Return (data, content_type) for a local path or an http(s) URL."""
    if path_or_url.lower().startswith(("http://", "https://")):
        import httpx
        resp = httpx.get(path_or_url, timeout=120.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.content, resp.headers.get("content-type", "")
    if not os.path.isfile(path_or_url):
        raise FileNotFoundError(f"文件不存在: {path_or_url}")
    with open(path_or_url, "rb") as f:
        data = f.read()
    content_type, _ = mimetypes.guess_type(path_or_url)
    return data, content_type or ""


def object_key(data, source, prefix):
    """Content MD5 + extension; extension from source filename, then mime."""
    digest = hashlib.md5(data).hexdigest()
    ext = os.path.splitext(source.split("?")[0])[1]
    if not ext:
        ext = mimetypes.guess_extension(
            mimetypes.guess_type(source)[0] or "application/octet-stream") or ""
    return f"{prefix}{digest}{ext}"


def upload(path_or_url, prefix="", conf=None):
    conf = conf or s3_config()
    data, content_type = fetch(path_or_url)
    if not content_type:
        content_type = "application/octet-stream"
    key = object_key(data, path_or_url, prefix)

    client = boto3.client(
        "s3",
        aws_access_key_id=conf["access_key_id"],
        aws_secret_access_key=conf["secret_key"],
        endpoint_url=conf["endpoint_url"],
        config=Config(signature_version="s3v4",
                      s3={"addressing_style": "virtual"}),
    )
    client.upload_fileobj(io.BytesIO(data), conf["bucket_name"], key,
                          ExtraArgs={"ContentType": content_type})
    return f"{conf['cdn_base']}/{key}"


def die(msg, code=1):
    print(f"ERROR: {msg}")
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser(description="上传本地文件/远程 URL 到 S3，返回 CDN 链接")
    ap.add_argument("paths", nargs="+", help="本地路径或 http(s) URL")
    ap.add_argument("--prefix", default="", help="对象 key 前缀，如 shots/")
    ap.add_argument("--config", help="KEY=VALUE 配置文件路径")
    args = ap.parse_args()

    load_env_file(args.config)
    if not args.config:
        load_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "s3.env"))
    conf = s3_config()

    failed = 0
    for source in args.paths:
        try:
            print(upload(source, args.prefix, conf))
        except Exception as e:
            print(f"上传失败 {source}: {e}", file=sys.stderr)
            failed += 1
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
