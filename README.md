# backend

Setup (uv)
1) install uv: https://astral.sh/uv
2) uv venv .venv
3) uv sync

VS Code auto activation
- .vscode/settings.json points to .venv\\Scripts\\python.exe and keeps python.terminal.activateEnvironment on.
- .python-version pins 3.12 so IDEs pick the right interpreter.
- Open this folder in VS Code and create a new terminal; it should auto-activate .venv (prompt shows (.venv)).

Notes
- .venv is gitignored; commit uv.lock when generated.
- If you disable auto activation in VS Code, terminals will stay in the global env.
