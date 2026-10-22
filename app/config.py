"""Environment-based configuration; secrets never enter API responses."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False, default="")
    model: str = "gemini-3.5-flash-lite"
    output_dir: Path = ROOT / "outputs"
    agent_timeout: float = 240
    llm_timeout: float = 45
    llm_min_interval: float = 13

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env")
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
            raise ValueError("GEMINI_MODEL must be a model ID, not a URL")
        output = Path(os.getenv("AGENT_OUTPUT_DIR", "outputs"))
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            model=model,
            output_dir=output if output.is_absolute() else ROOT / output,
            agent_timeout=max(1, float(os.getenv("AGENT_TIMEOUT_SECONDS", "240"))),
            llm_timeout=max(1, float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))),
            llm_min_interval=max(0, float(os.getenv("LLM_MIN_INTERVAL_SECONDS", "13"))),
        )
