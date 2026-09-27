# -*- coding: utf-8 -*-
"""submit_take.py — the only path to a paid video generation ([14]).

It closes the G07 -> paid-submission gap that used to rely on discipline:

  1. a current <SHOT>.freeze.json must exist;
  2. every file hash is recomputed and must equal the frozen one — a prompt
     edited after the gate is rejected (re-freeze requires re-running G07);
  3. the job (workflow / mode / model / images / audios / duration) is
     printed, and the user must confirm on the spot before any paid request
     (--confirm); no silent spending;
  4. the backend adapter performs the actual submit/poll/download; the
     resulting clip is saved to 09-takes/<SHOT>/take_NN.mp4 and the
     provenance (model/workflow/task_id/seed) is written back to gen.json.

Backend HTTP lives in scripts/video_backends/<model>.py (keyed by the gen
model); this runner never hardcodes an endpoint.

Usage:
  python scripts/submit_take.py <root> --shot <SHOT> [--confirm]
"""
import argparse
import datetime
import hashlib
import importlib.util
import os
import sys

from _common import (BOM_PATH, die, dump_json, exists, load_json,
                     load_profile, write_text)

PROMPTS_DIR = os.path.join("08-prompts")
TAKES_DIR = os.path.join("09-takes")
VIDEO_BACKENDS_DIR = os.path.join("scripts", "video_backends")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_freeze(root, shot):
    freeze_rel = os.path.join(PROMPTS_DIR, f"{shot}.freeze.json")
    fpath = os.path.join(root, freeze_rel)
    if not os.path.exists(fpath):
        die(f"未冻结（缺 {freeze_rel}）；先过 G07 再跑 freeze_prompt")
    freeze = load_json(fpath)
    changed, missing = [], []
    for rel, want in freeze.get("files", {}).items():
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            missing.append(rel)
        elif sha256_file(path) != want:
            changed.append(rel)
    if missing:
        die("冻结后文件缺失: " + ", ".join(missing))
    if changed:
        die("冻结后被改动，禁止提交（回 G07 重新冻结）: "
            + ", ".join(changed))
    return freeze


def describe(gen):
    lines = [
        f"  workflow : {gen.get('workflow')}",
        f"  mode     : {gen.get('mode')}",
        f"  model    : {gen.get('model')}",
        f"  duration : {gen.get('duration_s')}s",
        f"  images   : {len(gen.get('ref_images') or [])}",
        f"  videos   : {len(gen.get('ref_videos') or [])}",
        f"  audios   : {len(gen.get('ref_audios') or [])}",
    ]
    return "\n".join(lines)


def load_video_adapter(model):
    slug = (model or "").lower().replace(".", "").replace(" ", "_")
    path = os.path.join(VIDEO_BACKENDS_DIR, f"{slug}.py")
    if not os.path.exists(path):
        die(f"无视频后端适配器 {path}；真实提交需先按 h3.md 实现该适配器")
    spec = importlib.util.spec_from_file_location(slug, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def next_take_path(root, shot):
    d = os.path.join(root, TAKES_DIR, shot)
    n = 1
    while os.path.exists(os.path.join(d, f"take_{n:02d}.mp4")):
        n += 1
    return os.path.join(d, f"take_{n:02d}.mp4"), n


def submit(root, shot, confirm):
    freeze = verify_freeze(root, shot)
    gen_rel = os.path.join(PROMPTS_DIR, f"{shot}.gen.json")
    gen_path = os.path.join(root, gen_rel)
    gen = load_json(gen_path)

    print("将提交以下付费生成作业：")
    print(describe(gen))
    if not confirm:
        die("需当场明确确认：加 --confirm 才会发起付费请求（未确认，已中止）")

    adapter = load_video_adapter(gen.get("model"))
    result = adapter.submit_and_wait(gen=gen, root=root)
    # adapter returns {"bytes":..., "task_id":..., "seed":...}
    take_rel, take_n = next_take_path(root, shot)
    take_abs = os.path.join(root, take_rel)
    os.makedirs(os.path.dirname(take_abs), exist_ok=True)
    with open(take_abs, "wb") as f:
        f.write(result["bytes"])

    # Provenance write-back (was hand-filled before).
    provenance = {
        "model": gen.get("model"),
        "workflow": result.get("task_id") or gen.get("workflow"),
        "seed": result.get("seed"),
        "task_id": result.get("task_id"),
    }
    gen["provenance"] = provenance
    dump_json(gen, gen_path)

    ledger_add(root, shot, take_n, take_rel, provenance)
    print(f"take_{take_n:02d} saved -> {take_rel}")
    print("provenance:", provenance)


def ledger_add(root, shot, take_n, take_rel, provenance):
    path = os.path.join(root, TAKES_DIR, shot, "takes.json")
    ledger = load_json(path) if os.path.exists(path) else {"shot_id": shot, "takes": []}
    ledger["takes"].append({
        "take": take_n,
        "path": take_rel.replace("\\", "/"),
        "status": "produced",
        "provenance": provenance,
        "recorded_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "review_note": "",
    })
    dump_json(ledger, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--shot", required=True)
    ap.add_argument("--confirm", action="store_true",
                    help="on-the-spot user approval for the paid request")
    args = ap.parse_args()
    submit(os.path.abspath(args.root), args.shot, args.confirm)


if __name__ == "__main__":
    main()
