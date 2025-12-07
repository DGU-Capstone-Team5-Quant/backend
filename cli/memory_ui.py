"""메모리 관리 UI 모듈"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import subprocess
import redis
import json
from datetime import datetime
from config import settings

console = Console()

custom_style = Style([
    ('qmark', 'fg:#5f87ff bold'),
    ('question', 'bold'),
    ('answer', 'fg:#00ff87 bold'),
    ('pointer', 'fg:#5f87ff bold'),
    ('highlighted', 'fg:#5f87ff bold'),
    ('selected', 'fg:#00ff87'),
])


class MemoryUI:
    """메모리 관리 인터랙티브 UI"""

    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=3)
            self.redis_client.ping()
        except Exception:
            pass

    def view_stats(self):
        """메모리 통계 조회"""
        console.print(Panel(
            "[bold cyan]메모리 통계[/bold cyan]",
            box=box.ROUNDED
        ))

        if not self.redis_client:
            console.print("[red]Redis에 연결할 수 없습니다.[/red]")
            return

        try:
            # Redis 정보
            info = self.redis_client.info()

            # 키 개수
            keys = self.redis_client.keys("*")
            memory_keys = [k for k in keys if "memory" in k.lower()]

            table = Table(box=box.ROUNDED, show_header=True)
            table.add_column("항목", style="cyan", width=30)
            table.add_column("값", style="green", justify="right")

            table.add_row("Redis 버전", info.get("redis_version", "N/A"))
            table.add_row("전체 키 개수", str(len(keys)))
            table.add_row("메모리 관련 키", str(len(memory_keys)))
            table.add_row("사용 메모리", f"{info.get('used_memory_human', 'N/A')}")
            table.add_row("피크 메모리", f"{info.get('used_memory_peak_human', 'N/A')}")

            console.print(table)

            # 메모리 키 미리보기
            if memory_keys:
                console.print("\n[bold]메모리 키 미리보기 (최근 5개):[/bold]")
                for key in memory_keys[:5]:
                    console.print(f"  • [dim]{key}[/dim]")

        except Exception as e:
            console.print(f"[red]통계 조회 실패: {e}[/red]")

    def reset_memory(self):
        """메모리 초기화"""
        console.print(Panel(
            "[bold yellow]⚠️  메모리 초기화[/bold yellow]\n\n"
            "[dim]모든 학습된 메모리가 삭제됩니다.\n"
            "이 작업은 되돌릴 수 없습니다.[/dim]",
            box=box.ROUNDED
        ))

        if not questionary.confirm(
            "정말로 메모리를 초기화하시겠습니까?",
            default=False,
            style=custom_style
        ).ask():
            console.print("[yellow]취소되었습니다.[/yellow]")
            return

        # 초기화 스크립트 실행
        try:
            import sys
            from pathlib import Path

            # .venv의 Python 찾기
            venv_python = Path(".venv/Scripts/python.exe")  # Windows
            if not venv_python.exists():
                venv_python = Path(".venv/bin/python")  # Linux/Mac

            python_exe = str(venv_python) if venv_python.exists() else sys.executable

            console.print("\n[cyan]메모리 초기화 중...[/cyan]")
            result = subprocess.run(
                [python_exe, "scripts/reset_memory.py", "--all", "--yes"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                console.print("[bold green]✓ 메모리가 초기화되었습니다.[/bold green]")
            else:
                console.print(f"[red]초기화 실패:\n{result.stderr}[/red]")

        except Exception as e:
            console.print(f"[red]오류 발생: {e}[/red]")

    def export_memory(self):
        """메모리 내보내기"""
        console.print(Panel(
            "[bold cyan]메모리 내보내기[/bold cyan]\n\n"
            "[dim]현재 메모리를 JSON 파일로 저장합니다.[/dim]",
            box=box.ROUNDED
        ))

        filename = questionary.text(
            "파일명:",
            default=f"memory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            style=custom_style
        ).ask()

        if not filename:
            return

        if not self.redis_client:
            console.print("[red]Redis에 연결할 수 없습니다.[/red]")
            return

        try:
            # 메모리 키 추출
            keys = self.redis_client.keys("*memory*")

            export_data = {}
            for key in keys:
                key_type = self.redis_client.type(key)
                if key_type == "string":
                    export_data[key] = self.redis_client.get(key)
                elif key_type == "hash":
                    export_data[key] = self.redis_client.hgetall(key)
                elif key_type == "list":
                    export_data[key] = self.redis_client.lrange(key, 0, -1)

            # 파일로 저장
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            console.print(f"[bold green]✓ 메모리를 {filename}에 저장했습니다.[/bold green]")

        except Exception as e:
            console.print(f"[red]내보내기 실패: {e}[/red]")

    def run(self):
        """메모리 관리 메뉴 실행"""
        while True:
            console.print()
            choices = [
                "📊 메모리 통계 조회",
                "🗑️  메모리 초기화",
                "💾 메모리 내보내기",
                "← 뒤로가기"
            ]

            choice = questionary.select(
                "메모리 관리 메뉴",
                choices=choices,
                style=custom_style
            ).ask()

            if not choice or choice == "← 뒤로가기":
                break

            if "통계 조회" in choice:
                self.view_stats()
            elif "초기화" in choice:
                self.reset_memory()
            elif "내보내기" in choice:
                self.export_memory()

            if choice != "← 뒤로가기":
                questionary.press_any_key_to_continue("\n계속하려면 아무 키나 누르세요...").ask()
