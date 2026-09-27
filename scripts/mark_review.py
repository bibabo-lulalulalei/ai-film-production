# -*- coding: utf-8 -*-
"""mark_review.py — the ONLY legal writer of BOM production status.

State machine for one member row (06-bom/bom.json items[]):

  pending ──produce_asset ok──▶ produced ──user approves──▶ approved
                                   └──user rejects──▶ reject

Rules enforced (no silent edits, audit trail):
  * target_path must identify exactly one BOM item;
  * produced  requires the artifact file to exist;
  * approved/rejected require --decision-by <user> (the user holds the
    approval right; a script never self-approves) and are timestamped;
  * notes are appended to review_note; nothing else in the BOM is touched.

Usage:
  python scripts/mark_review.py <root> --path <target_path>
        --status produced|approved|rejected [--note ...] [--by <user>]
"""
import argparse
import datetime
import os
import sys

from _common import BOM_PATH, die, dump_json, exists, load_json

LEGAL = {"pending", "produced", "approved", "rejected"}


def find_item(bom, target_path):
    matches = [i for i in bom.get("items", [])
               if i.get("target_path") == target_path]
    return matches


def mark(root, target_path, status, note, by):
    bom_file = os.path.join(root, BOM_PATH)
    if not os.path.exists(bom_file):
        die(f"缺 {BOM_PATH}；先跑 [8] build_bom")
    bom = load_json(bom_file)
    matches = find_item(bom, target_path)
    if not matches:
        die(f"BOM 中无 target_path={target_path}")
    if len(matches) > 1:
        die(f"target_path 不唯一（{len(matches)} 行）：{target_path}")
    item = matches[0]

    if status not in LEGAL:
        die(f"status 非法 {status}（允许 {sorted(LEGAL)}）")

    # Forward preconditions.
    if status == "produced" and not exists(root, target_path):
        die(f"不能标 produced：成品文件不存在 {target_path}")
    if status in ("approved", "rejected") and not by:
        die(f"标 {status} 须用 --by <审批人>；审批权属于用户，脚本不自批")

    today = datetime.date.today().isoformat()
    if status == "produced":
        item["produced_at"] = item.get("produced_at") or today
    if status in ("approved", "rejected"):
        item["status_reviewed_by"] = by
        item["status_reviewed_at"] = today
    if note:
        prior = item.get("review_note", "")
        stamp = f"[{today}" + (f" {by}" if by else "") + f"] {note}"
        item["review_note"] = (prior + " / " + stamp).strip(" /")

    item["status"] = status
    dump_json(bom, bom_file)
    print(f"ok: {target_path} -> {status}"
          + (f" (by {by})" if by else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--path", required=True, help="member target_path")
    ap.add_argument("--status", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--by", default="", help="审批人（approved/rejected 必填）")
    args = ap.parse_args()
    mark(os.path.abspath(args.root), args.path, args.status, args.note, args.by)


if __name__ == "__main__":
    main()
