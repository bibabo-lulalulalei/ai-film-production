# -*- coding: utf-8 -*-
"""Shared layout constants and IO helpers for ai-film-production.

Everything is relative to the project root passed by the caller; the canonical
layout is documented in SKILL.md. Model-specific limits live in the target
model's profile under references/models/<model>/profile.json — never hardcode
them in callers.
"""
import glob
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---- project layout ----
DIR_CHARTER = "00-charter"
DIR_NOVEL = "01-novel"
DIR_SCREENPLAY = "02-screenplay"
DIR_STYLE = "03-style"
DIR_WORLD = "04-world"
DIR_SHOTS = "05-shots"
DIR_BOM = "06-bom"
DIR_ASSETS = "07-assets"
DIR_PROMPTS = "08-prompts"
DIR_TAKES = "09-takes"

SOUL_CHECKS = os.path.join(DIR_NOVEL, "soul-checks.json")
STYLE_DIRECTION = os.path.join(DIR_STYLE, "style-direction.md")
STYLE_CHECKS = os.path.join(DIR_STYLE, "style-checks.json")
STYLE_BIBLE = os.path.join(DIR_STYLE, "style-bible.md")
KEYS_DIR = os.path.join(DIR_STYLE, "keys")
SPECS_DIR = os.path.join(DIR_BOM, "asset-specs")
BOM_PATH = os.path.join(DIR_BOM, "bom.json")

# Beat -> duration tiers. This is pipeline policy (model-agnostic, category D);
# the valid interval is then intersected with the profile's [min, max] envelope,
# so a model with a shorter ceiling needs no special-casing.
DURATION_TIERS = {
    "standard": (8, 12),    # default narrative beat
    "motion": (12, 15),     # continuous movement / establishing shots
    "dialogue": (4, 10),    # Ref2VA multi-person dialogue, cut per turn
}

# Grid layout -> legal cell positions (mirrors scene-spec grids[].layout).
GRID_POSITIONS = {
    "single": ["single"],
    "2x2": ["tl", "tr", "bl", "br"],
    "3x3": ["tl", "tc", "tr", "ml", "c", "mr", "bl", "bc", "br"],
}
# Prop grids allow a single-image mode or a four-view grid.
PROP_POSITIONS = ["single", "tl", "tr", "bl", "br"]

RETENTION = ("fully_preserved", "partially_preserved",
             "attribute_transfer", "weak_reference")


def spec_path(asset_id):
    return os.path.join(SPECS_DIR, f"{asset_id}.json")


# ---- light schema check (shared; no external deps) ----

def validate_like(instance, schema, path="$"):
    """Minimal structural validation used by skill-level gates.

    Supports the keywords our self-describing schemas use: required /
    properties / items / enum / type. Domain rules live in each gate.
    (The richer validator used for project cards lives in lint_cards.)
    """
    import re

    out = []
    if instance is None:
        types = schema.get("type")
        types = types if isinstance(types, list) else [types]
        if "null" not in types:
            out.append(f"{path} 不应为 null")
        return out

    if "enum" in schema and instance not in schema["enum"]:
        out.append(f"{path} 取值非法: {instance!r}（允许 {schema['enum']}）")
    if isinstance(instance, str) and "pattern" in schema \
            and re.search(schema["pattern"], instance) is None:
        out.append(f"{path} 不符合格式 {schema['pattern']}: {instance!r}")

    types = schema.get("type")
    types = types if isinstance(types, list) else [types]
    if "object" in types and isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance or is_unset(instance[key]):
                out.append(f"{path}.{key} 缺失/未填")
        for key, sub in (schema.get("properties") or {}).items():
            if key in instance:
                out += validate_like(instance[key], sub, f"{path}.{key}")
    if "array" in types and isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            out.append(f"{path} 元素数 < minItems {schema['minItems']}")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, value in enumerate(instance):
                out += validate_like(value, items, f"{path}[{i}]")
    return out


def die(msg, code=1):
    print(f"ERROR: {msg}")
    sys.exit(code)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(obj, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def write_text(path, text):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def flatten(obj):
    """Serialize a JSON object to a searchable string (for substring rules)."""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(obj)


# ---- shot cards ----

def load_cards(root):
    paths = glob.glob(os.path.join(root, DIR_SHOTS, "*.json"))
    cards = [load_json(p) for p in paths]
    cards.sort(key=lambda c: (c.get("seq", 0), c.get("shot_id", "")))
    return cards


def card_map(cards):
    return {c.get("shot_id"): c for c in cards}


def exists(root, rel):
    return bool(rel) and os.path.exists(os.path.join(root, rel))


# Dash placeholders that used to masquerade as real values ("—"); a genuine
# "not applicable" must be the explicit NOT_APPLICABLE token instead.
DASH_PLACEHOLDERS = ("—", "–", "--")
NOT_APPLICABLE = "N/A"


def is_unset(value):
    if value is None:
        return True
    if isinstance(value, str):
        v = value.strip()
        return (not v or v.upper() == "UNSET" or v in DASH_PLACEHOLDERS)
    return False


# ---- model profiles ----

def skill_root():
    """Directory of this skill (scripts/ lives directly under it)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def target_model(root, required=True):
    """Read the model locked in 00-charter/charter.md.

    Plain line parsing: a ``目标模型`` or ``target model``/``target_model`` key
    followed by ``:``/``：``, e.g. ``目标模型：H3``.

    No model is ever *assumed*: a missing charter or an unparseable line is a
    hard failure (required=True) or None (required=False, used by G02 which
    reports one FAIL). This replaced the old silent default of "h3", which
    violated the "never invent facts" rule.
    """
    charter = os.path.join(root, DIR_CHARTER, "charter.md")
    if not os.path.exists(charter):
        if required:
            die(f"未找到 {DIR_CHARTER}/charter.md；目标模型不能默认假定，需在 "
                "[1] 立项、[2] 用户选定后写明「目标模型：…」")
        return None
    with open(charter, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line[:1] in ("-", "*"):  # tolerate a markdown list marker
                line = line[1:].strip()
            for sep in (":", "："):
                key, found, value = line.partition(sep)
                if not found:
                    continue
                key_norm = " ".join(key.strip().lower().replace("_", " ").split())
                if key_norm in ("目标模型", "target model") and value.strip():
                    name = value.strip().split()[0].strip("`'\"")
                    if name in ("待", "TBD", "TBA", "PENDING", "?"):
                        if not required:
                            return None
                        die("charter 的目标模型尚未锁定（占位「%s」）。"
                            "需在 [2] 风格定向产出跨模型矩阵、用户选定组合后回写锁定。"
                            % value.strip())
                    return name.lower()
    # No "目标模型" line found: not a default model — fail or let G02 report.
    if required:
        die(f"{DIR_CHARTER}/charter.md 中未找到「目标模型：…」行；不能默认假定模型，"
            "需写明目标模型。")
    return None


def load_profile(root):
    """Load the charter's target-model profile; die listing available models."""
    name = target_model(root)
    models_dir = os.path.join(skill_root(), "references", "models")
    path = os.path.join(models_dir, name, "profile.json")
    if not os.path.exists(path):
        available = []
        if os.path.isdir(models_dir):
            available = sorted(d for d in os.listdir(models_dir)
                               if os.path.exists(os.path.join(models_dir, d, "profile.json")))
        die(f"目标模型「{name}」没有 profile（{path}）。"
            f"当前可用模型: {', '.join(available) or '无'}；"
            f"按 references/models/README.md 的适配清单新增。")
    profile = load_json(path)
    profile["_dir"] = os.path.join(models_dir, name)
    return profile


def load_all_profiles():
    """Load every registered model profile (references/models/*/profile.json).

    Used by the style-direction cross-model matrix: candidates are matched
    against the style capabilities of ALL models, not the charter's target.
    Returns a list sorted by model name; each profile has ``_dir`` injected.
    """
    models_dir = os.path.join(skill_root(), "references", "models")
    profiles = []
    if os.path.isdir(models_dir):
        for name in sorted(os.listdir(models_dir)):
            path = os.path.join(models_dir, name, "profile.json")
            if os.path.exists(path):
                profile = load_json(path)
                profile["_dir"] = os.path.join(models_dir, name)
                profiles.append(profile)
    return profiles
