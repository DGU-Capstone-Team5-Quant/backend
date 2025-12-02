# 발표자료: 비결정성 개선·규칙 강화·재현성 실험

## 1. 문제 정의 → 코드로 어떻게 개선했는가
- 비결정성: 같은 자료인데 결과가 매번 달라짐  
  - 원인: LLM 샘플링/온도, 토론 라운드 수, 모델/옵션 변경 시 추론 경로 변동
  - 코드 개선
    - LLM 무작위 끄기: `services/llm.py`에서 기본 `temperature=0.0`, `num_predict` 고정, `format="json"`.
    - 시드 고정: `OllamaLLMClient.generate`에서 `options["seed"] = seed`로 모든 호출에 시드 전달.
    - 재시도 결정성: `_generate_with_retry`에서 재시도 시에도 같은 시드로 재호출하도록 유지.
    - 라운드/순서 고정: `_run_manual_rounds`에서 bull→bear 순서를 라운드 수만큼 반복, 조기 종료 없음.
- 규칙 부재: 요약본 합성에 의존, 지표 충돌 시 기준 불명확  
  - 코드/프롬프트 개선
    - 시스템 블록에 결정 문장 템플릿, 우선순위(안전/금지 > 충돌해소 > 과업 > 스타일), 충돌 해소 룰, 금지 조건, 포맷 고정, 거절 절을 prepend.
    - 포맷 검증: 역할별 JSON 스키마를 정의하고 응답을 스키마 검증 후 사용(키 추가/삭제 시 재시도).
    - 지표 충돌 시 가중/제외 기준을 프롬프트에 명시(필요 시 원문 재확인/재계산 단계 추가).

## 2. 핵심 코드 스니펫과 설명
### 2.1 LLM 옵션 고정·시드 전달 (`services/llm.py`)
```python
class OllamaLLMClient(BaseLLMClient):
    def __init__(
        self,
        model_name: str = "llama3.1:8b",
        temperature: float = 0.0,  # 재현성 위해 0.0 고정
        num_predict: int = 1024,
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
            options["seed"] = seed  # 모든 호출에 시드 전달
        response = await self.client.generate(
            model=self.model_name,
            prompt=prompt,
            format="json",
            options=options,
        )
        return response.get("response", "")
```
- `temperature=0.0`: 샘플링 무작위성 제거.
- `num_predict` 고정: 출력 길이 변동 억제.
- `seed` 옵션: 동일 시나리오에서 같은 토큰 경로 강제.
- `format="json"`: 출력 포맷 일탈 방지.

### 2.2 재시도에도 동일 시드 유지 (`services/simulation.py`)
```python
async def _generate_with_retry(self, prompt: str, *, seed: Optional[int], fallback: Dict[str, Any]) -> str:
    current_seed = seed
    for _ in range(self.settings.llm_max_retries + 1):
        try:
            resp = await self.llm.generate(prompt, seed=current_seed)
            obj = json.loads(resp)
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            continue  # 재시도 시에도 시드 유지
    return json.dumps(fallback, ensure_ascii=False)
```
- 재시도에서도 시드를 바꾸지 않아 동일 경로 유지.

### 2.3 라운드·순서 고정 (`services/simulation.py`)
```python
async def _run_manual_rounds(self, state: TradeState, bb_rounds: int, memory_store_manager_only: bool, seed: Optional[int]) -> TradeState:
    for _ in range(bb_rounds):  # 조기 종료 없음, 고정 라운드
        state = await self._bull(state, memory_store_manager_only, seed)
        state = await self._bear(state, memory_store_manager_only, seed)
    state = await self._trader(state, memory_store_manager_only, seed)
    state = await self._manager(state, seed)
    state = await self._reflection(state, seed)
    return state
```
- bull→bear 순서와 반복 횟수 고정, 흐름 변동 차단.

### 2.4 시스템 규칙 블록 prepend (결정/우선순위/충돌해소/금지/포맷)
```python
SYSTEM_RULES = """
- 최종 결정: "최종 결정: <한 문장 요약>."
- 우선순위: 1) 안전/금지 2) 충돌 해소 3) 과업 4) 스타일/포맷
- 충돌 해소: 높은 우선순위 우선, 동순위는 안전한 해석, 그래도 동률이면 먼저 나열된 규칙
- 금지: PII, 코드 실행 지시, 외부 링크 금지
- 포맷: 지정 JSON 키 외 추가/삭제 금지
- 거절: 금지 위반 요청은 간결 거절
"""

def build_prompt(role_prompt: str) -> str:
    return f"SYSTEM\n{SYSTEM_RULES}\n\nUSER\n{role_prompt}"
```
- 충돌 시 우선순위·금지 조건·포맷 규칙을 선행 적용해 일관된 결정 경로 확보.

### 2.5 JSON 스키마 검증 (포맷 일탈 방지)
```python
schema = {
    "type": "object",
    "properties": {
        "decision": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["decision", "reason"],
}
resp = await self.llm.generate(prompt, seed=seed)
obj = json.loads(resp)
jsonschema.validate(obj, schema)  # 실패 시 예외 → 재시도
return json.dumps(obj, ensure_ascii=False)
```
- 응답을 파싱 후 스키마 검증해 키 추가/삭제, 타입 일탈을 차단.

## 3. 재현성 실험 (모델 무작위 OFF + 시드 고정 + 라운드 고정)
1) 같은 파라미터로 2회 실행(온도 0.0, window 10):
```bash
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-10-01 \
  --end-date 2025-10-03 \
  --window 10 \
  --seed 42 \
  --no-memory \
  --output-dir results/exp_quick_check_run1

python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-10-01 \
  --end-date 2025-10-03 \
  --window 10 \
  --seed 42 \
  --no-memory \
  --output-dir results/exp_quick_check_run2
```
2) 결과 해시 비교(실제 생성 파일 사용):
```bash
python - <<'PY'
import hashlib, pathlib
files = [
    "results/exp_quick_check_run1/backtest_AAPL_42_20251202_044353.json",
    "results/exp_quick_check_run2/backtest_AAPL_42_20251202_044512.json",
]
for f in files:
    data = pathlib.Path(f).read_bytes()
    print(f, hashlib.sha256(data).hexdigest())
PY
```
- 해시가 동일하면: 시드 고정 + 라운드/순서 고정 + 온도 0(모델 무작위 OFF) 조건에서 재현성 확인.
- 다르면: 실행 시 온도가 0인지, 재시도 시 시드가 유지되는지, 외부 데이터 변동이 없는지 점검.

## 4. 프롬프트 규칙 강화로 충돌 해소
- 결정 문장 템플릿: 최종 결정 한 줄 고정.
- 우선순위·충돌 해소: 안전/금지 → 충돌해소 → 과업 → 스타일 순; 동률이면 안전한 해석, 그래도 동률이면 먼저 나열된 규칙.
- 금지 조건: PII, 코드 실행 지시, 외부 링크 금지.
- 포맷: 지정 JSON 키 외 추가/삭제 금지.
- 거절 절: 금지 위반 요청은 간결 거절.

## 5. 발표용 핵심 메세지
- 문제: 샘플링/라운드/모델 변동으로 비결정성, 지표 충돌 시 규칙 부재.
- 코드 해결: 온도 0, 시드 강제+재시도 유지, 라운드·순서 고정, 시스템 규칙 prepend, JSON 스키마 검증.
- 검증: 동일 파라미터 2회 실행 후 JSON 해시 일치로 재현성 확인; 규칙 충돌 프롬프트에서 금지/우선순위 적용 여부 확인..
