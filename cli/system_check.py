"""시스템 상태 체크 모듈"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import redis
from rich.console import Console
from rich.table import Table
from rich import box
from config import settings

console = Console()


class SystemCheck:
    """시스템 요구사항 체크"""

    def __init__(self):
        self.checks = []

    def check_ollama(self) -> bool:
        """Ollama 연결 확인"""
        try:
            ollama_url = f"{settings.ollama_base_url}/api/tags"
            response = requests.get(ollama_url, timeout=3)
            if response.status_code == 200:
                models = response.json().get("models", [])
                has_llama = any("llama" in m.get("name", "") for m in models)
                return True, has_llama
            return False, False
        except Exception:
            return False, False

    def check_redis(self) -> bool:
        """Redis 연결 확인"""
        try:
            r = redis.from_url(settings.redis_url, socket_connect_timeout=3)
            r.ping()
            return True
        except Exception:
            return False

    def run(self) -> bool:
        """모든 체크 실행"""
        table = Table(
            title="시스템 상태 체크",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("컴포넌트", style="cyan", width=20)
        table.add_column("상태", width=15)
        table.add_column("세부정보", style="dim")

        all_ok = True

        # Ollama 체크
        ollama_ok, has_model = self.check_ollama()
        if ollama_ok:
            if has_model:
                table.add_row(
                    "Ollama (LLM)",
                    "[green]✓ 연결됨[/green]",
                    "모델 준비 완료"
                )
            else:
                table.add_row(
                    "Ollama (LLM)",
                    "[yellow]⚠ 경고[/yellow]",
                    "llama 모델이 없습니다. 'ollama pull llama3.1:8b' 실행"
                )
                all_ok = False
        else:
            table.add_row(
                "Ollama (LLM)",
                "[red]✗ 연결 실패[/red]",
                "Ollama를 시작하세요: 'ollama serve'"
            )
            all_ok = False

        # Redis 체크
        redis_ok = self.check_redis()
        if redis_ok:
            table.add_row(
                "Redis (Memory)",
                "[green]✓ 연결됨[/green]",
                "메모리 저장소 준비 완료"
            )
        else:
            table.add_row(
                "Redis (Memory)",
                "[red]✗ 연결 실패[/red]",
                "Redis를 시작하세요: 'docker run -d -p 6379:6379 redis:latest'"
            )
            all_ok = False

        console.print(table)
        return all_ok
