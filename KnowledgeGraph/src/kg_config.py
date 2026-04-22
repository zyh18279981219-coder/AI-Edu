from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _pick_env(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return default


@dataclass
class KGConfig:
    project_root: Path
    kg_root: Path
    config_dir: Path
    course_profile_path: Path
    scripts_dir: Path
    data_dir: Path
    intermediate_dir: Path
    output_dir: Path
    backup_dir: Path
    third_party_dir: Path
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    neo4j_uri: str
    neo4_user: str
    neo4j_password: str

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> "KGConfig":
        root = project_root or Path(__file__).resolve().parents[2]
        load_dotenv(root / ".env", override=False)

        kg_root = root / "KnowledgeGraph"
        data_dir = kg_root / "data"

        return cls(
            project_root=root,
            kg_root=kg_root,
            config_dir=kg_root / "config",
            course_profile_path=kg_root / "config" / "course_profile.yaml",
            scripts_dir=kg_root / "unstructured_script",
            data_dir=data_dir,
            intermediate_dir=data_dir / "intermediate",
            output_dir=data_dir / "output",
            backup_dir=data_dir / "backup",
            third_party_dir=kg_root / "third_party",
            llm_api_key=_pick_env("LLM_API_KEY", "api_key"),
            llm_base_url=_pick_env("LLM_BASE_URL", "base_url"),
            llm_model=_pick_env("LLM_MODEL", "model_name"),
            neo4j_uri=_pick_env("NEO4J_URI"),
            neo4_user=_pick_env("NEO4_USER", "NEO4J_USER"),
            neo4j_password=_pick_env("NEO4J_PASSWORD"),
        )

    def ensure_directories(self) -> None:
        required_dirs = [
            self.kg_root,
            self.config_dir,
            self.data_dir,
            self.intermediate_dir,
            self.output_dir,
            self.backup_dir,
            self.third_party_dir,
        ]
        for path in required_dirs:
            path.mkdir(parents=True, exist_ok=True)

    def masked_dict(self) -> dict:
        masked_key = ""
        if self.llm_api_key:
            masked_key = (
                f"{self.llm_api_key[:6]}...{self.llm_api_key[-4:]}"
                if len(self.llm_api_key) >= 10
                else "***"
            )
        return {
            "project_root": str(self.project_root),
            "kg_root": str(self.kg_root),
            "config_dir": str(self.config_dir),
            "course_profile_path": str(self.course_profile_path),
            "scripts_dir": str(self.scripts_dir),
            "intermediate_dir": str(self.intermediate_dir),
            "output_dir": str(self.output_dir),
            "backup_dir": str(self.backup_dir),
            "third_party_dir": str(self.third_party_dir),
            "llm_base_url": self.llm_base_url,
            "llm_model": self.llm_model,
            "llm_api_key_masked": masked_key,
            "neo4j_uri": self.neo4j_uri,
            "neo4_user": self.neo4_user,
            "neo4j_password_set": bool(self.neo4j_password),
        }
