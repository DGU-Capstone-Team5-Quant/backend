# LLM Multi-Agent Debate Module (Deep Dive)

This deck explains the architecture, tech stack, and code that power the Bull/Bear/Trader/Manager/Reflection debate, assuming no prior context.

## 1) Tech Stack at a Glance
- API: FastAPI + Pydantic for request/response validation.
- LLM: Ollama (local) using JSON mode for structured outputs.
- Embeddings: Ollama `nomic-embed-text` to embed text for retrieval.
- Memory: Redis VectorStore (via langchain_redis) + custom scoring/rollup logic (`FinMemMemory`).
- Orchestration: Handwritten async sequence in `SimulationService` (plus a LangGraph design reference in `agents/graph.py`).
- Data: Market/news snapshots from `MarketDataLoader` (not shown here), results persisted to Postgres (`Simulation`, `AgentLog`).

## 2) End-to-End Flow (Request to JSON Decision)
```mermaid
flowchart TD
    Client -->|POST /api/run| FastAPI
    FastAPI --> SimulationService
    SimulationService -->|load| MarketDataLoader
    SimulationService -->|search| FinMemMemory
    SimulationService -->|debate| Ollama LLM
    SimulationService -->|store| Redis (memory)
    SimulationService -->|persist| Postgres
    SimulationService --> Response
```
- Input: ticker, window, optional news toggle, rounds, seed, memory usage flag.
- Output: structured JSON summary (decision/report/bull/bear/reflection/snapshot/meta) + simulation_id.

## 3) API Contract (FastAPI Layer)
```python
# routers/simulation.py (annotated)
@router.post("/run", response_model=SimulationResponse)
async def run_simulation(payload: SimulationRequest, service: SimulationService = Depends(get_service)):
    """Entry point: validate payload, delegate to SimulationService."""
    result = await service.run(
        ticker=payload.ticker,
        window=payload.window,
        include_news=payload.news,
        mode=payload.mode,
        interval=payload.interval,
        start_date=payload.start_date,
        end_date=payload.end_date,
        news_limit=payload.news_limit,
        news_page=payload.news_page,
        bb_rounds=payload.bb_rounds,
        memory_store_manager_only=payload.memory_store_manager_only,
        seed=payload.seed,
        use_memory=payload.use_memory,
    )
    return SimulationResponse(
        simulation_id=result.simulation_id,
        status="completed",
        summary=result.summary,
    )
```
- FastAPI validates request against `SimulationRequest`; response is always `SimulationResponse` with a structured summary.

## 4) Request/Response Schemas (what the API expects/returns)
```python
# routers/simulation.py (Pydantic models)
class SimulationRequest(BaseModel):
    ticker: str                     # required; symbol
    window: int = 200               # bars to load
    news: bool = True               # include news
    mode: str = "intraday"          # intraday or daily
    interval: str = "1h"            # candle interval
    start_date: datetime | None = None
    end_date: datetime | None = None
    news_limit: int = 5             # number of news items
    news_page: int = 0              # news page offset
    bb_rounds: int | None = None    # bull/bear debate rounds (fallback to config)
    memory_store_manager_only: bool | None = None  # if True, only manager/reflection persisted to LTM
    seed: int | None = None         # LLM seed for reproducibility
    use_memory: bool = True         # toggle retrieval-augmented prompting

class SimulationResponse(BaseModel):
    simulation_id: str              # UUID of this simulation
    status: str                     # e.g., "completed"
    summary: dict[str, Any] | None = None  # structured debate result

# nested shapes used inside summary
class AgentView(BaseModel):
    summary: str | None = None
    risks: list[str] = []

class TraderDecision(BaseModel):
    action: str                     # LONG | SHORT | HOLD
    rationale: str | None = None
    confidence: str | None = None   # low|medium|high

class ManagerReport(BaseModel):
    risks: list[str] = []
    strategy: str | None = None
    next_steps: list[str] = []

class Reflection(BaseModel):
    reflection: str | None = None
    actions: list[str] = []

class Snapshot(BaseModel):
    ticker: str
    window: int
    mode: str
    interval: str
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    latest: dict[str, Any]
    news: list[dict[str, Any]] | None = None

class SimulationSummary(BaseModel):
    decision: TraderDecision
    report: ManagerReport
    bull: AgentView
    bear: AgentView
    reflection: Reflection
    snapshot: Snapshot
    meta: dict[str, Any] | None = None  # seed, rounds, models, intervals, counts
```
- `summary` returned to clients follows `SimulationSummary` shape above.
- Defaults: `bb_rounds=None` uses the server's config; `use_memory=True` enables retrieval.

## 5) Debate Orchestration (SimulationService)
```python
# services/simulation.py (core loop, annotated)
async def _run_manual_rounds(self, state: TradeState, bb_rounds: int, memory_store_manager_only: bool, seed: Optional[int]) -> TradeState:
    for _ in range(bb_rounds):      # alternate bull/bear for the requested rounds
        state = await self._bull(state, memory_store_manager_only, seed)
    state = await self._bear(state, memory_store_manager_only, seed)
    state = await self._trader(state, memory_store_manager_only, seed)
    state = await self._manager(state, seed)
    state = await self._reflection(state, seed)
    return state
```
- State carries snapshot, retrieved memories, working memory, and each role's JSON output.
- Working memory is trimmed to `working_mem_max` to keep prompts small.

### 5.1 LLM call with retry/fallback
```python
async def _generate_with_retry(self, prompt: str, *, seed: Optional[int], fallback: Dict[str, Any]) -> str:
    last = ""
    current_seed = seed
    for attempt in range(self.settings.llm_max_retries + 1):
        try:
            resp = await self.llm.generate(prompt, seed=current_seed)  # Ollama JSON mode
            obj = json.loads(resp)
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            current_seed = None  # drop seed to vary output on retry
            continue
    return json.dumps(fallback, ensure_ascii=False)
```
- Guarantees well-formed JSON to satisfy the response contract.

### 5.2 Working memory for prompt context
```python
def _add_working(self, state: TradeState, content: str, role: str) -> None:
    if not content:
        return
    entry = {"content": content, "metadata": {"role": role, "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}}
    state.working_mem.append(entry)
    if len(state.working_mem) > self.settings.working_mem_max:
        state.working_mem = state.working_mem[-self.settings.working_mem_max :]
```
- Keeps a rolling window of recent utterances; injected into later prompts.

## 6) Prompt Schemas (JSON enforced)
```python
# agents/prompts.py (snippets)
BULL_TEMPLATE: summary + risks[]  # bullish drivers
BEAR_TEMPLATE: summary + risks[]  # bearish drivers
TRADER_TEMPLATE: {
  "action": "BUY_25|BUY_50|BUY_100|SELL_25|SELL_50|SELL_100|HOLD",
  "rationale": "...",
  "confidence": "low|medium|high"
}
MANAGER_TEMPLATE: {"risks": [...], "strategy": "...", "next_steps": ["..."]}
REFLECTION_TEMPLATE: {"reflection": "...", "actions": ["..."]}
```
- Forces each role's output into a machine-readable shape.

## 7) Memory Layer (Retrieval + Writeback)
```python
# memory/finmem_memory.py (scoring excerpt)
score = sim * role_weight - self.recency_lambda * age_days + self.salience_weight * float(sal)
```
- Retrieval ranks by similarity, boosted by role weights, penalized by age, optionally boosted by salience; filters by ticker/role/TTL/cutoff.

```python
async def add_memory(self, content: str, metadata: Dict[str, Any]) -> str:
    if len(content or "") < self.min_length:
        return "skipped_short"
    if await self._is_duplicate(content, metadata):
        return "deduped"
    self.store.add_texts([content], metadatas=[metadata], ids=[memory_id])
    # Manager reports roll up every rollup_count via LLM summarization
```
- Long-term memory in Redis; working memory in-process only.

## 8) LLM & Embeddings (Ollama APIs)
```python
class OllamaLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, *, seed: Optional[int] = None) -> str:
        options = {"temperature": self.temperature, "num_predict": self.num_predict}
        if seed is not None:
            options["seed"] = seed
        response = await self.client.generate(
            model=self.model_name,
            prompt=prompt,
            format="json",  # force JSON outputs
            options=options,
        )
        return response.get("response", "")
```
- Async Ollama JSON-mode calls; embeddings via `nomic-embed-text` stored in Redis.

## 9) Key Tunables (config.py)
- Debate depth: `max_rounds_bull_bear`
- LLM behavior: `llm_temperature`, `llm_max_tokens`, `llm_max_retries`
- Memory: `memory_search_k`, `memory_recency_lambda`, `memory_role_weights`, `memory_score_cutoff`, `memory_min_length`, `memory_rollup_count/target`, `working_mem_max`
- Modes: `use_memory` (retrieval on/off), `memory_store_manager_only` (writeback scope).

## 10) Output Contract (what the client gets)
- `summary.decision`: trader action/rationale/confidence
- `summary.report`: manager risks/strategy/next steps
- `summary.bull` / `summary.bear`: viewpoints and risks
- `summary.reflection`: post-hoc lessons and actions
- `summary.snapshot`: market/news snapshot used
- `summary.memories`: {long_term, working}
- `summary.meta`: seed, bb_rounds, model/embedding names, temperature, intervals, counts

## 11) Narrative Walkthrough (first-time audience)
1. Client calls `/api/run` with ticker/window and options (news, rounds, memory on/off).
2. Data loader fetches prices/news -> snapshot assembled.
3. Memory retrieval: similar past items pulled from Redis (role/recency weighted) if memory is enabled.
4. Debate:
   - Bull/Bear alternate `bb_rounds` times, each consuming snapshot + memories + working_mem.
   - Trader decides an action using both views + portfolio.
   - Manager consolidates into risks/strategy/next steps and is always written to long-term memory.
   - Reflection captures lessons/actions and is stored with higher salience.
5. Persist: summary + agent logs to Postgres; manager/reflection (and optionally bull/bear/trader) to Redis vectorstore.
6. Respond: client gets `simulation_id` and the structured `summary` ready for downstream analytics.

## 12) Why JSON mode + retries matter
- Prevents unstructured LLM text from breaking the API contract.
- Seeded retries give a second chance at well-formed JSON before falling back to a safe default.

## 13) Failure boundaries
- Validation errors -> 400, upstream data errors -> 502, unexpected errors -> 500 (logged).
- Memory/DB failures are isolated to avoid crashing the main response path (best-effort writes).

## 14) Quick demo recipe
- Start Redis + Postgres + Ollama locally.
- `POST /api/run` with `{ "ticker": "AAPL", "window": 120, "news": true, "bb_rounds": 2, "use_memory": true }`.
- Receive JSON decision/report plus links to the stored simulation by `simulation_id`.
