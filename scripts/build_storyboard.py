# -*- coding: utf-8 -*-
"""Mechanically derive the single text-storyboard document from locked cards.

[12b] runs after card lock [12] and before prompt writing [13]. The document
is (a) the human cross-shot read — no node-hopping, and (b) the prompt
writer's rendering brief: hook / spatial anchor card / continuity /
double-binding / per-panel four-quadrant content / ASCII layout.

Usage: python scripts/build_storyboard.py <project-root>
Output: 05-shots/storyboard.md
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import DIR_SHOTS, die, load_cards, write_text

ELASTIC_WORDS = ("squash", "stretch", "anticipation", "overshoot",
                 "follow-through", "挤压", "拉伸", "预备", "过冲", "随动")
OUT_PATH = os.path.join(DIR_SHOTS, "storyboard.md")


def main(root):
    cards = load_cards(root)
    locked = [c for c in cards if c.get("status") == "locked"]
    skipped = [c.get("shot_id") for c in cards if c.get("status") != "locked"]
    if skipped:
        print(f"WARN: 跳过未锁定卡: {', '.join(skipped)}")
    if not locked:
        die("无 locked 镜头卡；先过 [12] 锁镜")

    total = sum(float(c.get("duration_s", 0)) for c in locked)
    project = os.path.basename(root.rstrip("/\\"))
    lines = [
        f"# {project} · 文本分镜 Text Storyboards", "",
        f"- 镜数 {len(locked)} ｜ 总时长约 {total:g}s ｜ "
        f"生成于 {datetime.datetime.now().isoformat(timespec='seconds')}",
        "- 本文档由锁定镜头卡机械派生，只转译不改写；"
        "镜头卡是唯一事实源，改稿改卡后重新生成本文档。", "",
        "## 目录", "",
        "| 镜 | 时长 | 档位 | Hook | 叙事任务 |", "|---|---|---|---|---|",
    ]
    for c in locked:
        sid = c.get("shot_id", "?")
        job = str(c.get("narrative_job", "")).replace("|", "\\|")
        lines.append(f"| [{sid}](#{sid.lower()}) | "
                     f"{c.get('duration_s'):g}s | "
                     f"{c.get('duration_tier', '?')} | "
                     f"{c.get('hook', {}).get('hook_type', '?')} | {job} |")
    lines.append("")

    for prev, c in zip([None] + locked[:-1], locked):
        lines += render_section(c, prev)

    out = os.path.join(root, OUT_PATH)
    write_text(out, "\n".join(lines) + "\n")
    print(f"storyboard ok: {len(locked)} shot(s), {total:g}s -> {OUT_PATH}")


def render_section(c, prev):
    sid = c.get("shot_id", "?")
    dur = float(c.get("duration_s"))
    sa = c.get("spatial_anchors") or {}
    tl = c.get("timeline") or []

    landmarks = sa.get("fixed_landmarks") or []
    positions = sa.get("cast_positions") or []
    exited = sa.get("exited_characters") or []
    lighting = sa.get("lighting_baseline") or {}
    chars = [x.get("character_id") for x in c.get("cast") or []]
    scene_need = next((n for n in c.get("needs") or []
                       if n.get("kind") == "scene"), None)
    props = [n.get("asset_id") for n in c.get("needs") or []
             if n.get("kind") == "prop"]
    hook = c.get("hook") or {}

    lines = [f"## {sid} / {dur:g}s / {c.get('duration_tier', '?')} — "
             f"{c.get('narrative_job', '')}", ""]
    hline = f"- **Hook type**: {hook.get('hook_type', '?')}"
    if hook.get("note"):
        hline += f" — {hook['note']}"
    lines.append(hline)
    if c.get("beat"):
        lines.append(f"- **剧拍拍次**: {c['beat']}")
    lines.append(f"- **Scene & characters**: scene:{c.get('scene_id', '?')} "
                 f"| char:{', '.join(filter(None, chars)) or '—'}")
    if scene_need and scene_need.get("grid_id"):
        lines.append(f"- **Scene cell**: {scene_need.get('grid_id')}/"
                     f"{scene_need.get('cell', '?')}")

    # ---- spatial anchor card ----
    lines += [
        "- **Spatial anchor card**:",
        "  - Fixed landmarks: "
        + _join_or(landmarks, lambda x: f"{x.get('name')} ({x.get('screen_position')})"),
        "  - Character positions: "
        + _join_or(positions, lambda x: (
            f"{x.get('character_id')} ({x.get('screen_position')}, "
            f"facing {x.get('facing')}, {x.get('initial_pose')})")),
        "  - Exited character status: "
        + _join_or(exited, lambda x: (
            f"{x.get('character_id')} → {x.get('offscreen')} ({x.get('reason')})")),
        "  - Lighting baseline: "
        f"key={lighting.get('key', '?')} ｜ fill={lighting.get('fill', '?')} "
        f"｜ rim={lighting.get('rim', '?')} ｜ modifier={lighting.get('modifier', '?')}",
    ]

    # ---- continuity ----
    prev_tl = (prev or {}).get("timeline") or []
    from_handoff = prev_tl[-1].get("handoff") if prev_tl else None
    lines.append(f"- **Continuity from {(prev or {}).get('shot_id', '—')}**: "
                 f"{from_handoff or '全片首镜' if not prev else '（前镜未写 handoff）'}")
    to_handoff = tl[-1].get("handoff") if tl else None
    lines.append(f"- **Continuity to next**: {to_handoff or '（末镜未写 handoff）'}")

    # ---- double-binding ----
    if scene_need and scene_need.get("grid_id"):
        scene_tag = (f"[scene:{c.get('scene_id', '?')}#"
                     f"{scene_need.get('grid_id')}/{scene_need.get('cell', '?')}]")
    else:
        scene_tag = f"[scene:{c.get('scene_id', '?')}]"
    tags = [f"[char:{x}]" for x in chars] \
        + [f"[prop:{x}]" for x in props] \
        + [scene_tag, f"[hook:{hook.get('hook_type', '?')}]"]
    lines += ["- **Double-binding**: " + " ".join(tags), "",
              "### Per-panel four-quadrant content", ""]

    # ---- four-quadrant panels; collect the cam/audio index lines in the same
    # pass so the timeline is walked only once ----
    index_lines = []
    for i, item in enumerate(tl):
        t0 = float(item.get("t", 0))
        t1 = float(tl[i + 1]["t"]) if i + 1 < len(tl) else dur
        span = span_label(t0, t1)

        lines.append(f"#### {span}")
        if t1 <= t0:
            lines.append("- 落幅点（final pose）")
        lines += [
            f"- Picture: {item.get('picture', '')}",
            f"- Pose + Action: {item.get('action', '')}",
            f"- Camera: {item.get('camera', '')}",
            f"- Audio: {item.get('sound', '')}",
        ]
        if item.get("dialogue_ref"):
            lines.append(f"- Dialogue ref: {item['dialogue_ref']}")
        marks = []
        if any(w in str(item.get("action", "")).lower() for w in ELASTIC_WORDS):
            marks.append("[BEAT]")
        if item.get("handoff"):
            marks.append(f"[HANDOFF] {item['handoff']}")
        if marks:
            lines.append("- " + " ".join(marks))
        lines.append("")

        sound = str(item.get("sound", ""))
        if len(sound) > 60:
            sound = sound[:57] + "..."
        index = f"- `{span}` cam: {item.get('camera', '')} ｜ audio: {sound}"
        if item.get("handoff"):
            index += f" ｜ handoff: {item['handoff']}"
        index_lines.append(index)

    # ---- ASCII layout + collected index ----
    lines += ["### ASCII 空间布局", "", "```"]
    for x in positions:
        lines.append(f"  {x.get('character_id')} @ {x.get('screen_position')} "
                     f"(facing {x.get('facing')}, {x.get('initial_pose')})")
    for x in landmarks:
        lines.append(f"  {x.get('name')} @ {x.get('screen_position')}")
    for x in exited:
        lines.append(f"  [offscreen] {x.get('character_id')} → "
                     f"{x.get('offscreen')} ({x.get('reason')})")
    lines.append(f"  lighting: key={lighting.get('key', '?')} | "
                 f"fill={lighting.get('fill', '?')} | rim={lighting.get('rim', '?')} | "
                 f"modifier={lighting.get('modifier', '?')}")
    lines += ["```"] + index_lines + [""]
    return lines


def _join_or(items, fmt):
    return "；".join(fmt(x) for x in items) or "—"


def span_label(t0, t1):
    if t1 <= t0:
        return f"落幅 @{t0:g}s"
    return f"{t0:g}–{t1:g}s"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        die("usage: python scripts/build_storyboard.py <project-root>")
    main(os.path.abspath(sys.argv[1]))
