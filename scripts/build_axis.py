# -*- coding: utf-8 -*-
"""build_axis.py — deterministic orientation calculator (the "方位脚本").

For every registered camera facing in an axis_table, compute the
screen-left/right mapping from the world compass convention, so the
production never derives left/right by hand ("禁心算"). It also verifies
each camera_facing id exists and resolves to a real space in geography.

Usage:
  python scripts/build_axis.py <project-root> [--scene <world_id>] ...

Without --scene it processes every 04-world/<world>/axis_table.json.
The result is written next to the axis table as axis_resolved.json
(derived artifact; safe to regenerate). Exit 0 = all facings resolved.
"""
import argparse
import os
import sys

from _common import (DIR_WORLD, die, dump_json, load_json, validate_like)

# 8-direction order clockwise from North.
DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# For a camera looking in direction `face`, world direction that lands on
# screen-left is 90° counter-clockwise; screen-right is 90° clockwise.
HALF = 2  # 90° = two 45° steps


def _index(face):
    try:
        return DIRS.index(face)
    except ValueError:
        return None


def screen_left(face):
    i = _index(face)
    return None if i is None else DIRS[(i - HALF) % len(DIRS)]


def screen_right(face):
    i = _index(face)
    return None if i is None else DIRS[(i + HALF) % len(DIRS)]


def resolve_world(world_dir):
    """Resolve one 04-world/<world> directory. Returns (entries, errors)."""
    geo_path = os.path.join(world_dir, "geography.json")
    axis_path = os.path.join(world_dir, "axis_table.json")
    errors, entries = [], []

    if not os.path.exists(geo_path):
        errors.append(f"缺 geography.json（{world_dir}）")
        return entries, errors
    if not os.path.exists(axis_path):
        errors.append(f"缺 axis_table.json（{world_dir}）")
        return entries, errors

    geo = load_json(geo_path)
    axis = load_json(axis_path)
    errors += [f"geography: {m}" for m in validate_like(
        geo, _schema("geography.schema.json"))]
    errors += [f"axis_table: {m}" for m in validate_like(
        axis, _schema("axis-table.schema.json"))]

    spaces = {s.get("id") for s in geo.get("spaces", [])}
    for cam in axis.get("camera_facings", []):
        cid, space, face = cam.get("id"), cam.get("space"), cam.get("faces")
        if space not in spaces:
            errors.append(f"机位 {cid}: space {space} 不在 geography.spaces")
        left, right = screen_left(face), screen_right(face)
        if left is None:
            errors.append(f"机位 {cid}: faces 非法 {face}")
            continue
        entries.append({
            "camera_id": cid,
            "space": space,
            "faces": face,
            "screen_left_world": left,
            "screen_right_world": right,
            "note": f"面向 {face}：screen-left 朝 {left}，screen-right 朝 {right}",
        })
    return entries, errors


def _schema(name):
    from _common import skill_root
    return load_json(os.path.join(skill_root(), "schemas", name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--scene", help="only one world_id")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    worlds_dir = os.path.join(root, DIR_WORLD)
    if not os.path.isdir(worlds_dir):
        die(f"无 {DIR_WORLD}/ 目录")

    if args.scene:
        world_names = [args.scene]
    else:
        world_names = sorted(
            d for d in os.listdir(worlds_dir)
            if os.path.isdir(os.path.join(worlds_dir, d)))

    all_errors = []
    for name in world_names:
        wdir = os.path.join(worlds_dir, name)
        entries, errors = resolve_world(wdir)
        all_errors += [f"[{name}] {e}" for e in errors]
        if entries:
            resolved = {
                "world_id": name,
                "derived": True,
                "note": "由 build_axis.py 从 axis_table + geography 机械生成",
                "cameras": entries,
            }
            dump_json(resolved, os.path.join(wdir, "axis_resolved.json"))
            print(f"[{name}] resolved {len(entries)} camera facing(s)")

    if all_errors:
        for e in all_errors:
            print(f"  FAIL {e}")
        print(f"\n{len(all_errors)} problem(s) — build_axis FAILED")
        sys.exit(1)
    print("PASS — all axis facings resolved")


if __name__ == "__main__":
    main()
