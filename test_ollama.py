"""Simple script to test Ollama connection"""
import asyncio
from services.llm import build_llm

async def test_ollama():
    print("Testing Ollama connection...")

    # Build LLM client (same as in your code)
    llm = build_llm(
        model_name="llama3.1:8b",
        temperature=0.3,
        max_tokens=512,
        base_url="http://localhost:11434"
    )

    print(f"LLM Client Type: {type(llm).__name__}")

    # Test generation
    test_prompt = """You are a trader. Respond in JSON only.
    Input: Buy signal detected
    Output JSON schema:
    {
      "action": "BUY_100",
      "rationale": "test",
      "confidence": "high"
    }"""

    print("\nSending test prompt to Ollama...")
    response = await llm.generate(test_prompt, seed=0)

    print(f"\nResponse received:")
    print(response[:500])

    print("\n✓ Ollama connection successful!")
    return True

if __name__ == "__main__":
    asyncio.run(test_ollama())
