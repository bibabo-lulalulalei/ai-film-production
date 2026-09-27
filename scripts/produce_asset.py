# -*- coding: utf-8 -*-
"""produce_asset.py — BOM-driven asset production runner ([10]).

Replaces hand-written one-off batch scripts. For every selectable BOM item
it assembles one production job and (optionally) submits it to the image
backend, then records state via the same rules as mark_review:

  job = production prompt (06-bom/asset-prompts/<id>.md)
        + Style Key reference(s) that really go into the request
        + the member target_path (no hand-typed destinations)

Contract checks (always, zero-cost; this is the default "dry run"):
  * BOM item status is pending (never regenerate an approved member);
  * the production prompt file exists and is non-empty;
  * a Style Key is available when the pipeline requires one (profile
    pipeline_requirements.style_key_required) — references are attached,
    not merely mentioned;
  * the layout is one the image backend can produce (asset_image
    sheet_capabilities); target directory is writable.

Real submission needs --submit and a backend adapter under
scripts/image_backends/<backend>.py (keyed by profile asset_image.backend).
Adapters do the HTTP call; this runner never hardcodes an endpoint.

Usage:
  python scripts/produce_asset.py <root> [--id ASSET_ID] [--all]
        [--submit]
"""
import argparse
import os
import sys

import glob as _glob

from _common import (BOM_PATH, KEYS_DIR, die, dump_json, exists,
                     load_json, load_profile)

PROMPT_DIR = os.path.join("06-bom", "asset-prompts")
BACKENDS_DIR = os.path.join("scripts", "image_backends")


def glob_keys(root):
    return sorted(_glob.glob(os.path.join(root, KEYS_DIR, "*.png")))


def candidate_items(bom, only_id, only_grid=None, only_sheet=None):
    items = []
    for it in bom.get("items", []):
        if it.get("kind") in ("voice", "tts", "sound"):
            continue
        if only_id and it.get("asset_id") != only_id:
            continue
        if only_grid and it.get("grid_id") != only_grid:
            continue
        if only_sheet and it.get("sheet_id") != only_sheet:
            continue
        items.append(it)
    return items


def prompt_file_for(root, asset_id):
    return os.path.join(root, PROMPT_DIR, f"{asset_id}.md")


def layout_of(item):
    """Grid/canvas layout implied by the member (for capability check)."""
    # Scene/prop members carry their grid layout implicitly via the BOM
    # member kind; character sheets are 1x4. Explicit mapping is read from
    # the production template wording, so we return a coarse tag only.
    if item.get("kind") == "character":
        return "1x4"
    name = (item.get("target_path") or "")
    # single-image members have no grid suffix in dir name; default single.
    return "single"


def base_member_for(bom, item):
    """The approved identity/base member this variant row depends on.

    Character state variants (sheet_id != main) depend on the same asset's
    approved main sheet; scene state packs (grid_id g2…) depend on the
    approved g1 pack. Returns the base BOM row, or None if this is a base row.
    """
    if item.get("kind") == "character" and item.get("sheet_id") not in (None, "main"):
        want = {"asset_id": item.get("asset_id"), "sheet_id": "main"}
    elif item.get("kind") == "scene" and item.get("grid_id") not in (None, "g1"):
        want = {"asset_id": item.get("asset_id"), "grid_id": "g1"}
    else:
        return None
    for it in bom.get("items", []):
        if all(it.get(k) == v for k, v in want.items()):
            return it
    return False  # dependency row does not exist in BOM


def check_job(root, item, profile, bom=None):
    """Zero-cost contract checks for one production job."""
    errors = []
    aid = item.get("asset_id")
    status = item.get("status")

    if status != "pending":
        errors.append(f"status={status}，只投产 pending（approved 件不重烧；重走开 ECN）")

    # Variant rows need an approved, on-disk base member (identity anchor).
    if bom is not None:
        base = base_member_for(bom, item)
        if base is False:
            errors.append("变体行的基础 member（main sheet / g1 包）不在 BOM 中；先核设计卡")
        elif base is not None:
            if base.get("status") != "approved":
                errors.append(f"基础件 {base.get('target_path')} 状态 {base.get('status')}；"
                              "变体须在 base approved 后投产")
            elif not exists(root, base.get("target_path", "")):
                errors.append(f"基础件已 approved 但文件缺失：{base.get('target_path')}")

    pf = prompt_file_for(root, aid)
    if not exists(root, os.path.relpath(pf, root)):
        errors.append(f"缺生产提示词 {os.path.relpath(pf, root)}；先跑 [9b]")
    elif os.path.getsize(pf) == 0:
        errors.append("生产提示词为空")

    ai = profile.get("asset_image", {})
    layouts = (ai.get("sheet_capabilities") or {}).get("layouts") or []
    layout = layout_of(item)
    if layouts and layout not in layouts:
        errors.append(f"后端 {ai.get('backend')} 不支持版式 {layout}（支持 {layouts}）")

    # Style Key really attached when required.
    reqs = profile.get("pipeline_requirements", {})
    if reqs.get("style_key_required"):
        keys = glob_keys(root)
        if not keys:
            errors.append("无 Style Key（03-style/keys/*.png）；必垫样板图，不能裸生成")

    # Destination directory must be writable (we never hand-type a dest).
    dest = os.path.join(root, item.get("target_path", ""))
    dest_dir = os.path.dirname(dest)
    if dest_dir:
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError as e:
            errors.append(f"落点不可写 {item.get('target_path')}: {e}")
    return errors


def load_backend_adapter(profile):
    """Import scripts/image_backends/<backend>.py for real submission."""
    backend_name = (profile.get("asset_image") or {}).get("backend", "")
    if not backend_name:
        die("profile.asset_image.backend 未登记，无法提交")
    slug = backend_name.lower().replace(".", "").replace(" ", "_")
    path = os.path.join(BACKENDS_DIR, f"{slug}.py")
    if not os.path.exists(path):
        die(f"无后端适配器 {path}；真实提交需先按 profile 实现该适配器")
    import importlib.util
    spec = importlib.util.spec_from_file_location(slug, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def submit_job(root, item, profile, bom=None):
    adapter = load_backend_adapter(profile)
    pf = prompt_file_for(root, item.get("asset_id"))
    with open(pf, "r", encoding="utf-8") as f:
        prompt_text = f.read()
    # The approved base member (if any) is the strongest identity anchor:
    # prepend it, then Style Keys.
    refs = []
    if bom is not None:
        base = base_member_for(bom, item)
        if isinstance(base, dict):
            refs.append(os.path.join(root, base.get("target_path", "")))
    refs += glob_keys(root)
    result = adapter.generate(prompt_text=prompt_text,
                             reference_paths=refs,
                             target_path=item.get("target_path"),
                             asset_image=profile.get("asset_image", {}),
                             root=root)
    out = os.path.join(root, item["target_path"])
    mode = "wb" if isinstance(result, bytes) else "w"
    with open(out, mode) as f:
        f.write(result)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--id", help="one asset_id")
    ap.add_argument("--grid", help="只投产某一 grid_id（同一 asset 多行时）")
    ap.add_argument("--sheet", help="只投产某一 sheet_id（同一 asset 多行时）")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--submit", action="store_true",
                    help="really call the image backend (default: dry-run)")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    bom_file = os.path.join(root, BOM_PATH)
    if not os.path.exists(bom_file):
        die(f"缺 {BOM_PATH}；先跑 [8] build_bom")
    bom = load_json(bom_file)
    if not args.id and not args.all:
        die("指定 --id <asset_id> 或 --all")
    profile = load_profile(root)

    items = candidate_items(bom, args.id, args.grid, args.sheet)
    if not items:
        die("没有匹配的可投产 BOM 项")

    all_errors, produced = [], []
    for item in items:
        aid = item.get("asset_id")
        errors = check_job(root, item, profile, bom)
        if errors:
            all_errors += [f"{aid}: {e}" for e in errors]
            continue
        if args.submit:
            path = submit_job(root, item, profile, bom)
            item["status"] = "produced"
            import datetime
            item["produced_at"] = datetime.date.today().isoformat()
            produced.append(aid)
            print(f"produced {aid} -> {item['target_path']}")
        else:
            print(f"ready (dry-run) {aid} -> {item['target_path']}")

    if args.submit and produced:
        dump_json(bom, bom_file)  # persist produced state
    if all_errors:
        for e in all_errors:
            print(f"  FAIL {e}")
        print(f"\n{len(all_errors)} problem(s) — produce_asset FAILED")
        sys.exit(1)
    print("PASS — " + ("assets produced" if args.submit else "dry-run only"))


if __name__ == "__main__":
    main()
