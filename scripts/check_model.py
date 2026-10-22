"""Make one small live call to verify credentials, model access and schema support."""

import asyncio
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app.config import Settings  # noqa: E402
from app.llm import AgentError, GeminiModel  # noqa: E402


class ConnectionCheck(BaseModel):
    ready: bool


async def main():
    config = Settings.from_env()
    try:
        async with httpx.AsyncClient(verify=ssl.create_default_context()) as client:
            result = await GeminiModel(client, config).generate("Return ready=true.", {}, ConnectionCheck)
        print(f"Live Gemini schema check passed: {result.ready}; model: {config.model}")
    except AgentError as exc:
        print(f"{exc.code}: {exc.message}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    asyncio.run(main())
