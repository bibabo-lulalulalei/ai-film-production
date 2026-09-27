# -*- coding: utf-8 -*-
"""Mechanically derive the BOM from shot cards + asset design cards.

Usage: python scripts/build_bom.py <project-root>

Shot-card needs are minimal (asset_id / kind / target_path; scene needs add
grid_id + cell, character needs may add sheet). Appearance detail lives in
06-bom/asset-specs/<ASSET>.json.

- Every produced image is a *member*: a character sheet, a prop grid, or a
  scene grid; one BOM line per member, keyed by its unique target_path.
- The same asset_id may have several members (character state sheets, scene
  grids); scene needs also verify the bound cell exists in the grid.
- lip_sync characters additionally get voice + tts lines.
- Missing/invalid spec -> error (run [7], pass G05). Previous reviewed
  status, review_note and depends_on are preserved across rebuilds by
  target_path.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (BOM_PATH, die, dump_json, load_cards, load_json,
                     spec_path)


def main(root):
    cards = load_cards(root)
    if not cards:
        die("no shot cards under 05-shots")

    # (asset_id, target_path) -> aggregated member info.
    members, order = {}, []
    # asset_id -> lip-sync info (voice/tts are asset-level, not member-level).
    lip = {}

    for card in cards:
        sid = card.get("shot_id", "?")
        if card.get("lip_sync"):
            audio = card.get("audio") or {}
            cid = audio.get("character_id")
            if cid:
                info = lip.setdefault(cid, {"tts_paths": set(), "used_in": []})
                if audio.get("tts_path"):
                    info["tts_paths"].add(audio["tts_path"])
                if sid not in info["used_in"]:
                    info["used_in"].append(sid)
        for n in card.get("needs") or []:
            aid, target = n.get("asset_id"), n.get("target_path")
            if not aid or not target:
                continue
            key = (aid, target)
            info = members.get(key)
            if info is None:
                info = {"kinds": set(), "grid_ids": set(), "cells": set(),
                        "sheets": set(), "used_in": []}
                members[key] = info
                order.append(key)
            info["kinds"].add(n.get("kind"))
            if n.get("grid_id"):
                info["grid_ids"].add(n["grid_id"])
            if n.get("cell"):
                info["cells"].add(n["cell"])
            if n.get("sheet"):
                info["sheets"].add(n["sheet"])
            if sid not in info["used_in"]:
                info["used_in"].append(sid)

    errors, items = [], []
    for aid, target in order:
        info = members[(aid, target)]
        kinds = info["kinds"]
        if len(kinds) != 1:
            errors.append(f"{aid}: 同 member 多种 kind {sorted(kinds)}")
            continue
        kind = next(iter(kinds))

        spec_file = os.path.join(root, spec_path(aid))
        if not os.path.exists(spec_file):
            errors.append(f"{aid}: 缺设计卡 {os.path.relpath(spec_file, root)}")
            continue
        spec = load_json(spec_file)
        if spec.get("kind") != kind:
            errors.append(f"{aid}: 设计卡 kind 不匹配（{spec.get('kind')}≠{kind}）")
            continue

        spec_ref = os.path.relpath(spec_file, root).replace("\\", "/")
        line = member_line(aid, kind, target, info, spec, spec_ref)
        if line is None:
            errors.append(f"{aid}: member 与设计卡不对齐（{target}）")
        else:
            items.append(line)

    for aid, info in lip.items():
        items.append(derived_line(
            f"{aid}-voice", "voice", f"07-assets/voices/{aid}_voice.wav",
            f"原始嗓音，仅供克隆（{aid}）", info["used_in"]))
        items.append(derived_line(
            f"{aid}-tts", "tts",
            (next(iter(info["tts_paths"])) if len(info["tts_paths"]) == 1
             else f"07-assets/tts/{aid}_tts.wav"),
            f"声音参考；台词写在提示词里，AutoDL 不卡 wav 时长"
            f"（官方平台口径 2–15s）；{aid} 开口镜共用",
            info["used_in"]))

    # target_path must be unique across the whole BOM.
    seen = {}
    for line in items:
        other = seen.get(line["target_path"])
        if other:
            errors.append(f"target_path 冲突：{line['target_path']} "
                          f"被 {other} 与 {line['asset_id']} 共用")
        else:
            seen[line["target_path"]] = line["asset_id"]

    preserve_review_state(root, items)

    bom = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "source_cards": [c.get("shot_id") for c in cards],
           "conflicts": [{"asset_id": "-", "reason": e} for e in errors],
           "items": items}
    bom_file = os.path.join(root, BOM_PATH)
    dump_json(bom, bom_file)

    if errors:
        print(f"BOM written with {len(errors)} error(s) -> {BOM_PATH}")
        for e in errors:
            print("  " + e)
        sys.exit(1)

    print(f"BOM ok: {len(items)} line(s), {len(cards)} card(s) -> {BOM_PATH}")
    for line in items:
        dep = f" dep={line['depends_on']}" if line.get("depends_on") else ""
        print(f"  {line['asset_id']:<22} {line['kind']:<11} "
              f"status={line['status']}{dep}")


def _line(asset_id, kind, target, used_in, spec_ref, status="pending", **extra):
    line = {"asset_id": asset_id, "kind": kind,
            "target_path": target, "used_in": used_in,
            "status": status, "derived": False, "spec_path": spec_ref}
    line.update(extra)
    return line


def derived_line(asset_id, kind, target, spec, used_in):
    return _line(asset_id, kind, target, used_in, "—", visual_spec=spec,
                 derived=True)


def member_line(aid, kind, target, info, spec, spec_ref):
    """Build one member line, or None when the need does not match the spec."""
    name = (spec.get("identity") or {}).get("name", aid)
    if kind == "character":
        sheet_ids = info["sheets"]
        if len(sheet_ids) > 1:
            return None
        sheet_id = next(iter(sheet_ids)) if sheet_ids else "main"
        sheet = next((s for s in spec.get("sheets") or []
                      if s.get("sheet_id") == sheet_id), None)
        if sheet is None or sheet.get("target_path") != target:
            return None
        extra = {"sheet_id": sheet_id,
                 "visual_spec": f"见设计卡（{name}·定妆 sheet {sheet_id}）"}
        if sheet_id != "main":
            main_t = next((s.get("target_path") for s in spec.get("sheets") or []
                           if s.get("sheet_id") == "main"), None)
            if main_t:
                extra["depends_on"] = [main_t]
        return _line(aid, kind, target, info["used_in"], spec_ref, **extra)

    if kind == "scene":
        grid_ids = info["grid_ids"]
        if len(grid_ids) != 1:
            return None
        grid_id = next(iter(grid_ids))
        grid = next((g for g in spec.get("grids") or []
                     if g.get("grid_id") == grid_id), None)
        if grid is None or grid.get("target_path") != target:
            return None
        valid_cells = {c.get("cell_id") for c in grid.get("cells") or []}
        if any(c not in valid_cells for c in info["cells"]):
            return None
        kind_word = "场景单图" if grid.get("layout") == "single" else "场景宫格"
        extra = {"grid_id": grid_id,
                 "visual_spec": f"见设计卡（{name}·{kind_word} {grid_id}）"}
        if grid.get("continuity_ref"):
            extra["depends_on"] = [grid["continuity_ref"]]
        return _line(aid, kind, target, info["used_in"], spec_ref, **extra)

    # prop
    grid = ((spec.get("presentation") or {}).get("grid") or {})
    if grid.get("target_path") != target:
        return None
    return _line(aid, kind, target, info["used_in"], spec_ref,
                 visual_spec=f"见设计卡（{name}·道具宫格）")


def preserve_review_state(root, items):
    """Carry prior human review fields onto rebuilt lines (keyed by path)."""
    bom_file = os.path.join(root, BOM_PATH)
    if not os.path.exists(bom_file):
        return
    prior = {i["target_path"]: i for i in load_json(bom_file).get("items", [])
             if i.get("target_path")}
    live_paths = {line["target_path"] for line in items}
    for line in items:
        old = prior.get(line["target_path"])
        if not old:
            continue
        line["status"] = old.get("status", line["status"])
        if old.get("review_note"):
            line["review_note"] = old["review_note"]
        # Builder-computed deps are the baseline; keep manual extras that still
        # point at existing member paths.
        deps = line.get("depends_on", [])
        for d in old.get("depends_on") or []:
            if d in live_paths and d not in deps:
                deps.append(d)
        if deps:
            line["depends_on"] = deps


if __name__ == "__main__":
    if len(sys.argv) != 2:
        die("usage: python scripts/build_bom.py <project-root>")
    main(os.path.abspath(sys.argv[1]))
