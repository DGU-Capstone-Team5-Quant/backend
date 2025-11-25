# backend

Setup (uv)
1) install uv: https://astral.sh/uv
2) uv venv .venv
3) uv sync

Data sources
- Prices: configure RapidAPI (e.g., Twelve Data time_series). Set `RAPID_API_KEY`, `RAPID_API_HOST`, and `RAPID_API_PRICE_URL_INTRADAY|DAILY`.
- News: default uses Yahoo Finance RSS (`RAPID_API_NEWS_URL`), no RapidAPI key required. Ensure the URL template includes `{symbol}`.

VS Code auto activation
- .vscode/settings.json points to .venv\\Scripts\\python.exe and keeps python.terminal.activateEnvironment on.
- .python-version pins 3.12 so IDEs pick the right interpreter.
- Open this folder in VS Code and create a new terminal; it should auto-activate .venv (prompt shows (.venv)).

Notes
- .venv is gitignored; commit uv.lock when generated.
- If you disable auto activation in VS Code, terminals will stay in the global env.
