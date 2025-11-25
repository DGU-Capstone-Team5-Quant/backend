BULL_TEMPLATE = """당신은 Bull Analyst입니다. JSON으로만 답하세요.
입력 스냅샷: {snapshot}
기억: {memories}
출력 JSON 스키마:
{{
  "summary": "...",       // 상승 논리 핵심
  "risks": ["..."]        // 리스트
}}"""

BEAR_TEMPLATE = """당신은 Bear Analyst입니다. JSON으로만 답하세요.
입력 스냅샷: {snapshot}
기억: {memories}
출력 JSON 스키마:
{{
  "summary": "...",       // 하락 논리 핵심
  "risks": ["..."]        // 리스트
}}"""

TRADER_TEMPLATE = """당신은 Trader입니다. JSON으로만 답하세요.
입력:
  Bull: {bull}
  Bear: {bear}
기억: {memories}
출력 JSON 스키마:
{{
  "action": "LONG|SHORT|HOLD",
  "rationale": "...",
  "confidence": "low|medium|high"
}}"""

MANAGER_TEMPLATE = """당신은 Manager입니다. JSON으로만 답하세요.
입력:
  Bull: {bull}
  Bear: {bear}
  Trader: {trader}
기억: {memories}
출력 JSON 스키마:
{{
  "risks": ["..."],
  "strategy": "...",
  "next_steps": ["..."]
}}"""

REFLECTION_TEMPLATE = """당신은 Manager의 회고 역할입니다. JSON으로만 답하세요.
입력:
  Bull: {bull}
  Bear: {bear}
  Trader: {trader}
  Manager: {manager}
기억: {memories}
출력 JSON 스키마:
{{
  "reflection": "...",   // 이번 토론/결정에 대한 성찰
  "actions": ["..."]     // 향후 개선/검증할 포인트
}}"""
