# -*- coding: utf-8 -*-
"""Gate linter for shot cards.

Usage:
  python validation/lint_cards.py <project-root> --gate SD     # style direction
  python validation/lint_cards.py <project-root> --gate S      # shot self-check
  python validation/lint_cards.py <project-root> --gate A      # design freeze
  python validation/lint_cards.py <project-root> --gate lock   # lock
  python validation/lint_cards.py <project-root> --gate B      # prompt freeze

Prompt prose is never judged: wording, vocabulary and sentence counts stay
human review by design, because prose heuristics produce false FAILs. But the
linter DOES extract closed structural tokens from the prompt text — section
headers (`field:` lines), template tags (`<Picture N>` and friends), and the
first-line anchors (tags + second-precision seconds) — and compares them
deterministically against the target model profile. Everything else is over
structured JSON: field presence, enums, ID/path references, file existence,
numeric ranges. Model-specific limits come from the target model profile.
Exit 0 = pass.
"""
import argparse
import os
import re
import sys

# validation/ sits next to scripts/, where the shared _common module lives
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))
from _common import (BOM_PATH, DASH_PLACEHOLDERS, DURATION_TIERS, GRID_POSITIONS,
                     RETENTION, SOUL_CHECKS, STYLE_CHECKS, STYLE_DIRECTION,
                     card_map, die,
                     dump_json, exists, flatten, is_unset, load_all_profiles,
                     load_cards, load_json, load_profile, skill_root, spec_path,
                     target_model)

IMAGE_KINDS = ("character", "prop", "scene")
NEED_KINDS = IMAGE_KINDS + ("sound",)
# Artifact -> its JSON Schema. Schemas are the single source of truth for
# "which fields exist, which are required, closed vocabularies and formats";
# the linter reads them at runtime instead of hand-copying field lists.
SCHEMA_FOR = {
    "shot": "shot-card.schema.json",
    "gen": "gen-params.schema.json",
    "character": "character-spec.schema.json",
    "prop": "prop-spec.schema.json",
    "scene": "scene-spec.schema.json",
    "style-matrix": "style-matrix.schema.json",
    "style-spec": "style-spec.schema.json",
    "geography": "geography.schema.json",
    "axis-table": "axis-table.schema.json",
    "brightness": "brightness.schema.json",
    "soul-checks": "soul-checks.schema.json",
    "style-checks": "style-checks.schema.json",
}


def load_schema(name):
    return load_json(os.path.join(skill_root(), "schemas", SCHEMA_FOR[name]))


def validate_against_schema(instance, schema, path="$"):
    """Validate one instance against one schema, using only the keywords our
    schemas use: required / properties / items / enum / pattern / numeric
    bounds / minItems / maxItems. Returns human-readable messages.

    Not a full JSON Schema engine. Cross-card and file-existence rules live
    in the dedicated checks further down, not here.
    """
    out = []
    if instance is None:
        # null is valid only when this schema explicitly accepts it
        null_types = schema.get("type")
        null_types = null_types if isinstance(null_types, list) else [null_types]
        if "null" not in null_types:
            out.append(f"{path} 不应为 null")
        return out

    if "enum" in schema and instance not in schema["enum"]:
        out.append(f"{path} 取值非法: {instance!r}（允许 {schema['enum']}）")
    if isinstance(instance, str) and "pattern" in schema \
            and re.search(schema["pattern"], instance) is None:
        out.append(f"{path} 不符合格式 {schema['pattern']}: {instance!r}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            out.append(f"{path}={instance} 小于 minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            out.append(f"{path}={instance} 大于 maximum {schema['maximum']}")
        em = schema.get("exclusiveMinimum")
        if em is not None and instance <= em:
            out.append(f"{path}={instance} 须 > {em}")
        emax = schema.get("exclusiveMaximum")
        if emax is not None and instance >= emax:
            out.append(f"{path}={instance} 须 < {emax}")

    types = schema.get("type")
    types = types if isinstance(types, list) else [types]

    if "object" in types and isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                out.append(f"{path}.{key} 缺失/UNSET")
            elif instance[key] is not None and is_unset(instance[key]):
                # empty / "UNSET" placeholder; a real JSON null is allowed by type
                out.append(f"{path}.{key} 未填/UNSET")
        for key, sub in (schema.get("properties") or {}).items():
            if key in instance:
                out += validate_against_schema(instance[key], sub, f"{path}.{key}")

    if "array" in types and isinstance(instance, list):
        if schema.get("minItems") is not None and len(instance) < schema["minItems"]:
            out.append(f"{path} 元素数 {len(instance)} < minItems {schema['minItems']}")
        if schema.get("maxItems") is not None and len(instance) > schema["maxItems"]:
            out.append(f"{path} 元素数 {len(instance)} > maxItems {schema['maxItems']}")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, value in enumerate(instance):
                out += validate_against_schema(value, items, f"{path}[{i}]")
    return out
STRONG_HOOKS = ("visual-joke", "reversal", "reveal", "suspense", "tender")
TWIST_HOOKS = ("reveal", "reversal", "callback")
# When a landmark/lighting change is described with these words in continuity,
# the cross-shot check accepts it as explicitly acknowledged.
CHANGE_WORDS = ("orbit", "move", "cut", "hard", "转", "移", "跳", "换")
TIMELINE_FIELDS = ("picture", "action", "camera", "sound", "handoff")


# ====================================================================== G04

def check_timeline(card):
    """Timeline: per-second coverage, five fields per entry, endpoints."""
    out = []
    tl = card.get("timeline") or []
    try:
        duration = float(card.get("duration_s"))
    except (TypeError, ValueError):
        return ["duration_s 非数值"]
    if not tl:
        return ["timeline 为空"]

    times = []
    last_t = None
    for i, e in enumerate(tl):
        for field in TIMELINE_FIELDS:
            if is_unset(e.get(field)):
                out.append(f"timeline[{i}] 缺 {field}（无声须显式写 silent）")
        try:
            t = float(e["t"])
        except (TypeError, ValueError):
            out.append(f"timeline[{i}] t 非数值")
            continue
        times.append(t)
        if t < 0:
            out.append(f"timeline[{i}] t 为负")
        if last_t is not None:
            if t <= last_t:
                out.append(f"timeline[{i}] 时间点非严格递增")
            elif t - last_t > 1.0 + 1e-6:
                out.append(f"timeline {last_t:g}s→{t:g}s 留有 >1s 空隙（须逐秒覆盖）")
        last_t = t

    if times:
        if abs(times[0]) > 1e-6:
            out.append(f"timeline 首项 t 须为 0（现={times[0]:g}）")
        if abs(times[-1] - duration) > 0.05:
            out.append(f"timeline 末项 t={times[-1]:g} ≠ duration_s={duration:g}"
                       f"（落幅须覆盖到整镜时长）")
    return out


def check_spatial(card):
    """Spatial-anchor card structural completeness."""
    out = []
    sa = card.get("spatial_anchors")
    if not isinstance(sa, dict):
        return ["缺 spatial_anchors"]

    for i, lm in enumerate(sa.get("fixed_landmarks") or []):
        if is_unset(lm.get("name")) or is_unset(lm.get("screen_position")):
            out.append(f"spatial_anchors.fixed_landmarks[{i}] 缺 name 或 screen_position")

    cast_ids = {m.get("character_id") for m in card.get("cast") or []}
    pos_ids = set()
    for i, cp in enumerate(sa.get("cast_positions") or []):
        for field in ("character_id", "screen_position", "facing", "initial_pose"):
            if is_unset(cp.get(field)):
                out.append(f"spatial_anchors.cast_positions[{i}] 缺 {field}")
        pos_ids.add(cp.get("character_id"))
    if cast_ids - pos_ids:
        out.append(f"spatial_anchors.cast_positions 未覆盖在镜角色: {sorted(cast_ids - pos_ids)}")
    if pos_ids - cast_ids:
        out.append(f"spatial_anchors.cast_positions 出现非 cast 角色: {sorted(pos_ids - cast_ids)}")

    for i, ex in enumerate(sa.get("exited_characters") or []):
        for field in ("character_id", "offscreen", "reason"):
            if is_unset(ex.get(field)):
                out.append(f"spatial_anchors.exited_characters[{i}] 缺 {field}")

    lb = sa.get("lighting_baseline")
    if not isinstance(lb, dict):
        out.append("spatial_anchors 缺 lighting_baseline")
    else:
        for field in ("key", "fill", "rim", "modifier"):
            if field not in lb or is_unset(lb.get(field)):
                out.append(f"spatial_anchors.lighting_baseline.{field} 缺（无写 none）")
    return out


def check_basics(card, profile):
    """Card-shape rules shared by G04 and G05: schema shape, duration, cast.

    Field presence, enums and formats come straight from the shot schema — no
    hand-copied required/enum list lives here. Duration must sit inside the
    duration_tier policy interval, intersected with the model envelope; cast
    size is a business rule.
    """
    out = validate_against_schema(card, load_schema("shot"))
    # 固定镜（type=locked）无运动，amplitude/speed 以 dash 占位为合法契约，
    # 通用 schema 引擎会把 dash 当 UNSET，此处按运动语义豁免（真空仍 FAIL）。
    mov = (card.get("cinematography") or {}).get("movement") or {}
    if mov.get("type") == "locked":
        dash_fields = {"amplitude", "speed"}
        out = [m for m in out if not (
            m.startswith("$.cinematography.movement.")
            and m.split(".")[-1].split(" ")[0] in dash_fields
            and mov.get(m.split(".")[-1].split(" ")[0]) in DASH_PLACEHOLDERS)]
    tier = card.get("duration_tier")
    try:
        duration = float(card.get("duration_s"))
        if tier in DURATION_TIERS:
            lo, hi = DURATION_TIERS[tier]
            lo = max(lo, profile.get("min_duration_s", 0))
            hi = min(hi, profile["max_duration_s"])
            if duration <= 0 or duration < lo or duration > hi:
                out.append(f"duration_s={duration:g} 越档（{tier}：{lo:g}–{hi:g}s）；"
                           "节拍不符改 duration_tier，装不下拆镜")
        elif duration <= 0 or duration > profile["max_duration_s"]:
            out.append(f"duration_s={duration:g} 越界（模型上限 "
                       f"{profile['max_duration_s']:g}s；超长拆镜）")
    except (TypeError, ValueError):
        out.append("duration_s 非数值")
    if len(card.get("cast") or []) > 3:
        out.append(f"在镜重要角色 {len(card.get('cast'))} 人 > 3，须拆镜或减角色")
    return out


def gate_S(root, cards, profile):
    problems = []
    for c in cards:
        sid = c.get("shot_id", "?")
        problems += _prefixed(sid, check_basics(c, profile))
        problems += _prefixed(sid, check_timeline(c))
        problems += _prefixed(sid, check_spatial(c))

    # ---- cross-shot: hook density + continuity/exited tracking ----
    problems += cross_shot_checks(cards)
    return problems


def cross_shot_checks(cards):
    """Cross-shot rules shared by G04 and re-asserted by G05.

    Hook density (twist every three shots, strong hooks at both ends) plus
    same-scene continuity annotations and exited-character tracking.
    """
    problems = []
    hooks = [(c.get("hook") or {}).get("hook_type") for c in cards]
    for i in range(len(cards) - 2):
        if not any(h in TWIST_HOOKS for h in hooks[i:i + 3]):
            problems.append(
                f"钩子密度: {cards[i].get('shot_id')}–{cards[i+2].get('shot_id')} "
                f"连续三镜无 reveal/reversal/callback")
    if cards:
        for label, idx in (("开场镜", 0), ("收尾镜", -1)):
            if hooks[idx] not in STRONG_HOOKS:
                problems.append(
                    f"{cards[idx].get('shot_id')}: {label}须带强钩"
                    f"（visual-joke/reversal/reveal/suspense/tender），现={hooks[idx]}")

    for a, b in zip(cards, cards[1:]):
        if a.get("scene_id") != b.get("scene_id"):
            continue
        problems += check_pair_continuity(a, b)
    return problems


def check_pair_continuity(a, b):
    """Same-scene adjacent pair: landmark/lighting shifts must be acknowledged."""
    out = []
    bsid = b.get("shot_id", "?")
    b_sa = b.get("spatial_anchors") or {}

    note = (b.get("cinematography") or {}).get("continuity") \
        or (b.get("timeline") or [{}])[0].get("handoff", "")
    note_low = note.lower()
    acknowledged = lambda text: text in note or any(w in note_low for w in CHANGE_WORDS)

    a_lm = {x.get("name"): x.get("screen_position")
            for x in (a.get("spatial_anchors") or {}).get("fixed_landmarks") or []}
    for lm in b_sa.get("fixed_landmarks") or []:
        name, pos = lm.get("name"), lm.get("screen_position")
        if name in a_lm and a_lm[name] != pos and not acknowledged(name or ""):
            out.append(f"{bsid}: 地标「{name}」画面位置由「{a_lm[name]}」变为「{pos}」，"
                       f"须在 cinematography.continuity 显式标注")

    a_key = ((a.get("spatial_anchors") or {}).get("lighting_baseline") or {}).get("key", "")
    b_key = (b_sa.get("lighting_baseline") or {}).get("key", "")
    if a_key and b_key and a_key != b_key \
            and "光" not in note and "light" not in note_low:
        out.append(f"{bsid}: 主光基线由「{a_key}」变为「{b_key}」，continuity 须显式说明")

    gone = {m.get("character_id") for m in a.get("cast") or []} \
         - {m.get("character_id") for m in b.get("cast") or []}
    tracked = {x.get("character_id") for x in b_sa.get("exited_characters") or []}
    for cid in gone - tracked:
        out.append(f"{bsid}: 角色 {cid} 上镜在、本镜不在，"
                   f"须填入 spatial_anchors.exited_characters（至少追踪一镜）")
    return out


def _prefixed(sid, messages):
    return [f"{sid}: {m}" for m in messages]


# ====================================================================== G05

def check_tail_graph(cards, cmap):
    """Tail-chain references: parent must exist; graph must be acyclic."""
    out = []
    edges = {}
    for c in cards:
        parent = (c.get("tail") or {}).get("tail_of")
        if not parent:
            continue
        if parent not in cmap:
            out.append(f'{c.get("shot_id")}: tail_of 指向不存在的镜 {parent}')
        edges[c["shot_id"]] = parent

    # Walk every chain once; a node that reached `done` needs no re-walk.
    done = set()
    for start in edges:
        if start in done:
            continue
        seen, node = [], start
        while node in edges and node not in done:
            if node in seen:
                cyc = seen[seen.index(node):] + [node]
                out.append("尾帧依赖成环: " + " -> ".join(cyc))
                break
            seen.append(node)
            node = edges[node]
        done.update(seen)
    return out


def check_cast_members(card):
    out = []
    for i, m in enumerate(card.get("cast") or []):
        if is_unset(m.get("character_id")) or m.get("retention") not in RETENTION:
            out.append(f"cast[{i}] 缺 character_id 或 retention 非法")
    return out


def check_needs(card):
    """Needs are minimal; scene needs add grid_id + cell (one shot, one cell)."""
    out = []
    image_paths = set()
    for i, n in enumerate(card.get("needs") or []):
        aid = n.get("asset_id", "?")
        for field in ("asset_id", "kind", "target_path"):
            if is_unset(n.get(field)):
                out.append(f"needs[{i}] ({aid}) 缺 {field}")
        kind = n.get("kind")
        if kind not in NEED_KINDS:
            out.append(f"needs[{i}] ({aid}) kind 非法: {kind}")
        if kind in IMAGE_KINDS:
            image_paths.add(n.get("target_path"))
        if kind == "scene":
            for field in ("grid_id", "cell"):
                if is_unset(n.get(field)):
                    out.append(f"needs[{i}] ({aid}) scene 条缺 {field}（一镜一格）")
    return out, image_paths


def check_cinematography(card):
    out = []
    cine = card.get("cinematography")
    if not cine:
        return ["缺 cinematography（摄影岗未填）"]
    groups = (
        ("camera", ("world_facing", "position", "height", "angle")),
        ("lens", ("focal_length", "dof", "focus")),
    )
    for group, fields in groups:
        obj = cine.get(group) or {}
        for field in fields:
            if is_unset(obj.get(field)):
                out.append(f"cinematography.{group}.{field} 未填")
    for field in ("composition", "lighting", "continuity"):
        if is_unset(cine.get(field)):
            out.append(f"cinematography.{field} 未填")
    mov = cine.get("movement")
    if not isinstance(mov, dict):
        out.append("cinematography.movement 缺失")
    else:
        for field in ("type", "amplitude", "speed"):
            if is_unset(mov.get(field)):
                # locked 固定镜：amplitude/speed 的 dash 占位合法（见 check_basics）
                if mov.get("type") == "locked" and field in ("amplitude", "speed") \
                        and mov.get(field) in DASH_PLACEHOLDERS:
                    continue
                out.append(f"cinematography.movement.{field} 缺（固定镜 speed 可写 —）")
    if "UNSET" in flatten(cine).upper():
        out.append("cinematography 内仍含 UNSET")
    return out


def check_soul_marks(card):
    out = []
    marks = (card.get("soul") or {}).get("motif_marks")
    if not marks:
        out.append("soul.motif_marks 为空")
    for i, mk in enumerate(marks or []):
        if is_unset(mk.get("motif_id")) or not isinstance(mk.get("occurrence"), int):
            out.append(f"soul.motif_marks[{i}] 缺 motif_id 或 occurrence(整数)")
    return out


def gate_A(root, cards, profile):
    problems = []

    if not os.path.exists(os.path.join(root, STYLE_DIRECTION)):
        problems.append(f"风格定向未冻结（缺 {STYLE_DIRECTION}）；先过 [2]")
    problems += check_tail_graph(cards, card_map(cards))

    for c in cards:
        sid = c.get("shot_id", "?")
        if c.get("status") != "design":
            problems.append(f"{sid}: G05 前 status 应为 design")

        problems += _prefixed(sid, check_basics(c, profile))
        problems += _prefixed(sid, check_timeline(c))
        problems += _prefixed(sid, check_spatial(c))
        problems += _prefixed(sid, check_cast_members(c))

        need_problems, image_paths = check_needs(c)
        problems += _prefixed(sid, need_problems)
        problems += _prefixed(sid, check_cinematography(c))

        # reference-slot feasibility against the model contract
        incoming = 1 if (c.get("tail") or {}).get("tail_of") else 0
        n_img = incoming + len(image_paths)
        if n_img > profile["max_ref_images"]:
            problems.append(f"{sid}: 参考图约需 {n_img} 槽 > {profile['max_ref_images']}，须在设计阶段拆镜")
        n_aud = 1 if c.get("lip_sync") else 0
        if n_aud > profile["max_ref_audios"]:
            problems.append(f"{sid}: 参考音频 {n_aud} 槽 > {profile['max_ref_audios']}")

        problems += _prefixed(sid, check_soul_marks(c))

    problems += check_asset_specs(root, cards)
    problems += check_soul_rules(root, cards)
    problems += check_style_rules(root, cards)
    # Re-assert the G04 cross-shot rules so G05 truly covers all six G04
    # items (the old gate_A skipped hook density + pair continuity).
    problems += cross_shot_checks(cards)
    return problems


# ---- asset design cards: field shape read from the spec schemas ----


def check_asset_specs(root, cards):
    # referenced asset id -> set of declared kinds; also keep every need for
    # later member alignment.
    referenced, needs_by_aid = {}, {}
    for c in cards:
        for n in c.get("needs") or []:
            aid = n.get("asset_id")
            if aid:
                referenced.setdefault(aid, set()).add(n.get("kind"))
                needs_by_aid.setdefault(aid, []).append((c.get("shot_id"), n))

    out = []
    for aid, kinds in referenced.items():
        if len(kinds) > 1:
            out.append(f"{aid}: 同 ID 被声明为多种 kind {sorted(kinds)}")
            continue
        kind = next(iter(kinds))
        spec_file = os.path.join(root, spec_path(aid))
        if not os.path.exists(spec_file):
            out.append(f"{aid}: 缺资产设计卡 {os.path.relpath(spec_file, root)}")
            continue
        try:
            spec = load_json(spec_file)
        except ValueError as e:
            out.append(f"{aid}: 设计卡无法解析 {e}")
            continue
        if spec.get("kind") != kind:
            out.append(f"{aid}: 设计卡 kind=「{spec.get('kind')}」≠ 引用「{kind}」")
            continue
        out += validate_spec_against_schema(aid, spec, kind)
        out += check_needs_alignment(aid, kind, spec, needs_by_aid.get(aid, []))
    return out


def validate_spec_against_schema(aid, spec, kind):
    """Schema shape plus the member-contract rules for one design card."""
    out = [f"{aid}: {msg}" for msg in
           validate_against_schema(spec, load_schema(kind))]
    contract = {"character": check_character_contract,
                "prop": check_prop_contract,
                "scene": check_scene_contract}.get(kind)
    if contract:
        out += [f"{aid}: {msg}" for msg in contract(spec)]
    return out


def check_character_contract(spec):
    out = []
    sheets = spec.get("sheets") or []
    ids = [s.get("sheet_id") for s in sheets]
    if len(set(ids)) != len(ids):
        out.append("sheets sheet_id 有重复")
    if ids.count("main") != 1:
        out.append("sheets 须恰好有一张 sheet_id=main")
    paths = [s.get("target_path") for s in sheets]
    if len(set(paths)) != len(paths):
        out.append("sheets target_path 有重复")
    main_path = next((s.get("target_path") for s in sheets
                      if s.get("sheet_id") == "main"), None)
    if main_path and (spec.get("consistency") or {}).get("sheet_ref") != main_path:
        out.append("consistency.sheet_ref 须等于 main sheet 的 target_path")
    return out


def check_prop_contract(spec):
    out = []
    grid = (spec.get("presentation") or {}).get("grid") or {}
    cells = grid.get("cells") or []
    pos = [c.get("position") for c in cells]
    if len(cells) == 1 and pos[0] == "single":
        return out
    wanted = ["tl", "tr", "bl", "br"]
    if len(pos) != len(set(pos)) or sorted(pos) != sorted(wanted):
        out.append(f"presentation.grid cells 须为单图(single) 或四格 "
                   f"tl/tr/bl/br 各一次；得 {pos}")
    return out


def check_scene_contract(spec):
    out = []
    grids = spec.get("grids") or []

    # Empty-environment default: scene plates carry no people; characters are
    # added at shot time via their character sheets. A populated scene must be
    # deliberate (surfaced for human review), never a silent default.
    figs = spec.get("figures") or {}
    if figs.get("contains_people"):
        out.append("场景卡 figures.contains_people=true：环境板默认空场；确需"
                   "人物请在人审时写明理由（人物通常以定妆 sheet 在镜头阶段加入）")

    gids = [g.get("grid_id") for g in grids]
    if len(set(gids)) != len(gids):
        out.append("grids grid_id 有重复")

    all_cells = []
    prev_target = None
    for g in grids:
        cells = g.get("cells") or []
        all_cells += cells
        cids = [c.get("cell_id") for c in cells]
        if len(set(cids)) != len(cids):
            out.append(f"grid {g.get('grid_id')} 内 cell_id 有重复")
        layout = g.get("layout")
        pos = [c.get("position") for c in cells]
        if layout == "single":
            if len(cells) != 1 or pos != ["single"]:
                out.append(f"grid {g.get('grid_id')} (single) 须恰有一个 "
                           f"position=single 的 cell；得 {pos}")
        else:
            wanted = GRID_POSITIONS.get(layout, [])
            if len(pos) != len(set(pos)) or sorted(pos) != sorted(wanted):
                out.append(f"grid {g.get('grid_id')} ({layout}) cells position "
                           f"须恰为 {wanted}；得 {pos}")
        if prev_target is not None and g.get("continuity_ref") != prev_target:
            out.append(f"grid {g.get('grid_id')} continuity_ref 须指向 "
                       f"上一张 grid target_path（{prev_target}）")
        prev_target = g.get("target_path")

    cids_all = [c.get("cell_id") for c in all_cells]
    if len(set(cids_all)) != len(cids_all):
        out.append("cell_id 跨 grid 有重复（须在场景内全局唯一）")

    # Shot <-> cell reconciliation: each served shot bound to exactly one cell.
    served = (spec.get("identity") or {}).get("serves_shots") or []
    bound = []
    for c in all_cells:
        bound += c.get("serves_shots") or []
    for s in set(x for x in bound if bound.count(x) > 1):
        out.append(f"镜头 {s} 被绑定到多个 cell（一镜一格）")
    for s in served:
        if s not in bound:
            out.append(f"serves_shots 中镜头 {s} 未绑定任何 cell")
    for s in set(bound):
        if s not in served:
            out.append(f"cell 绑定了 serves_shots 清单外的镜头 {s}")
    return out


def check_needs_alignment(aid, kind, spec, needs):
    """Every need must point at a member that exists in the design card."""
    out = []
    if kind == "character":
        sheets = {s.get("sheet_id"): s for s in spec.get("sheets") or []}
        for sid, n in needs:
            sh = sheets.get(n.get("sheet") or "main")
            if sh is None:
                out.append(f"{sid}: 人物 sheet {n.get('sheet') or 'main'} 不在设计卡")
            elif sh.get("target_path") != n.get("target_path"):
                out.append(f"{sid}: 人物 target_path 与 sheet 设计卡不一致")
    elif kind == "scene":
        grids = {g.get("grid_id"): g for g in spec.get("grids") or []}
        for sid, n in needs:
            g = grids.get(n.get("grid_id"))
            if g is None:
                continue  # missing grid_id already reported by check_needs
            if g.get("target_path") != n.get("target_path"):
                out.append(f"{sid}: 场景 target_path 与 grid 设计卡不一致")
            elif n.get("cell") not in {c.get("cell_id")
                                      for c in g.get("cells") or []}:
                out.append(f"{sid}: cell {n.get('cell')} 不在 grid "
                           f"{n.get('grid_id')} 内")
    elif kind == "prop":
        target = ((spec.get("presentation") or {}).get("grid") or {}) \
            .get("target_path")
        for sid, n in needs:
            if n.get("target_path") != target:
                out.append(f"{sid}: 道具 target_path 与设计卡 grid 不一致")
    return [f"{aid}: {msg}" for msg in out]


# ---- project rule files: style-checks.json / soul-checks.json ----

def check_style_rules(root, cards):
    """Forbidden terms must not appear anywhere that reaches generation.

    The scan covers needs, cinematography AND the per-second timeline (the
    old blob missed the timeline, so a banned term in the actual picture
    description slipped through). style-checks.json is a standard [2] output,
    so its absence is a FAIL, not a silent pass.
    """
    path = os.path.join(root, STYLE_CHECKS)
    if not os.path.exists(path):
        return [f"风格机器规则缺失（{STYLE_CHECKS}）；它是 [2] 标准产出，缺失即不能投产"]
    forbidden = load_json(path).get("forbidden_terms", [])
    out = []
    for c in cards:
        sid = c.get("shot_id", "?")
        blob = (flatten(c.get("needs", ""))
                + flatten(c.get("cinematography", ""))
                + flatten(c.get("timeline", ""))).lower()
        for term in forbidden:
            if term.lower() in blob:
                out.append(f"{sid}: 出现风格禁词「{term}」")
    return out


def is_subsequence(want, actual):
    i = 0
    for value in actual:
        if i < len(want) and value == want[i]:
            i += 1
    return i == len(want)


def check_soul_rules(root, cards):
    path = os.path.join(root, SOUL_CHECKS)
    if not os.path.exists(path):
        return [f"魂机器规则缺失（{SOUL_CHECKS}）；它是 [0] 标准产出，缺失即不能投产"]
    rules = load_json(path)
    out = []
    shot_order = [c.get("shot_id") for c in cards]

    marks = {}
    for c in cards:
        for mk in (c.get("soul") or {}).get("motif_marks") or []:
            marks.setdefault(mk.get("motif_id"), []).append(
                (c.get("shot_id"), mk.get("note", "")))

    for rule in rules.get("motifs", []):
        mid = rule.get("motif_id")
        motif_marks = marks.get(mid, [])
        if "min_count" in rule and len(motif_marks) < rule["min_count"]:
            out.append(f"魂: 母题 {mid} 出现 {len(motif_marks)} 次 < 要求 {rule['min_count']}")
        if rule.get("order"):
            marked_shots = [s for s in shot_order
                            if s in {m[0] for m in motif_marks}]
            if not is_subsequence(rule["order"], marked_shots):
                out.append(f"魂: 母题 {mid} 顺序不符 要求{rule['order']} 实际{marked_shots}")
        if rule.get("meaning_changes"):
            notes = [m[1] for m in motif_marks]
            if any(not n for n in notes) or len(set(notes)) != len(notes):
                out.append(f"魂: 母题 {mid} 每次意味须不同（note 缺失/重复）")

    cards_by_id = card_map(cards)
    for req in rules.get("required_shots", []):
        c = cards_by_id.get(req["shot_id"])
        if c is None:
            out.append(f"魂: 必备镜 {req['shot_id']} 不存在")
            continue
        blob = flatten(c.get("timeline", "")).lower()
        for term in req.get("must_contain", []):
            if term.lower() not in blob:
                out.append(f"魂: {req['shot_id']} 须含「{term}」")

    for req in rules.get("required_orientations", []):
        c = cards_by_id.get(req["shot_id"])
        if c is None:
            # Missing-shot here is a FAIL, consistent with required_shots
            # (the old code silently skipped it).
            out.append(f"魂: 必备方位镜 {req['shot_id']} 不存在")
            continue
        facing = ((c.get("cinematography") or {}).get("camera") or {}).get(
            "world_facing", "")
        if req["world_facing"] not in facing:
            out.append(f"魂: {req['shot_id']} world_facing 须含「{req['world_facing']}」，"
                       f"现=「{facing}」")
    return out


# ===================================================================== lock

def gate_lock(root, cards, profile, only_shot=None):
    bom_file = os.path.join(root, BOM_PATH)
    if not os.path.exists(bom_file):
        die(f"BOM not found ({BOM_PATH}); run build_bom.py")
    bom = load_json(bom_file)
    if bom.get("conflicts"):
        die("BOM has unresolved conflicts")
    # Image members are approved by target_path; voice/tts by asset id.
    status_by_path = {i["target_path"]: i["status"]
                      for i in bom.get("items", []) if i.get("target_path")}
    status_by_id = {i["asset_id"]: i["status"] for i in bom.get("items", [])}
    cmap = card_map(cards)

    problems = []
    for c in cards:
        sid = c.get("shot_id", "?")
        # In --shot mode only the named card is a go/no-go target; other
        # cards not yet locked (tail-chain interleaving) are not failures.
        if only_shot is not None and sid != only_shot:
            continue
        if c.get("status") != "locked":
            problems.append(f"{sid}: status 未翻转为 locked")

        for n in c.get("needs") or []:
            kind, path = n.get("kind"), n.get("target_path")
            if kind in IMAGE_KINDS:
                if not exists(root, path):
                    problems.append(f"{sid}: 资产文件缺失: {path}")
                if status_by_path.get(path) != "approved":
                    problems.append(f"{sid}: 资产 {path} 未 approved"
                                    f"（现={status_by_path.get(path)}）")
            else:
                # sound needs keep the legacy asset-id lookup
                if not exists(root, path):
                    problems.append(f"{sid}: 资产文件缺失: {path}")
                if status_by_id.get(n.get("asset_id")) != "approved":
                    problems.append(f"{sid}: 资产 {n.get('asset_id')} 未 approved")

        if c.get("lip_sync"):
            audio = c.get("audio") or {}
            if not exists(root, audio.get("tts_path")):
                problems.append(f"{sid}: 开口镜 tts wav 缺失: {audio.get('tts_path')}（只核存在，不核时长）")
            if status_by_id.get(audio.get("tts_asset_id")) != "approved":
                problems.append(f"{sid}: tts 资产 {audio.get('tts_asset_id')} 未 approved")

        parent = (c.get("tail") or {}).get("tail_of")
        if parent:
            par = cmap.get(parent)
            if not par:
                problems.append(f"{sid}: 父镜 {parent} 不存在")
            else:
                if par.get("status") != "locked":
                    problems.append(f"{sid}: 父镜 {parent} 未 locked")
                parent_tail = (par.get("tail") or {}).get("target_path")
                if not exists(root, parent_tail):
                    problems.append(f"{sid}: 父镜尾帧未就位: {parent_tail}")
    if only_shot is not None and only_shot not in cmap:
        problems.append(f"--shot {only_shot} 不在镜头卡中")
    return problems


# ====================================================================== G07

# Closed tag namespace: the ONLY tag forms legal in gen.json labels.
TAG_RE = re.compile(r"<(Picture|Subject|Video|Audio) (\d+)>")
# Tag references inside prompt.md: usually bracketed, but the official FL2VA
# wording writes bare `Picture N` (both in its first line and body). Normalize
# every match back to the bracketed form before comparing.
BODY_TAG_RE = re.compile(r"<?(Picture|Subject|Video|Audio) (\d+)>?")


def _norm_tag(kind, num):
    return f"<{kind} {num}>"
# Removed from gen.json; their values live only in profile.conditions[mode].
GEN_OBSOLETE_FIELDS = ("first_line_instruction", "core_fields")


def check_gen_shape(gen, profile):
    # Required fields, item shapes, label patterns and role enums come from
    # the gen schema. Mode/model/resolution closed sets come from the profile.
    out = validate_against_schema(gen, load_schema("gen"))
    for key in GEN_OBSOLETE_FIELDS:
        if key in gen:
            out.append(f"gen 含已废弃字段「{key}」：段名/段序与首行类型由 "
                       f"profile.conditions 唯一派生，请从 gen.json 删除")
    if gen.get("mode") not in profile["conditions"]:
        out.append(f"gen mode 非法: {gen.get('mode')}（profile 条件: "
                   f"{', '.join(profile['conditions'])}）")
    model_values = profile.get("gen_model_values")
    if model_values and gen.get("model") not in model_values:
        out.append(f"gen model 非法: {gen.get('model')}（允许: {', '.join(model_values)}）")
    if gen.get("resolution") not in profile["resolutions"]:
        out.append(f"gen resolution 非法: {gen.get('resolution')}"
                   f"（profile: {', '.join(profile['resolutions'])}）")
    return out


def checkpoint_for(profile, mode):
    """Return (name, spec) of the physical checkpoint serving `mode`."""
    for name, spec in (profile.get("checkpoints") or {}).items():
        if mode in (spec.get("modes") or []):
            return name, spec
    return None, None


def _slot_index(item):
    m = re.search(r"(\d+)\s*$", item.get("slot") or "")
    return int(m.group(1)) if m else 0


def _image_bucket(card, item, mode=None):
    """Classify an image slot into a profile slot_order bucket."""
    role = item.get("role")
    # A parent tail is the dedicated first frame of an I2VA tail-chain shot.
    # The same image referenced in Ref2VA is just an ordinary frame anchor.
    if mode == "I2VA" and (card.get("tail") or {}).get("tail_of") \
            and role == "first-frame":
        return "parent-tail"
    if role == "style-key":
        return "style-key"
    if role in ("first-frame", "last-frame"):
        return "frame-anchor"
    return "subject"


def check_ref_slots(root, card, gen, profile):
    out = []
    images = gen.get("ref_images") if isinstance(gen.get("ref_images"), list) else []
    videos = gen.get("ref_videos") if isinstance(gen.get("ref_videos"), list) else []
    audios = gen.get("ref_audios") if isinstance(gen.get("ref_audios"), list) else []

    policy = profile.get("tag_policy") or {}
    role_tag = policy.get("role_tag") or {}
    ckpt_name, ckpt = checkpoint_for(profile, gen.get("mode"))
    scene_need = next((n for n in card.get("needs") or []
                       if n.get("kind") == "scene"), None)

    # Per-slot: file exists; label is a closed tag of the right kind; role maps
    # to that tag kind per the profile tag_policy.
    slot_groups = (("ref_images", images, ("Picture", "Subject")),
                   ("ref_videos", videos, ("Video",)),
                   ("ref_audios", audios, ("Audio",)))
    for media, items, kinds in slot_groups:
        for item in items:
            path = (item.get("path") or "").replace("\\", "/")
            if not path or not exists(root, path):
                out.append(f"{media}文件缺失: {path}（标签 {item.get('label')}）")
            m = TAG_RE.fullmatch(item.get("label") or "")
            if not m:
                out.append(f"{media} label 非法（只能是模板标签 "
                           f"{'/'.join(kinds)} N）: {item.get('label')}")
                continue
            kind = m.group(1)
            if kind not in kinds:
                out.append(f"{media} 标签类别 {kind} 非法"
                           f"（应 {'/'.join(kinds)}）: {item['label']}")
            role = item.get("role")
            if role not in role_tag:
                out.append(f"{media} role 非法: {role}"
                           f"（profile tag_policy 未登记）")
            elif role_tag[role] != kind:
                out.append(f"{media} role「{role}」与标签 {item['label']} "
                           f"不符（应为 <{role_tag[role]} N>）")
            elif media == "ref_images" and role == "scene-grid":
                cell = item.get("cell")
                if is_unset(cell):
                    out.append(f"{media} scene-grid {item.get('label')} "
                               "缺 cell（一镜一格）")
                elif (scene_need is None or cell != scene_need.get("cell")
                      or path != (scene_need.get("target_path") or ""
                                  ).replace("\\", "/")):
                    out.append(f"{media} scene-grid {item.get('label')} cell "
                               "与镜头卡 needs 的 scene 条不一致")

    # Video references exist only where the checkpoint spec supports them.
    if videos and not (ckpt or {}).get("videos"):
        out.append("ref_videos 仅支持视频参考的 checkpoint 可用"
                   "（当前 checkpoint spec.videos 为空）")

    # Image-slot ceiling: the mode-specific physical checkpoint limit when it
    # is known; fall back to the coarse profile ceiling.
    image_spec = (ckpt or {}).get("images") if ckpt else None
    image_max = image_spec["max"] if image_spec else profile["max_ref_images"]
    if len(images) > image_max:
        label = f"checkpoint {ckpt_name}" if ckpt else "profile"
        out.append(f"参考图 {len(images)} 槽 > {image_max}（{label} 上限），"
                   f"多人多物全绑定改判 Ref2VA，否则拆镜")

    if len(audios) > profile["max_ref_audios"]:
        out.append(f"参考音频 {len(audios)} 槽 > {profile['max_ref_audios']}")

    requirements = profile.get("pipeline_requirements", {})
    # T1 exemption: when every image slot is occupied by a frame anchor at the
    # checkpoint ceiling (H3: FL2VA = two frames), no slot remains for a key.
    full_of_anchors = bool(images) and len(images) == image_max and all(
        i.get("role") in ("first-frame", "last-frame") for i in images)
    if requirements.get("style_key_required") and not full_of_anchors and not any(
            i.get("role") == "style-key"
            or "03-style/keys/" in (i.get("path") or "") for i in images):
        out.append("未垫 Style Key 样板图（ref_images 须含 role=style-key）")

    if card.get("lip_sync") and requirements.get("tts_required_for_lip_sync") \
            and not any(i.get("role") == "tts" for i in audios):
        out.append("开口镜 ref_audios 须绑该角色 tts（多镜复用同一 wav）")

    gd = gen.get("duration_s")
    if isinstance(gd, (int, float)) \
            and abs(float(gd) - float(card.get("duration_s"))) > 0.01:
        out.append(f"gen.duration_s={gd} ≠ 镜头卡 duration_s={card.get('duration_s')}")

    # Slot order per the checkpoint's tag_policy ordering.
    order = (policy.get("slot_order") or {}).get(ckpt_name or "", [])
    if images and order:
        ranks = []
        for item in sorted(images, key=_slot_index):
            bucket = _image_bucket(card, item, gen.get("mode"))
            if bucket not in order:
                out.append(f"参考槽类别「{bucket}」不在 profile slot_order 内"
                           f"（{order}）")
            else:
                ranks.append(order.index(bucket))
        if any(ranks[i] > ranks[i + 1] for i in range(len(ranks) - 1)):
            out.append(f"参考槽顺序不符 profile slot_order: {order}")

    # Picture/Video/Audio numbering: per kind, 1..n by slot order.
    for kind, items in (("Picture", images), ("Video", videos),
                        ("Audio", audios)):
        nums = []
        for item in sorted(items, key=_slot_index):
            m = TAG_RE.fullmatch(item.get("label") or "")
            if m and m.group(1) == kind:
                nums.append(int(m.group(2)))
        want = list(range(1, len(nums) + 1))
        if sorted(nums) != want:
            out.append(f"{kind} 标签编号须从 1 连续不重号："
                       f"得 {nums}；应 {want}")

    # Subject numbering: one number per asset group. Group key = explicit ref,
    # except style-key (its own group) and ungrouped images (grouped by path).
    if images:
        group_of_num = {}
        for item in sorted(images, key=_slot_index):
            m = TAG_RE.fullmatch(item.get("label") or "")
            if not m or m.group(1) != "Subject":
                continue
            num = int(m.group(2))
            key = "style-key" if item.get("role") == "style-key" \
                else (item.get("ref") or item.get("path"))
            if num in group_of_num and group_of_num[num] != key:
                out.append(f"<Subject {num}> 被多个不相关资产共用"
                           f"（同 Subject 须填同一 ref 资产代号）："
                           f"{group_of_num[num]} ≠ {key}")
            group_of_num.setdefault(num, key)
        nums = sorted(group_of_num)
        want = list(range(1, len(nums) + 1))
        if nums != want:
            out.append(f"Subject 标签编号须从 1 连续："
                       f"得 {nums}；应 {want}")

    # Remaining checkpoint counts already declared in the profile spec.
    if ckpt:
        vspec, aspec = ckpt.get("videos"), ckpt.get("audios")
        if vspec and len(videos) > vspec["max"]:
            out.append(f"参考视频 {len(videos)} 段 > {vspec['max']}"
                       f"（checkpoint 上限）")
        if aspec:
            if len(audios) > aspec["max"]:
                out.append(f"参考音频 {len(audios)} 段 > {aspec['max']}"
                           f"（checkpoint 上限）")
            if aspec.get("requires_visual_input") and audios \
                    and not images and not videos:
                out.append("音频不能作为唯一输入（checkpoint 要求与图像"
                           "或视频一起使用）")
        total_max = ckpt.get("total_files_max")
        if total_max and len(images) + len(videos) + len(audios) > total_max:
            out.append(f"参考文件总数 {len(images) + len(videos) + len(audios)}"
                       f" > {total_max}（checkpoint 上限）")
    return out


def check_prompt_structure(prompt_path, card, gen, profile):
    """Extract closed structural tokens from prompt.md; never judge wording.

    Three checks only: section headers vs profile core_fields (ordered exact
    equality), first-line anchors (tags + two-decimal seconds), and a
    bidirectional tag-set cross-check against gen.json's declared labels.
    """
    out = []
    condition = profile["conditions"][gen["mode"]]
    want_fields = condition["core_fields"]

    with open(prompt_path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()

    # 1) Section headers: ordered exact equality with profile core_fields.
    found = []
    for line in lines:
        head = line.strip()
        for field in want_fields:
            if head.startswith(field + ":"):
                found.append(field)
    if found != want_fields:
        out.append(f"正文字段（段名/段序/段数）与 profile 不符："
                   f"得 {found or '无'}；应 {want_fields}")

    # 2) First line.
    nonblank = [(i, ln) for i, ln in enumerate(lines) if ln.strip()]
    if not nonblank:
        out.append("prompt.md 为空")
        return out
    first_idx, first_line_text = nonblank[0]
    fl = condition.get("first_line", "none")
    if isinstance(fl, dict):
        fl_type = fl.get("type", "none")
    else:
        fl_type = fl if isinstance(fl, str) else "none"

    duration_str = f"{float(card.get('duration_s') or 0):.2f}"
    anchor_tags = [_norm_tag(k, n)
                   for k, n in BODY_TAG_RE.findall(first_line_text)]
    seconds = re.findall(r"\d+\.\d{2}", first_line_text)

    if fl_type == "none":
        if not first_line_text.strip().startswith(want_fields[0] + ":"):
            out.append("该模式无首行指令：正文必须直接以 "
                       f"「{want_fields[0]}:」开头")
    else:
        want_tags = {
            "first_frame": ["<Picture 1>"],
            "last_frame": ["<Picture 1>"],
            "first_last": ["<Picture 1>", "<Picture 2>"],
        }.get(fl_type, [])
        want_seconds = {
            "first_frame": ["0.00"],
            "last_frame": [duration_str],
            "first_last": ["0.00", duration_str],
        }.get(fl_type, [])
        if anchor_tags != want_tags:
            out.append(f"首行标签不符：得 {anchor_tags}；应 {want_tags}")
        missing = [s for s in want_seconds if s not in seconds]
        if missing:
            out.append(f"首行秒值缺失或非两位小数：应含 {want_seconds}")
        if first_idx + 1 >= len(lines) or lines[first_idx + 1].strip():
            out.append("首行指令后必须空一行再写核心字段")

    # 3) Bidirectional tag-set cross-check against gen.json.
    gen_labels = set()
    for key in ("ref_images", "ref_videos", "ref_audios"):
        for item in gen.get(key) or []:
            if item.get("label"):
                gen_labels.add(item["label"])
    body_labels = {_norm_tag(k, n) for k, n in BODY_TAG_RE.findall(text)}
    undeclared = sorted(body_labels - gen_labels)
    unused = sorted(gen_labels - body_labels)
    if undeclared:
        out.append(f"正文使用了 gen 未声明的标签: {undeclared}")
    if unused:
        out.append(f"gen 声明但正文未使用的标签: {unused}")
    return out


def gate_B(root, cards, profile):
    # Style spec is the canonical source every locked prompt must obey.
    ss_problems = gate_SS(root)
    problems = [f"画风规格未过 SS：{m}" for m in ss_problems]
    for c in cards:
        sid = c.get("shot_id", "?")
        if c.get("status") != "locked":
            problems.append(f"{sid}: 仅 locked 卡可过 G07（现 status={c.get('status')}）")
            continue

        prompt_file = os.path.join(root, "08-prompts", f"{sid}.prompt.md")
        gen_file = os.path.join(root, "08-prompts", f"{sid}.gen.json")
        if not os.path.exists(prompt_file):
            problems.append(f"{sid}: 缺 prompt: 08-prompts/{sid}.prompt.md")
            continue
        if not os.path.exists(gen_file):
            problems.append(f"{sid}: 缺 gen: 08-prompts/{sid}.gen.json")
            continue

        gen = load_json(gen_file)
        problems += _prefixed(sid, check_gen_shape(gen, profile))
        if gen.get("mode") in profile["conditions"]:
            problems += _prefixed(sid, check_ref_slots(root, c, gen, profile))
            problems += _prefixed(sid,
                                  check_prompt_structure(prompt_file, c,
                                                         gen, profile))
    return problems


# ================================================================== G02 SD

DIR_STYLE = "03-style"


def _registered_model_dirs():
    """Directory names of every registered model (one that has profile.json)."""
    models_dir = os.path.join(skill_root(), "references", "models")
    out = set()
    if os.path.isdir(models_dir):
        for name in os.listdir(models_dir):
            if os.path.exists(os.path.join(models_dir, name, "profile.json")):
                out.add(name)
    return out


def gate_SD(root):
    """G02 style-direction machine checks. Zero-cost file/field existence.

    Runs at the end of [2], before any shot card exists, so it uses neither
    load_cards nor the single target profile; model limits do not apply here.
    """
    out = []

    # 1) the frozen style direction itself
    sd = os.path.join(root, DIR_STYLE, "style-direction.md")
    if not os.path.exists(sd):
        out.append(f"风格定向未冻结（缺 {DIR_STYLE}/style-direction.md）")
    elif "UNSET" in open(sd, encoding="utf-8").read():
        out.append(f"{DIR_STYLE}/style-direction.md 仍含 UNSET，须冻结")

    # 2) comparable-work research and bottom-up candidates
    if not os.path.exists(os.path.join(root, DIR_STYLE, "comps.md")):
        out.append(f"缺 {DIR_STYLE}/comps.md（同类型作品调研）")
    if not os.path.exists(os.path.join(root, DIR_STYLE, "candidates.md")):
        out.append(f"缺 {DIR_STYLE}/candidates.md（自下而上候选）")

    # 3) matrix parses, matches its schema, and rates every registered model
    matrix_path = os.path.join(root, DIR_STYLE, "model-matrix.json")
    matrix = None
    if not os.path.exists(matrix_path):
        out.append(f"缺 {DIR_STYLE}/model-matrix.json（跨模型能力矩阵）")
    else:
        try:
            matrix = load_json(matrix_path)
            out += validate_against_schema(matrix, load_schema("style-matrix"))
        except ValueError as e:
            out.append(f"model-matrix.json 无法解析 {e}")
        if matrix is not None:
            registered = _registered_model_dirs()
            for cand in matrix.get("candidates") or []:
                cid = cand.get("candidate_id", "?")
                rated = {r.get("model") for r in cand.get("model_ratings") or []}
                missing = registered - rated
                if missing:
                    out.append(f"候选 {cid} 缺模型评级: {sorted(missing)}")

    # 4) charter written back; the selected pairing must not be unsupported
    model = target_model(root, required=False)
    if not model:
        out.append("charter 目标模型尚未回写锁定（[2] 用户选定后回写）")
    elif matrix is not None:
        sel_cid = (matrix.get("selection") or {}).get("candidate_id")
        if sel_cid:
            for cand in matrix.get("candidates") or []:
                if cand.get("candidate_id") != sel_cid:
                    continue
                for r in cand.get("model_ratings") or []:
                    if r.get("model") == model and r.get("level") == "unsupported":
                        out.append(f"选定组合 {sel_cid} × {model} 评级 unsupported，"
                                   f"不得锁定")
    return out


def gate_SS(root):
    """Style-spec slot contract (part of [9], before burning Style Keys).

    Fail-loud: the structured style source must exist, parse, match its
    project-agnostic slot schema, and carry no UNSET/placeholder values.
    No silent fallback — [9b] and G07 refuse to run when this fails.
    """
    path = os.path.join(root, DIR_STYLE, "style-spec.json")
    if not os.path.exists(path):
        return [f"画风规格未填写（缺 {DIR_STYLE}/style-spec.json；[9] 按 "
                "schemas/style-spec.schema.json 的槽位填写）"]
    try:
        spec = load_json(path)
    except ValueError as e:
        return [f"style-spec.json 无法解析 {e}"]
    problems = validate_against_schema(spec, load_schema("style-spec"))
    raw = open(path, encoding="utf-8").read()
    if "UNSET" in raw or "TODO" in raw or "在此填" in raw or "占位" in raw:
        problems.append("style-spec.json 仍含 UNSET/TODO/占位文字，须填实")
    return problems


# ================================================================== gate W

def gate_W(root, write_frozen=True):
    """World-integrity gate (end of [4]).

    For every 04-world/<world>: geography / axis_table / brightness must
    exist, parse, and match their schemas; camera facings must resolve to
    spaces in geography, and brightness light ids must match geography
    light sources. On full pass the three files are marked frozen=true.
    No silent gaps — downstream [5][6][7] treat these as the objective root.
    """
    worlds_dir = os.path.join(root, "04-world")
    if not os.path.isdir(worlds_dir):
        return [f"无 04-world/ 目录；[4] 世界设计缺失"]

    problems = []
    for name in sorted(os.listdir(worlds_dir)):
        wdir = os.path.join(worlds_dir, name)
        if not os.path.isdir(wdir):
            continue
        files = {
            "geography": ("geography.json", "geography"),
            "axis_table": ("axis_table.json", "axis-table"),
            "brightness": ("brightness.json", "brightness"),
        }
        loaded = {}
        for label, (fname, schema_key) in files.items():
            fpath = os.path.join(wdir, fname)
            if not os.path.exists(fpath):
                problems.append(f"[{name}] 缺 {fname}")
                continue
            try:
                obj = load_json(fpath)
            except ValueError as e:
                problems.append(f"[{name}] {fname} 无法解析 {e}")
                continue
            problems += [f"[{name}] {m}" for m in
                         validate_against_schema(obj, load_schema(schema_key))]
            loaded[label] = (fpath, obj)

        if "geography" in loaded and "axis_table" in loaded:
            geo = loaded["geography"][1]
            axis = loaded["axis_table"][1]
            spaces = {s.get("id") for s in geo.get("spaces", [])}
            for cam in axis.get("camera_facings", []):
                if cam.get("space") not in spaces:
                    problems.append(
                        f"[{name}] 机位 {cam.get('id')} 的 space "
                        f"{cam.get('space')} 不在 geography.spaces")
            # Cross-referenced camera ids the shot cards may cite.
            geo_cam = {c.get("id") for c in axis.get("camera_facings", [])}
            axis_ids = {a.get("axis_id") for a in axis.get("narrative_axes", [])}
            for decl in axis.get("crossing_declarations", []):
                if decl.get("axis_id") not in axis_ids:
                    problems.append(
                        f"[{name}] 越轴声明指向未知 axis: {decl.get('axis_id')}")

        if "geography" in loaded and "brightness" in loaded:
            geo = loaded["geography"][1]
            bright = loaded["brightness"][1]
            source_ids = {s.get("id") for s in geo.get("light_sources", [])}
            for lvl in bright.get("light_levels", []):
                if lvl.get("light_id") not in source_ids:
                    problems.append(
                        f"[{name}] brightness light_id {lvl.get('light_id')} "
                        f"不在 geography.light_sources")

        # On a clean world, freeze the three files.
        if write_frozen and not any(p.startswith(f"[{name}]") for p in problems):
            for label, (fpath, obj) in loaded.items():
                if obj.get("frozen") is not True:
                    obj["frozen"] = True
                    dump_json(obj, fpath)
    return problems


# ================================================================== gate T

def gate_T(root, cards, profile, only_shot=None):
    """Take-delivery gate (after [14]).

    For every shot: a take recorded in 09-takes/<SHOT>/takes.json exists,
    its declared clip file is present, the tail frame has been extracted to
    tail.target_path (so a child shot can lock), and provenance matches
    between gen.json and the ledger. An unapproved (non-final) take is not
    a delivery.
    """
    problems = []
    for c in cards:
        sid = c.get("shot_id", "?")
        if only_shot is not None and sid != only_shot:
            continue
        ledger_rel = os.path.join("09-takes", sid, "takes.json")
        ledger_path = os.path.join(root, ledger_rel)
        if not os.path.exists(ledger_path):
            problems.append(f"{sid}: 无 take 台账 {ledger_rel}（未提交 [14]）")
            continue
        ledger = load_json(ledger_path)
        takes = ledger.get("takes") or []
        if not takes:
            problems.append(f"{sid}: takes.json 无任何 take")
            continue

        delivered = False
        for t in takes:
            clip = t.get("path")
            if clip and not exists(root, clip):
                problems.append(f"{sid}: take 文件缺失 {clip}")
            # A produced-but-not-user-approved take is not final delivery.
            if t.get("status") not in ("approved",):
                continue
            delivered = True
            gen_path = os.path.join(root, "08-prompts", f"{sid}.gen.json")
            if os.path.exists(gen_path):
                gen_prov = (load_json(gen_path).get("provenance") or {})
                tp = t.get("provenance") or {}
                if gen_prov.get("task_id") != tp.get("task_id"):
                    problems.append(
                        f"{sid}: provenance task_id 台账与 gen.json 不一致")
        if not delivered:
            problems.append(f"{sid}: 无用户 approved 的 take（交付需用户人审）")

        # Tail frame must be extracted to the declared target path so the
        # child shot has its parent tail in place.
        tail = c.get("tail") or {}
        if tail.get("target_path") and not exists(root, tail["target_path"]):
            problems.append(
                f"{sid}: 尾帧未抽出到 {tail['target_path']}（ffmpeg --tail）")
    return problems


# ==================================================================== main

# Internal gate functions keep their short keys (low churn); the command line
# accepts both the canonical Gxx ids and the legacy short names.
GATES = {
    "S": (gate_S, "G04 SHOT SELF-CHECK"),
    "A": (gate_A, "G05 DESIGN FREEZE"),
    "lock": (gate_lock, "LOCK"),
    "B": (gate_B, "G07 PROMPT FREEZE"),
    "T": (gate_T, "GATE T · TAKE DELIVERY"),
}

# command token -> internal gate key
GATE_ALIASES = {
    "G02": "SD", "SD": "SD",
    "G04": "S", "S": "S",
    "G05": "A", "A": "A",
    "G07": "B", "B": "B",
    "SS": "SS",
    "W": "W",
    "T": "T",
    "lock": "lock",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--gate", required=True, choices=sorted(GATE_ALIASES))
    ap.add_argument("--shot", help="lock/T: verify a single shot (tail-chain interleaving)")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    key = GATE_ALIASES[args.gate]

    if key in ("SD", "SS", "W"):
        if key == "SD":
            problems = gate_SD(root)
            title = "G02 STYLE DIRECTION"
        elif key == "SS":
            problems = gate_SS(root)
            title = "STYLE SPEC SLOT CONTRACT"
        else:
            problems = gate_W(root)
            title = "GATE W · WORLD INTEGRITY"
        n_cards = 0
        model = target_model(root, required=False) or "-"
    else:
        cards = load_cards(root)
        if not cards:
            die(f"no shot cards under {os.path.join(root, '05-shots')}")
        profile = load_profile(root)
        fn, title = GATES[key]
        if key in ("lock", "T"):
            problems = fn(root, cards, profile, only_shot=args.shot)
        else:
            problems = fn(root, cards, profile)
        n_cards, model = len(cards), profile.get("model", "-")

    print(f"== {title} : {n_cards} card(s) | model: {model} ==")
    if problems:
        for msg in problems:
            print(f"  FAIL {msg}")
        print(f"\n{len(problems)} problem(s) — gate FAILED")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
