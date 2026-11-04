"""設定載入：hermes.yaml / policy.yaml / market.yaml / tools/*.yaml"""
from __future__ import annotations
import os, glob, yaml
from pathlib import Path

ROOT = Path(os.environ.get("HERMES_CONFIG_DIR", Path(__file__).resolve().parent.parent / "config"))


def _load(name: str) -> dict:
    with open(ROOT / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


CFG = _load("hermes.yaml")
POLICY = _load("policy.yaml")
MARKET = _load("market.yaml")

TOOLS: dict[str, dict] = {}
for path in sorted(glob.glob(str(ROOT / "tools" / "*.yaml"))):
    with open(path, encoding="utf-8") as f:
        for t in (yaml.safe_load(f) or {}).get("tools", []):
            TOOLS[t["name"]] = t


def ha_token() -> str:
    tok = os.environ.get(CFG["ha"].get("token_env", "HERMES_HA_TOKEN"), "")
    if not tok:
        raise RuntimeError("HERMES_HA_TOKEN 未設定（HA 長效存取權杖）")
    return tok


def compact_tool_schema() -> str:
    """精簡 schema（名稱＋參數＋一行描述），約 1.1k tokens，注入 system prompt。"""
    lines = []
    for name, t in TOOLS.items():
        if t.get("internal"):
            continue
        ps = []
        for k, v in (t.get("params") or {}).items():
            spec = v.get("type", "string")
            if "enum" in v:
                spec += "[" + "|".join(map(str, v["enum"])) + "]"
            if "min" in v or "max" in v:
                spec += f"({v.get('min','')}..{v.get('max','')})"
            ps.append(f"{k}:{spec}")
        lines.append(f"- {name}({', '.join(ps)}) — {t['desc']}")
    return "\n".join(lines)
