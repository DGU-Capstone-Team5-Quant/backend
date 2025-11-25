from __future__ import annotations

from typing import Optional


class BaseLLMClient:
    async def generate(self, prompt: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class StubLLMClient(BaseLLMClient):
    async def generate(self, prompt: str) -> str:
        return f"[stubbed llm output]\n{prompt[:300]}..."


class GeminiLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    async def generate(self, prompt: str) -> str:
        # google-generativeai는 비동기 API가 없어 sync 호출을 래핑
        result = self.model.generate_content(prompt)
        return result.text if hasattr(result, "text") else str(result)


def build_llm(api_key: Optional[str], model_name: str = "gemini-2.0-flash") -> BaseLLMClient:
    if api_key:
        try:
            return GeminiLLMClient(api_key, model_name=model_name)
        except Exception:
            # API 키가 있어도 환경이 불안정할 경우 스텁으로 폴백
            return StubLLMClient()
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


def build_embeddings(api_key: Optional[str], mode: str = "stub") -> BaseEmbeddingClient:
    if mode == "stub":
        return StubEmbeddingClient()
    if api_key:
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)

            class _GeminiEmbedding(BaseEmbeddingClient):
                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    return [self.embed_query(t) for t in texts]

                def embed_query(self, text: str) -> list[float]:
                    result = genai.embed_content(model="text-embedding-004", content=text)
                    return result["embedding"]  # type: ignore[index]

            return _GeminiEmbedding()
        except Exception:
            return StubEmbeddingClient()
    return StubEmbeddingClient()
