"""대시보드 모듈"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich import box
from rich.text import Text
import redis
import requests
import json
from datetime import datetime
from config import settings

console = Console()


class Dashboard:
    """시스템 대시보드"""

    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=3)
            self.redis_client.ping()
        except Exception:
            pass

    def get_system_status(self) -> Table:
        """시스템 상태 테이블"""
        table = Table(title="시스템 상태", box=box.ROUNDED, show_header=True)
        table.add_column("컴포넌트", style="cyan", width=20)
        table.add_column("상태", width=15)

        # Ollama
        try:
            ollama_url = f"{settings.ollama_base_url}/api/tags"
            response = requests.get(ollama_url, timeout=2)
            if response.status_code == 200:
                table.add_row("Ollama (LLM)", "[green]● 정상[/green]")
            else:
                table.add_row("Ollama (LLM)", "[red]● 오류[/red]")
        except Exception:
            table.add_row("Ollama (LLM)", "[red]● 연결 안됨[/red]")

        # Redis
        if self.redis_client:
            try:
                self.redis_client.ping()
                table.add_row("Redis (Memory)", "[green]● 정상[/green]")
            except Exception:
                table.add_row("Redis (Memory)", "[red]● 오류[/red]")
        else:
            table.add_row("Redis (Memory)", "[red]● 연결 안됨[/red]")

        return table

    def get_memory_stats(self) -> Table:
        """메모리 통계 테이블"""
        table = Table(title="메모리 상태", box=box.ROUNDED, show_header=True)
        table.add_column("항목", style="cyan", width=25)
        table.add_column("값", style="green", justify="right")

        if not self.redis_client:
            table.add_row("상태", "[red]연결 안됨[/red]")
            return table

        try:
            info = self.redis_client.info()
            keys = self.redis_client.keys("*")
            memory_keys = [k for k in keys if "memory" in k.lower()]

            table.add_row("전체 키 개수", str(len(keys)))
            table.add_row("메모리 키 개수", str(len(memory_keys)))
            table.add_row("사용 메모리", info.get('used_memory_human', 'N/A'))
            table.add_row("피크 메모리", info.get('used_memory_peak_human', 'N/A'))

        except Exception as e:
            table.add_row("오류", str(e))

        return table

    def get_recent_backtests(self) -> Table:
        """최근 백테스트 결과 테이블"""
        table = Table(title="최근 백테스트 결과", box=box.ROUNDED, show_header=True)
        table.add_column("날짜", style="cyan", width=20)
        table.add_column("티커", style="yellow", width=8)
        table.add_column("수익률", justify="right", width=12)
        table.add_column("승률", justify="right", width=10)

        results_dir = Path("results")
        if not results_dir.exists():
            table.add_row("결과 없음", "", "", "")
            return table

        result_files = list(results_dir.glob("backtest_*.json"))

        if not result_files:
            table.add_row("결과 없음", "", "", "")
            return table

        # 최근 5개만
        result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for result_file in result_files[:5]:
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)

                metrics = result.get("metrics", {})
                config = result.get("config", {})

                # 파일 수정 시간
                mtime = datetime.fromtimestamp(result_file.stat().st_mtime)
                date_str = mtime.strftime("%Y-%m-%d %H:%M")

                # 수익률 색상
                total_return = metrics.get("total_return", 0)
                return_str = f"{total_return:.2%}"
                if total_return > 0:
                    return_str = f"[green]{return_str}[/green]"
                elif total_return < 0:
                    return_str = f"[red]{return_str}[/red]"

                table.add_row(
                    date_str,
                    config.get("ticker", "N/A"),
                    return_str,
                    f"{metrics.get('win_rate', 0):.1%}"
                )

            except Exception:
                continue

        return table

    def show(self):
        """대시보드 표시"""
        console.clear()

        # 헤더
        console.print(Panel(
            "[bold cyan]FinMem Trading System - Dashboard[/bold cyan]\n"
            f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
            box=box.DOUBLE
        ))

        console.print()

        # 레이아웃 생성
        layout = Layout()
        layout.split_column(
            Layout(name="top", size=10),
            Layout(name="middle", size=10),
            Layout(name="bottom")
        )

        # 상단: 시스템 상태
        layout["top"].update(self.get_system_status())

        # 중단: 메모리 상태
        layout["middle"].update(self.get_memory_stats())

        # 하단: 최근 백테스트
        layout["bottom"].update(self.get_recent_backtests())

        console.print(layout)

        console.print()
        questionary.press_any_key_to_continue("계속하려면 아무 키나 누르세요...").ask()
