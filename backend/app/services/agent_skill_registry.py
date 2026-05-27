from __future__ import annotations

from pathlib import Path
import yaml

_SKILLS_PATH = Path(__file__).resolve().parent.parent / "config" / "agent_skills.yaml"


def load_skill_registry() -> dict[str, dict]:
    if not _SKILLS_PATH.exists():
        return {}
    payload = yaml.safe_load(_SKILLS_PATH.read_text(encoding="utf-8")) or {}
    skills = payload.get("skills") or []
    return {str(s.get("id")): s for s in skills if s.get("id")}


def get_skill_definition(skill_id: str) -> dict | None:
    return load_skill_registry().get(skill_id)
