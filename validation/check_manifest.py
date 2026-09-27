# -*- coding: utf-8 -*-
"""Gate OM: validate the Outputs Value Manifest (skill self-description).

Zero-cost structural gate. It enforces the "make everything earn its keep"
contract:

  * every registered output is structurally valid and carries a value tier;
  * V3 (high-value) outputs MUST have a real mechanical consumer;
  * decision "delete" is allowed only with a rationale (no silent deletion);
  * decision "extend-downstream" must name at least one consumer;
  * "archive"/"delete" entries may have no consumers but must say why.

The manifest is skill-level data, so this gate takes no project root and no
shot cards. Exit 0 = the manifest is consistent.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))
from _common import die, load_json, skill_root, validate_like  # noqa: E402

MANIFEST_DATA = "outputs-manifest.data.json"
MANIFEST_SCHEMA = os.path.join("schemas", "outputs-manifest.json")

DECISIONS = {"extend-downstream", "review-checklist", "merge-ref",
             "conditional", "archive", "keep", "delete"}
TIERS = {"V3", "V2", "V1"}


def check_manifest():
    root = skill_root()
    data_path = os.path.join(root, MANIFEST_DATA)
    if not os.path.exists(data_path):
        return [f"缺少产出物总账 {MANIFEST_DATA}"]
    schema = load_json(os.path.join(root, MANIFEST_SCHEMA))
    data = load_json(data_path)

    out = validate_like(data, schema)
    outputs = data.get("outputs") or []
    if not outputs:
        out.append("outputs-manifest 未登记任何产出物")

    seen = set()
    for i, item in enumerate(outputs):
        name = item.get("output") or f"#{i}"
        if name in seen:
            out.append(f"产出物重复登记: {name}")
        seen.add(name)

        tier = item.get("value_tier")
        decision = item.get("decision")
        consumers = item.get("consumed_by") or []
        rationale = item.get("rationale")

        if tier not in TIERS:
            out.append(f"{name}: value_tier 非法 {tier}")
        if decision not in DECISIONS:
            out.append(f"{name}: decision 非法 {decision}")

        # High-value outputs cannot be left without a mechanical consumer.
        if tier == "V3" and not consumers:
            out.append(
                f"{name}: V3 高价值产出物必须有机械消费者（改下游补用），"
                "不能归档/删除")

        if decision in ("extend-downstream", "merge-ref", "keep",
                        "review-checklist", "conditional") and not consumers:
            out.append(f"{name}: decision={decision} 须至少登记一个消费者")

        # Deletion/archival is permitted only with a stated reason.
        if decision in ("delete", "archive") and not rationale:
            out.append(f"{name}: decision={decision} 必须填写 rationale")

        if decision == "delete" and tier == "V3":
            out.append(f"{name}: V3 高价值产出物不得删除")
    return out


def main():
    problems = check_manifest()
    print("== OUTPUTS VALUE MANIFEST (gate OM) ==")
    if problems:
        for m in problems:
            print(f"  FAIL {m}")
        print(f"\n{len(problems)} problem(s) — gate OM FAILED")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
