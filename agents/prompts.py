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
  현재 포트폴리오: {portfolio}
기억: {memories}
출력 JSON 스키마:
{{
  "action": "BUY_25|BUY_50|BUY_100|SELL_25|SELL_50|SELL_100|HOLD",
  "rationale": "...",
  "confidence": "low|medium|high"
}}
참고:
- BUY_X: 현재 잔고(cash)의 X%를 사용해 추가 매수
- SELL_X: 현재 보유 주식(position_shares)의 X%를 매도
- HOLD: 포지션 유지
- 현재 잔고가 부족하면 매수 불가, 보유 주식이 없으면 매도 불가"""

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
