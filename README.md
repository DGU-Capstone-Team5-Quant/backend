# backend

Setup (uv)
1) install uv: https://astral.sh/uv
2) uv venv .venv
3) uv sync

Data sources
- Prices: configure RapidAPI (e.g., Twelve Data time_series). Set `RAPID_API_KEY`, `RAPID_API_HOST`, and `RAPID_API_PRICE_URL_INTRADAY|DAILY`.
- News: default uses Yahoo Finance RSS (`RAPID_API_NEWS_URL`), no RapidAPI key required. Ensure the URL template includes `{symbol}`.

Memory/FinMem options
- `MEMORY_STORE_MANAGER_ONLY` (default true): store only Manager summaries to save cost. Set false to keep Bull/Bear/Trader too.
- `MEMORY_SEARCH_K`: how many memories to retrieve (3 is a good balance).
- `MEMORY_RECENCY_LAMBDA`: recency penalty per day when ranking memories.
- `MEMORY_DUPLICATE_THRESHOLD`: similarity threshold to skip storing near-duplicate memories.
- `MEMORY_TTL_DAYS`: memories older than this are ignored in search.
- `MEMORY_ROLE_WEIGHTS`: role weighting for ranking (e.g., {"manager":1.5,"trader":1.2,"bull":1,"bear":1}).
- `EMBEDDING_MODE`: `stub` or `gemini` to force embedding selection.
- `MEMORY_SALIENCE_WEIGHT`: additional weight for salience/pnl metadata when ranking.
- `MEMORY_SCORE_CUTOFF`: drop memories whose score falls below this cutoff.
- `MEMORY_MIN_LENGTH`: skip storing too-short content.
- `MEMORY_SKIP_STUB`: when true and embedding mode is stub, skip LTM writes (cost/quality control).

VS Code auto activation
- .vscode/settings.json points to .venv\\Scripts\\python.exe and keeps python.terminal.activateEnvironment on.
- .python-version pins 3.12 so IDEs pick the right interpreter.
- Open this folder in VS Code and create a new terminal; it should auto-activate .venv (prompt shows (.venv)).

Notes
- .venv is gitignored; commit uv.lock when generated.
- If you disable auto activation in VS Code, terminals will stay in the global env.
