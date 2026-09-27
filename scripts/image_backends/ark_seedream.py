# -*- coding: utf-8 -*-
"""ark_seedream.py — 火山方舟（Volcengine Ark）图片生成适配器。

对应 profile.asset_image：
    backend        "Ark Seedream"
    base_url       默认 https://ark.cn-beijing.volces.com/api/v3/images/generations
    model_id       模型/接入点 ID，如 doubao-seedream-5-0-pro-260628（必填）
    size           分辨率档位 "1K" / "1.5K" / "2K"（5.0 pro/flash）；
                   宽高比不在此指定——按 API 方式 1，由提示词自然语言描述、模型自定
    response_format "b64_json"（适配器直接拿回 bytes）或 "url"
    output_format  "png" / "jpeg"
    watermark      false 时不添加「AI 生成」水印
    timeout_s      请求超时（默认 300）

凭证：环境变量 ARK_API_KEY（火山方舟长效 API Key）。仅标准库。
文档依据：火山方舟《图片生成 API》（2026-09，MinerU 文本归档）。
"""
import base64
import json
import os
import urllib.error
import urllib.request

_DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
_MIME = {".png": "image/png", ".jpeg": "image/jpeg", ".jpg": "image/jpeg",
         ".webp": "image/webp", ".bmp": "image/bmp", ".tiff": "image/tiff",
         ".gif": "image/gif", ".heic": "image/heic", ".heif": "image/heif"}


def _data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = _MIME.get(ext)
    if not mime:
        raise RuntimeError(f"不支持的参考图格式 {path}（API 仅接受 jpeg/png/webp/bmp/tiff/gif/heic/heif）")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def generate(*, prompt_text, reference_paths, target_path, asset_image, root):
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        raise RuntimeError("缺凭证：请先设置环境变量 ARK_API_KEY（火山方舟 API Key）")

    model_id = asset_image.get("model_id")
    if not model_id:
        raise RuntimeError("profile.asset_image.model_id 未登记（如 doubao-seedream-5-0-pro-260628）")

    max_refs = asset_image.get("max_reference_images")
    refs = list(reference_paths or [])
    if max_refs and len(refs) > max_refs:
        raise RuntimeError(f"参考图 {len(refs)} 张超过后端上限 {max_refs}（{target_path}）")

    payload = {"model": model_id, "prompt": prompt_text}
    if refs:
        images = [_data_uri(p) for p in refs]
        payload["image"] = images[0] if len(images) == 1 else images
    if asset_image.get("size"):
        payload["size"] = asset_image["size"]
    if asset_image.get("response_format"):
        payload["response_format"] = asset_image["response_format"]
    if asset_image.get("output_format"):
        payload["output_format"] = asset_image["output_format"]
    if "watermark" in asset_image:
        payload["watermark"] = bool(asset_image["watermark"])

    base_url = asset_image.get("base_url") or _DEFAULT_BASE_URL
    timeout = asset_image.get("timeout_s") or 300
    req = urllib.request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"Ark API HTTP {e.code}: {detail}") from None

    data = body.get("data") or []
    if not data:
        raise RuntimeError(f"Ark API 返回无图片数据: {json.dumps(body, ensure_ascii=False)[:500]}")
    first = data[0]
    if first.get("error"):
        raise RuntimeError(f"Ark API 图片错误: {json.dumps(first['error'], ensure_ascii=False)}")

    if first.get("b64_json"):
        return base64.b64decode(first["b64_json"])
    if first.get("url"):
        with urllib.request.urlopen(first["url"], timeout=timeout) as r:
            return r.read()
    raise RuntimeError(f"Ark API 返回中既无 b64_json 也无 url: {json.dumps(first, ensure_ascii=False)[:500]}")
