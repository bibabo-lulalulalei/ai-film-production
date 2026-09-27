# -*- coding: utf-8 -*-
"""Asset readiness coverage for the readiness gate.

Usage: python validation/coverage.py <project-root>

Exit 0 only when every BOM item is status=approved AND its file exists, and no
item is approved while a depends_on prerequisite is not approved.
"""
import os
import sys

# validation/ sits next to scripts/, where the shared _common module lives
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))
from _common import BOM_PATH, die, exists, load_json


def main(root):
    path = os.path.join(root, BOM_PATH)
    if not os.path.exists(path):
        die(f"BOM not found ({BOM_PATH}); run build_bom.py first")
    bom = load_json(path)
    if bom.get("conflicts"):
        die("BOM has unresolved conflicts; fix the shot cards and rebuild")

    items = bom.get("items", [])
    # depends_on entries are target_paths, so approval is keyed by path.
    status = {i["target_path"]: i["status"]
              for i in items if i.get("target_path")}
    total = len(items)
    missing = []
    dep_violations = []

    for it in items:
        ready = it["status"] == "approved" and exists(root, it["target_path"])
        flag = "ok " if ready else "MISS"
        print(f"  [{flag}] {it['asset_id']:<22} {it['kind']:<11} "
              f"status={it['status']:<9} {it['target_path']}")
        if not ready:
            reason = it["status"] if it["status"] != "approved" else "file absent"
            missing.append(f"{it['asset_id']} ({reason})")
        for dep in it.get("depends_on", []):
            if status.get(dep) != "approved":
                dep_violations.append(
                    f"{it['asset_id']} 依赖 {dep} 未 approved（投产顺序违规）")

    pct = (total - len(missing)) / total * 100 if total else 0.0
    print(f"\ncoverage: {total - len(missing)}/{total} = {pct:.1f}%")
    for v in dep_violations:
        print(f"  DEP {v}")
    if missing:
        print("not ready:")
        for m in missing:
            print(f"  - {m}")
    if missing or dep_violations:
        sys.exit(1)
    print("READINESS 100% — safe to lock shots.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        die("usage: python validation/coverage.py <project-root>")
    main(os.path.abspath(sys.argv[1]))
