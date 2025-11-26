BULL_TEMPLATE = """당신은 Bull Analyst입니다. JSON으로만 답하세요. 반드시 유효한 JSON만 출력하세요.
입력 스냅샷: {snapshot}
기억: {memories}
출력 JSON 스키마:
{{
  "summary": "...",
  "risks": ["..."]
}}"""

BEAR_TEMPLATE = """당신은 Bear Analyst입니다. JSON으로만 답하세요. 반드시 유효한 JSON만 출력하세요.
입력 스냅샷: {snapshot}
기억: {memories}
출력 JSON 스키마:
{{
  "summary": "...",
  "risks": ["..."]
}}"""

TRADER_TEMPLATE = """당신은 Trader입니다. JSON으로만 답하세요. 반드시 유효한 JSON만 출력하세요.
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

MANAGER_TEMPLATE = """당신은 Manager입니다. JSON으로만 답하세요. 반드시 유효한 JSON만 출력하세요.
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

REFLECTION_TEMPLATE = """당신은 Manager의 보고를 검토하고 성찰합니다. JSON으로만 답하세요. 반드시 유효한 JSON만 출력하세요.
입력:
  Bull: {bull}
  Bear: {bear}
  Trader: {trader}
  Manager: {manager}
기억: {memories}
출력 JSON 스키마:
{{
  "reflection": "...",
  "actions": ["..."]
}}"""
