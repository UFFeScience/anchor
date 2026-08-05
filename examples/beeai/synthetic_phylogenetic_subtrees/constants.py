import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from beeai_framework.backend.chat import ChatModel


load_dotenv(Path(__file__).resolve().parents[3] / ".env")


DEFAULT_LLM = "ollama:granite3.3:8b"


# def _normalize_llm_name(value: str) -> str:
#     value = value.strip()
#     if ":" in value:
#         return value
#     if "/" in value:
#         return f"openai:{value}"
#     return value


# LLM = _normalize_llm_name(os.getenv("ANCHOR_LLM", DEFAULT_LLM))
LLM = os.getenv("ANCHOR_LLM", DEFAULT_LLM)


# def _tool_choice_support() -> set[str] | None:
#     value = os.getenv("ANCHOR_LLM_TOOL_CHOICE_SUPPORT")
#     if not value:
#         api_base = os.getenv("OPENAI_API_BASE", "")
#         model_name = os.getenv("ANCHOR_LLM", DEFAULT_LLM)
#         if (
#             "router.huggingface.co" in api_base
#             or "novita" in model_name
#             or "gpt-oss" in model_name
#         ):
#             return {"none", "auto", "single"}
#         return None
#     return {item.strip() for item in value.split(",") if item.strip()}


# def create_llm(name: str | None = None) -> Any:
#     resolved_name = _normalize_llm_name(name or os.getenv("ANCHOR_LLM", DEFAULT_LLM))
#     kwargs: dict[str, Any] = {}
#     tool_choice_support = _tool_choice_support()
#     if tool_choice_support is not None:
#         kwargs["tool_choice_support"] = tool_choice_support
#     return ChatModel.from_name(resolved_name, **kwargs)

def create_llm(name: str | None = None) -> Any:
    resolved_name = name or os.getenv("ANCHOR_LLM", DEFAULT_LLM)
    return ChatModel.from_name(resolved_name)
