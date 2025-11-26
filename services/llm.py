from __future__ import annotations

from typing import Any, Dict, Optional


class BaseLLMClient:
    async def generate(self, prompt: str, *, seed: Optional[int] = None) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class StubLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, *, seed: Optional[int] = None) -> str:
        # Return valid JSON so downstream parsing succeeds deterministically in stub mode.
        return (
            '{'
            f'"stub": true, "seed": {seed if seed is not None else "null"}, '
            f'"text": {repr(prompt[:160])}'
            '}'
        )


class OllamaLLMClient(BaseLLMClient):
    def __init__(
        self,
        model_name: str = "llama3.1:8b",
        temperature: float = 0.3,
        num_predict: int = 512,
        base_url: str = "http://localhost:11434",
    ):
        import ollama

        self.client = ollama.AsyncClient(host=base_url)
        self.model_name = model_name
        self.temperature = temperature
        self.num_predict = num_predict

    async def generate(self, prompt: str, *, seed: Optional[int] = None) -> str:
        options = {
            "temperature": self.temperature,
            "num_predict": self.num_predict,
        }
        if seed is not None:
            options["seed"] = seed

        response = await self.client.generate(
            model=self.model_name,
            prompt=prompt,
            format="json",  # JSON mode로 강제 - 구조화된 출력 보장
            options=options,
        )
        return response.get("response", "")


def build_llm(
    model_name: str = "llama3.1:8b",
    temperature: float = 0.3,
    max_tokens: int = 512,
    base_url: str = "http://localhost:11434",
) -> BaseLLMClient:
    try:
        return OllamaLLMClient(
            model_name=model_name,
            temperature=temperature,
            num_predict=max_tokens,
            base_url=base_url,
        )
    except Exception:
        # Ollama 연결 실패 시 스텁으로 백업
        return StubLLMClient()


class BaseEmbeddingClient:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - interface
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:  # pragma: no cover - interface
        raise NotImplementedError


class StubEmbeddingClient(BaseEmbeddingClient):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))]


def build_embeddings(mode: str = "stub") -> BaseEmbeddingClient:
    # 현재는 stub 임베딩만 지원
    return StubEmbeddingClient()
