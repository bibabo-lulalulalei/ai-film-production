# -*- coding: utf-8 -*-
"""Mechanically derive per-asset production prompts from design cards + BOM.

[9b] runs after style refinement [9] and before asset production [10]. The
wording lives in external, model-agnostic templates under
references/asset-prompt-templates/ (one template per asset kind); this script
only fills the placeholders with values read from the design cards — it never
invents wording. Multi-member assets (character state sheets, scene grids)
render one block per member.

Usage: python scripts/build_asset_prompts.py <project-root>
Output: 06-bom/asset-prompts/<ASSET>.md (one file per asset)
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (BOM_PATH, KEYS_DIR, STYLE_CHECKS, die, load_json,
                     skill_root, write_text)

TEMPLATE_DIR = os.path.join("references", "asset-prompt-templates")
TEMPLATE_FILE = {"character": "character-sheet-prompt.md",
                 "prop": "prop-grid-prompt.md",
                 "scene": "scene-grid-prompt.md"}
OUT_DIR = os.path.join("06-bom", "asset-prompts")
# Everything below this marker in a template is the placeholder reference
# table and must not appear in a rendered prompt.
CUTOFF_MARK = "<!-- === 分隔线"
TOKEN_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")

# Grid cell position -> Chinese panel label (used in numbered view blocks).
POS_CN = {"single": "单图", "tl": "左上角", "tc": "上方正中", "tr": "右上角",
          "ml": "左侧正中", "c": "居中", "mr": "右侧正中",
          "bl": "左下角", "bc": "下方正中", "br": "右下角"}


def main(root):
    bom_file = os.path.join(root, BOM_PATH)
    if not os.path.exists(bom_file):
        die(f"缺 {BOM_PATH}；先跑 [8] build_bom")
    items = load_json(bom_file).get("items", [])

    forbidden = []
    style_rules = os.path.join(root, STYLE_CHECKS)
    if os.path.exists(style_rules):
        forbidden = load_json(style_rules).get("forbidden_terms") or []

    keys = [os.path.relpath(p, root).replace("\\", "/")
            for p in sorted(glob.glob(os.path.join(root, KEYS_DIR, "*.png")))]
    style_spec = load_style_spec(root)

    # Group BOM rows by asset_id; voice/tts are not visual assets.
    groups = {}
    for it in items:
        if it.get("kind") in ("voice", "tts"):
            continue
        groups.setdefault(it.get("asset_id"), []).append(it)

    errors, written = [], []
    templates = {}
    for aid, rows in groups.items():
        spec = load_spec(root, rows[0], errors)
        if spec is None:
            continue
        kind = spec.get("kind")
        if kind not in TEMPLATE_FILE:
            errors.append(f"{aid}: 未知 kind {kind}")
            continue
        if kind not in templates:
            templates[kind] = load_template(kind)

        doc = preamble(spec, rows, keys) + [""]

        def member_text(ctx):
            ctx["forbidden"] = joined_forbidden(forbidden)
            return render(templates[kind], ctx)

        if kind == "character":
            for sheet in spec.get("sheets") or []:
                doc += [member_text(
                    character_context(spec, sheet, style_spec)),
                    "", "---", ""]
            doc = doc[:-2]  # drop trailing separator
        elif kind == "scene":
            for grid in spec.get("grids") or []:
                doc += [member_text(
                    scene_context(spec, grid, style_spec)),
                    "", "---", ""]
            doc = doc[:-2]
        else:
            doc += [member_text(prop_context(spec, style_spec))]

        text = "\n".join(doc).strip() + "\n"
        leftover = sorted(set(TOKEN_RE.findall(text)))
        if leftover:
            errors.append(f"{aid}: 模板占位未填充 {leftover}")
            continue
        path = os.path.join(root, OUT_DIR, f"{aid}.md")
        write_text(path, text)
        written.append(aid)

    if errors:
        print(f"{len(written)} prompt(s) written, {len(errors)} error(s):")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    print(f"asset prompts ok: {len(written)} file(s) -> {OUT_DIR}/")
    for n in written:
        print("  " + n)


def load_style_spec(root):
    """Load + hard-validate the project's style-spec slot contract.

    Fail-loud: [9b] refuses to run when the spec is missing/malformed
    (same checks as `validation/lint_cards.py --gate SS`).
    """
    val_dir = os.path.join(skill_root(), "validation")
    sys.path.insert(0, val_dir)
    from lint_cards import gate_SS  # reuse the canonical checks
    problems = gate_SS(root)
    if problems:
        for m in problems:
            print("  FAIL " + m)
        die("画风规格未过 SS；先在 [9] 填 03-style/style-spec.json 并跑 "
            "validation/lint_cards.py <root> --gate SS")
    return load_json(os.path.join(root, "03-style", "style-spec.json"))


def _clause(text):
    """Normalize one self-describing clause: drop terminal punctuation."""
    return str(text).strip().rstrip("。.；;，,")


def _look_clauses(spec, full=False):
    look = spec["look"]
    bits = [look["exposure"], look["contrast"], look["depth_of_field"],
            look["highlights"]]
    if full:
        bits.append(look["grain"])
    return bits


def compose_style(spec, kind):
    """Assemble the per-asset-kind style paragraph from contract slots.

    Every clause is self-describing (carries its own concrete cue); we only
    normalize terminal punctuation and join — no added labels that could
    duplicate words already in the slot values.
    """
    shape = spec["shape_language"]
    parts = [spec["medium"]["is"], shape["tendency"], shape["edges"]]
    parts += _look_clauses(spec, full=(kind == "scene"))

    if kind == "character":
        pr, mat, line = spec["proportions"], spec["materials"], spec["line"]
        parts += [pr["human"], pr["anatomy"], mat["overall"], line["near"]]
    elif kind == "prop":
        mat, line = spec["materials"], spec["line"]
        parts += [f"{s['part']}：{s['quality']}" for s in mat["surfaces"]]
        parts.append(line["near"])
    else:  # scene
        mat, line = spec["materials"], spec["line"]
        parts += [mat["overall"], line["far"]]
    return "；".join(_clause(p) for p in parts)


def load_spec(root, item, errors):
    rel = item.get("spec_path")
    if not rel or rel == "—":
        errors.append(f"{item.get('asset_id')}: BOM 行缺 spec_path")
        return None
    path = os.path.join(root, rel)
    if not os.path.exists(path):
        errors.append(f"{item.get('asset_id')}: 缺设计卡 {rel}")
        return None
    return load_json(path)


def load_template(kind):
    path = os.path.join(skill_root(), TEMPLATE_DIR, TEMPLATE_FILE[kind])
    if not os.path.exists(path):
        die(f"缺模板 {os.path.relpath(path, skill_root())}")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    idx = text.find(CUTOFF_MARK)
    return text[:idx] if idx >= 0 else text


def render(template, context):
    def sub(m):
        key = m.group(1)
        return str(context[key]) if key in context else m.group(0)
    return TOKEN_RE.sub(sub, template).strip()


def preamble(spec, rows, keys):
    name = (spec.get("identity") or {}).get("name", spec.get("asset_id"))
    used = []
    for r in rows:
        for s in r.get("used_in") or []:
            if s not in used:
                used.append(s)
    lines = [
        "> 本文件由 build_asset_prompts.py 按 "
        "references/asset-prompt-templates/ 的模板机械派生。形制以设计卡为唯一"
        "依据；有疑回资产设计，不私自改。",
        f"> - 类别：{spec.get('kind')}",
        "> - 成品落点：",
    ]
    for r in rows:
        lines.append(f">   - `{r.get('target_path')}`")
    lines.append(f"> - 用于镜：{', '.join(used) or '—'}")
    lines.append("> - 垫图清单：")
    if keys:
        for k in keys:
            lines.append(f">   - Style Key: `{k}`")
    else:
        lines.append(">   - 03-style/keys/ 下暂无样板图，先过 [9] 风格精冻")
    return lines


def joined_forbidden(forbidden):
    return " / ".join(forbidden) if forbidden else "—"


def negative_block(spec, style_spec=None):
    """Card negatives not already merged into global_negative (dedup).

    global_negative merges style-spec negatives AND every card negative, so
    by default nothing is repeated; a card item survives only when absent
    from the merged global set.
    """
    neg = (spec.get("acceptance") or {}).get("negative") or []
    already = set(_global_negative_items(style_spec))
    # Every card negative is itself merged into global_negative.
    already |= {str(x).strip() for x in neg}
    lines = [f"- {x}" for x in neg if str(x).strip() not in already]
    return "\n".join(lines) if lines else "- （无额外）"


def _global_negative_items(style_spec):
    if not style_spec:
        return []
    items = [str(x).strip() for x in style_spec.get("negative", [])]
    items += [str(x).strip()
              for x in (style_spec.get("medium") or {}).get("not", [])]
    fl = (style_spec.get("line") or {}).get("forbidden")
    if fl:
        items.append(str(fl).strip())
    return items


def numbered_views(cells):
    """Numbered per-view block: Chinese panel label + view + must_see.

    serves_shots stays out — it is machine binding metadata, not image content.
    """
    lines = []
    for i, c in enumerate(cells, 1):
        pos = c.get("position")
        if pos == "single":
            line = f"画面：{c['view']}"
        else:
            label = POS_CN.get(pos, pos)
            line = f"{i}. {label}视图：{c['view']}"
        if c.get("must_see"):
            line += f"；画面须见：{c['must_see']}"
        lines.append(line)
    return "\n".join(lines)


# ------------------------------------------------------------ character

def character_context(spec, sheet, style_spec):
    idn = spec.get("identity") or {}
    is_main = sheet.get("sheet_id") == "main"

    if is_main:
        state_phrase = "默认定妆"
        first_article = ("- 角色首件/身份根：小批量 4 张选身份与四格一致性最好的 "
                         "1 张，用户批准后定名。")
        variant_note, dependency = "", ""
    else:
        state_phrase = f"{sheet.get('state', '')}状态"
        first_article = ("- 状态变体：垫已批 main sheet 生成，只改状态差异、身份五官"
                         "不变；main 未 approved 拒绝投产。")
        variant_note = (f"- 变体差异：{sheet['note']}" if sheet.get("note") else "")
        main_t = next((s.get("target_path") for s in spec.get("sheets") or []
                       if s.get("sheet_id") == "main"), None)
        dependency = (f"- 投产依赖（depends_on）：`{main_t}`" if main_t else "")

    return {
        "name": idn.get("name"),
        "asset_id": spec.get("asset_id"),
        "sheet_id": sheet.get("sheet_id"),
        "state_phrase": state_phrase,
        "first_article_line": first_article,
        "visual_style": compose_style(style_spec, "character"),
        "identity_line": (
            f"{idn.get('name')}，{idn.get('age')} 岁{idn.get('sex')}；"
            f"{idn.get('station')}；{idn.get('period_region')}；{idn.get('health')}"),
        "color_anchors": character_colors(spec),
        "materials": character_materials(spec),
        "fixed_structure": character_structure(spec),
        "face_block": character_face_block(spec),
        "shape_block": character_shape_block(spec),
        "hands_feet_block": character_hands_feet_block(spec),
        "hair_block": character_hair_block(spec),
        "costume_detail_block": character_costume_detail_block(spec),
        "global_negative": global_negative(spec, style_spec),
        "variant_note": variant_note,
        "dependency_line": dependency,
        "forbidden": "",  # filled below so it never blocks template render
    }


def character_colors(spec):
    hair = spec.get("hair") or {}
    skin = spec.get("skin") or {}
    lines = [f"- 发色：{hair.get('color_hex')}"]
    skin_line = f"- 肤色：{skin.get('color_hex')}"
    if skin.get("tone_note"):
        skin_line += f"（{skin['tone_note']}）"
    lines.append(skin_line)
    for c in spec.get("costume") or []:
        lines.append(f"- {c.get('garment')}（{c.get('layer')}）："
                     f"{c.get('color_hex')}")
    for o in hair.get("ornaments") or []:
        if o.get("color_hex"):
            lines.append(f"- {o.get('item')}：{o.get('color_hex')}")
    return "\n".join(lines)


def character_materials(spec):
    return "\n".join(f"- {c.get('garment')}：{c.get('material')}"
                     for c in spec.get("costume") or [])


def character_structure(spec):
    hair = spec.get("hair") or {}
    face = spec.get("head_face") or {}
    stature = spec.get("stature") or {}
    proportions = spec.get("proportions") or []
    lines = ["- 发式：" + str(hair.get("style"))]
    ornaments = hair.get("ornaments") or []
    if ornaments:
        lines.append("- 头饰：")
        for o in ornaments:
            line = (f"  - {o.get('item')}（{o.get('worn_position')}）："
                    f"{o.get('description')}")
            if o.get("prop_ref"):
                line += f"；另有独立道具 {o['prop_ref']}"
            lines.append(line)
    lines.append("- 五官锚点：")
    lines.append(f"  - 眉：{face.get('brows')}")
    lines.append(f"  - 眼：{face.get('eyes')}")
    for mk in face.get("distinguishing_marks") or []:
        lines.append(f"  - {mk.get('mark')} @ {mk.get('location')}")
    lines.append(
        f"- 体态：头身比 {proportions.get('head_body_ratio')}；"
        f"肩宽 {proportions.get('shoulder_head_widths')} 头宽；"
        f"{stature.get('posture')}")
    return "\n".join(lines)


def character_face_block(spec):
    """Face morphology: face shape + every feature + facial proportions.

    These fields were required in the card but never reached the image; now
    they are injected so the same face holds across shots.
    """
    face = spec.get("head_face") or {}
    fr = (spec.get("proportions") or {}).get("face_ratio") or {}
    lines = ["- 脸型轮廓：" + str(face.get("face_shape"))]
    lines.append(f"- 额头：{face.get('forehead')}")
    lines.append(f"- 鼻：{face.get('nose')}")
    lines.append(f"- 唇与嘴角：{face.get('mouth')}")
    lines.append(f"- 面颊/颧骨：{face.get('cheeks')}")
    lines.append(f"- 下巴：{face.get('chin')}")
    lines.append(f"- 耳：{face.get('ears')}")
    lines.append(f"- 三庭比例：{fr.get('three_courts')}")
    lines.append(f"- 五眼比例（眼距）：{fr.get('five_eyes')}")
    return "\n".join(lines)


def character_shape_block(spec):
    """Build / shoulders / waist-hips / visual weight (body silhouette)."""
    st = spec.get("stature") or {}
    return "\n".join([
        "- 体型：" + str(st.get("build")),
        f"- 肩：{st.get('shoulders')}",
        f"- 腰臀：{st.get('waist_hips')}",
        f"- 画面分量感：{st.get('visual_weight')}",
    ])


def character_hands_feet_block(spec):
    hf = spec.get("hands_feet") or {}
    return "\n".join([
        "- 手：" + str(hf.get("hands")),
        f"- 足：{hf.get('feet')}",
    ])


def character_hair_block(spec):
    hair = spec.get("hair") or {}
    return "\n".join([
        "- 发际线：" + str(hair.get("hairline")),
        f"- 发质：{hair.get('texture')}",
    ])


def character_costume_detail_block(spec):
    """Pattern / cut / fastening / condition per garment."""
    lines = []
    for c in spec.get("costume") or []:
        lines.append(
            f"- {c.get('garment')}：剪裁 {c.get('cut')}；纹样 {c.get('pattern')}；"
            f"系束 {c.get('fastening')}；新旧 {c.get('condition')}")
    return "\n".join(lines) or "- （无）"


def global_negative(spec, style_spec):
    """Merge style-spec global negatives with the card negatives (dedup)."""
    lines = []
    seen = set()

    def add(text):
        for raw in text or []:
            v = (raw or "").strip()
            if v and v not in seen:
                seen.add(v)
                lines.append(f"- {v}")

    add(style_spec.get("negative"))
    add((style_spec.get("medium") or {}).get("not"))
    forbidden_line = (style_spec.get("line") or {}).get("forbidden")
    if forbidden_line:
        add([forbidden_line])
    add((spec.get("acceptance") or {}).get("negative"))
    return "\n".join(lines) or "- （无）"


# ---------------------------------------------------------------- prop

def prop_context(spec, style_spec):
    idn = spec.get("identity") or {}
    grid = (spec.get("presentation") or {}).get("grid") or {}
    cells = grid.get("cells") or []
    is_single = len(cells) == 1 and cells[0].get("position") == "single"
    layout = "single" if is_single else "2x2"
    layout_phrase = "一张完整单图" if is_single else "一组2×2四宫格"

    return {
        "name": idn.get("name"),
        "asset_id": spec.get("asset_id"),
        "layout_phrase": layout_phrase,
        "identity_line": (
            f"类别 {idn.get('category')}；时代 {idn.get('period')}；"
            f"用途 {str(idn.get('use')).rstrip('。.；;')}；使用者 "
            f"{', '.join(idn.get('used_by') or []) or '—'}"),
        "visual_style": compose_style(style_spec, "prop"),
        "scale_block": prop_scale(spec),
        "color_anchors": prop_color_anchors(spec),
        "materials": prop_materials(spec),
        "fixed_structure": prop_structure(spec),
        "decoration_block": prop_decoration(spec),
        "age_block": prop_age(spec),
        "weight_impression": spec.get("weight_impression", "—"),
        "layout_instruction": prop_layout(spec.get("presentation") or {}, layout),
        "view_blocks": numbered_views(cells),
        "negative": negative_block(spec),
        "forbidden": "",
    }


def prop_scale(spec):
    dim = spec.get("dimensions") or {}
    size = dim.get("size") or {}
    return "\n".join([
        f"- 尺寸：长 {size.get('length')}｜宽 {size.get('width')}｜"
        f"高 {size.get('height')}",
        f"- 尺度锚：{dim.get('scale_reference')}",
        f"- 部件比例：{dim.get('part_ratios', '—')}",
    ])


def prop_color_anchors(spec):
    return "\n".join(f"- {m.get('part')}：{m.get('color_hex')}"
                     for m in spec.get("materials") or [])


def prop_materials(spec):
    return "\n".join(
        f"- {m.get('part')}：{m.get('material')}；表面 {m.get('finish')}；"
        f"织理 {m.get('texture')}" for m in spec.get("materials") or [])


def prop_structure(spec):
    return "\n".join(
        f"- {p.get('part')}（×{p.get('count')}，{p.get('position')}）："
        f"{p.get('shape')}；连接：{p.get('connection', '—')}"
        for p in spec.get("parts") or [])


def prop_decoration(spec):
    d = spec.get("decoration") or {}
    motifs = d.get("motifs") or []
    return "\n".join([
        "- 纹样：" + ("、".join(motifs) if motifs else "无"),
        f"- 分布：{d.get('layout', '—')}",
        f"- 工艺：{d.get('technique', '—')}",
        f"- 对称：{d.get('symmetry', '—')}"])


def prop_age(spec):
    age = spec.get("age") or {}
    lines = [f"- 成色：{age.get('condition')}", f"- 包浆：{age.get('patina', '—')}"]
    wears = age.get("wear_locations") or []
    if wears:
        lines.append("- 磨损定位：")
        lines += [f"  - {w.get('wear')} @ {w.get('location')}" for w in wears]
    return "\n".join(lines)


def prop_layout(pres, layout):
    bg = pres.get("background", "素净不抢眼的背景")
    light = pres.get("lighting", "均匀柔光，清楚呈现形制与材质")
    marker = "需要" if pres.get("scale_marker") else "不需要"
    if layout == "single":
        return ("- 画面为一张完整单图（single image），器物居中、无分隔线；"
                f"背景：{bg}；布光：{light}；尺度参照物：{marker}。画面内容：")
    return ("- 画面严格采用2×2四宫格均匀拼版（Four-grid split screen layout），"
            "由干净利落的分隔线划分为完全相等的 4 个视图，无重叠、无偏移；"
            "全部视图为同一器物，形制、材质、色彩完全一致；"
            f"背景：{bg}；布光：{light}；尺度参照物：{marker}。各视图内容：")


# ---------------------------------------------------------------- scene

def scene_context(spec, grid, style_spec):
    idn = spec.get("identity") or {}
    layout = grid.get("layout")
    layout_phrase = {"single": "一张完整场景单图", "2x2": "一组2×2四宫格场景",
                     "3x3": "一组3×3九宫格场景"}.get(layout, f"一组{layout}")
    return {
        "name": idn.get("name"),
        "asset_id": spec.get("asset_id"),
        "grid_id": grid.get("grid_id"),
        "layout_phrase": layout_phrase,
        "identity_line": (
            f"{idn.get('interior_exterior')}；{idn.get('time_of_day')}；"
            f"季候 {idn.get('season')}；天气 {idn.get('weather')}"),
        "visual_style": compose_style(style_spec, "scene"),
        "floor_plan": (spec.get("layout") or {}).get("floor_plan", "—"),
        "lighting_block": scene_lighting(spec),
        "color_anchors": scene_color_anchors(spec),
        "materials": scene_materials(spec),
        "furnishings_block": scene_furnishings(spec),
        "environment_block": (
            f"{spec.get('air', '—')}；地形植被："
            f"{spec.get('terrain_vegetation', '—')}"),
        "layout_instruction": scene_layout(layout),
        "continuity_line": (
            f"- 本张垫上一张宫格：`{grid['continuity_ref']}`"
            "（只借空间形制，不串内容）。"
            if grid.get("continuity_ref") else ""),
        "view_blocks": numbered_views(grid.get("cells") or []),
        "depth_block": scene_depth_block(spec),
        "occlusion_block": (spec.get("layout") or {}).get("occlusion", "—"),
        "global_negative": global_negative(spec, style_spec),
        "forbidden": "",
    }


def scene_depth_block(spec):
    """Depth layers along the viewing axis (previously never rendered)."""
    lines = []
    for d in (spec.get("layout") or {}).get("depth_layers") or []:
        lines.append(f"- {d.get('layer')}：{d.get('contents')}")
    return "\n".join(lines) or "- （无）"


def scene_color_anchors(spec):
    lines = [f"- {p.get('name')}：{p.get('hex')}"
             for p in spec.get("palette") or []]
    for s in (spec.get("lighting") or {}).get("practical_sources") or []:
        lines.append(f"- {s.get('type')}（光源色）：{s.get('color_hex')}")
    return "\n".join(lines)


def scene_materials(spec):
    """Full per-element fields (color / condition / size / opening view)."""
    lines = []
    for a in spec.get("architecture") or []:
        lines.append(
            f"- {a.get('element')}：材质 {a.get('material')}；色 {a.get('color_hex')}；"
            f"尺度 {a.get('size_note')}；新旧 {a.get('condition')}；"
            f"开口景 {a.get('opening_view')}")
    return "\n".join(lines)


def scene_lighting(spec):
    lighting = spec.get("lighting") or {}
    lines = []
    for s in lighting.get("practical_sources") or []:
        lines.append(
            f"- {s.get('type')} @{s.get('position')}：色 {s.get('color_hex')}，"
            f"{s.get('intensity')}，焰心 ×{s.get('flame_count')}")
    lines += [
        f"- 环境光：{lighting.get('ambient')}",
        f"- 主辅比：{lighting.get('key_to_fill_ratio')}",
        f"- 整体曝光：{lighting.get('overall_exposure')}"]
    return "\n".join(lines)


def scene_furnishings(spec):
    furnishings = spec.get("furnishings") or []
    if not furnishings:
        return "无"
    lines = []
    for f in furnishings:
        line = f"- {f.get('prop_id')}：{f.get('position')}"
        if f.get("screen_share"):
            line += f"（画面占比 {f.get('screen_share')}）"
        lines.append(line)
    return "\n".join(lines)


def scene_layout(layout):
    if layout == "single":
        return ("- 画面为一张完整单图（single image），无分隔线、无拼版；"
                "同一空间内构图、构件、光源、色彩统一。画面内容：")
    n = 4 if layout == "2x2" else 9
    phrase_en = ("Four-grid split screen layout" if layout == "2x2"
                 else "3×3 multi-panel split screen layout")
    return (f"- 画面严格采用{layout}均匀拼版（{phrase_en}），由干净利落的"
            f"分隔线划分为完全相等的 {n} 个视图，无重叠、无偏移；所有视图"
            "为同一空间，建筑构件、光源、陈设与色彩完全一致。各视图内容：")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        die("usage: python scripts/build_asset_prompts.py <project-root>")
    main(os.path.abspath(sys.argv[1]))
