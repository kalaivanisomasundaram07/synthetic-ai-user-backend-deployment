"""
Decides which LLM provider/model to try, and in what order, based on what's
configured. Keeps the "Gemini primary, Ollama fallback" policy in one place
so llm_client.py stays a dumb executor.
"""
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class ModelCandidate:
    provider: str          # "gemini" | "ollama"
    model: str             # litellm-formatted model string
    api_base: str | None = None
    api_key: str | None = None


class ModelRouter:
    def __init__(self) -> None:
        self.settings = get_settings()

    def candidates(self) -> list[ModelCandidate]:
        """
        Returns an ordered list of models to attempt:
        Groq (primary, per this project's frontend/README) -> Gemini -> Ollama.
        Groq and Gemini are only attempted if their API key is configured;
        Ollama is always listed as a last-resort network attempt (llm_client
        fails fast and moves on if it's unreachable).
        """
        out: list[ModelCandidate] = []

        if self.settings.GROQ_API_KEY:
            out.append(
                ModelCandidate(
                    provider="groq",
                    model=self.settings.GROQ_MODEL,
                    api_key=self.settings.GROQ_API_KEY,
                )
            )

        if self.settings.GEMINI_API_KEY:
            out.append(
                ModelCandidate(
                    provider="gemini",
                    model=f"gemini/{self.settings.GEMINI_MODEL}",
                    api_key=self.settings.GEMINI_API_KEY,
                )
            )

        out.append(
            ModelCandidate(
                provider="ollama",
                model=self.settings.OLLAMA_MODEL,
                api_base=self.settings.OLLAMA_BASE_URL,
            )
        )
        return out

    def has_any_llm_configured(self) -> bool:
        """Ollama is listed unconditionally above, but that doesn't mean it's
        actually reachable. This flags whether we have a *real* configured
        provider (Groq or Gemini key present) vs. relying purely on a local
        Ollama that may or may not be running."""
        return bool(self.settings.GROQ_API_KEY or self.settings.GEMINI_API_KEY)
