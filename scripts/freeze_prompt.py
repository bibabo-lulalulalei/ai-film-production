# -*- coding: utf-8 -*-
"""freeze_prompt.py — freeze the reviewed prompt into a hash manifest.

Runs right after G07 and before [14] submission. It records a sha256 for
every file the submission depends on:

  08-prompts/<SHOT>.prompt.md
  08-prompts/<SHOT>.gen.json
  every reference file gen.json declares (ref_images/ref_videos/ref_audios)

submit_take refuses to fire when a current hash differs from the frozen
one, so "edit the prompt after the gate" is impossible, and a freeze can
only be replaced by re-running G07 + this command.

Usage:
  python scripts/freeze_prompt.py <root> --shot <SHOT>
Output: 08-prompts/<SHOT>.freeze.json
"""
import argparse
import datetime
import hashlib
import os
import sys

from _common import die, dump_json, exists, load_json

PROMPTS_DIR = os.path.join("08-prompts")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def reference_files(gen):
    paths = []
    for key in ("ref_images", "ref_videos", "ref_audios"):
        for item in gen.get(key) or []:
            p = item.get("path")
            if p:
                paths.append(p.replace("\\", "/"))
    return sorted(set(paths))


def freeze(root, shot):
    prompt_rel = os.path.join(PROMPTS_DIR, f"{shot}.prompt.md")
    gen_rel = os.path.join(PROMPTS_DIR, f"{shot}.gen.json")
    prompt_path = os.path.join(root, prompt_rel)
    gen_path = os.path.join(root, gen_rel)
    if not os.path.exists(prompt_path):
        die(f"缺 {prompt_rel}；先完成 [13]")
    if not os.path.exists(gen_path):
        die(f"缺 {gen_rel}；先完成 [13]")

    gen = load_json(gen_path)
    files = {}
    missing = []
    for rel in [prompt_rel.replace("\\", "/"), gen_rel.replace("\\", "/")] \
            + reference_files(gen):
        if not exists(root, rel):
            missing.append(rel)
            continue
        files[rel] = sha256_file(os.path.join(root, rel))
    if missing:
        die("冻结引用了缺失文件: " + ", ".join(missing))

    manifest = {
        "shot_id": shot,
        "frozen_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "model": gen.get("model"),
        "mode": gen.get("mode"),
        "files": files,
    }
    out = os.path.join(root, PROMPTS_DIR, f"{shot}.freeze.json")
    dump_json(manifest, out)
    print(f"frozen {shot}: {len(files)} file(s) hashed -> "
          f"{os.path.relpath(out, root)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--shot", required=True)
    args = ap.parse_args()
    freeze(os.path.abspath(args.root), args.shot)


if __name__ == "__main__":
    main()
