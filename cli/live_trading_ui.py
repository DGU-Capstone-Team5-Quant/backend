"""실시간 거래 UI 모듈"""

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from datetime import datetime
import subprocess
import sys
import os
from pathlib import Path

console = Console()

custom_style = Style([
    ('qmark', 'fg:#5f87ff bold'),
    ('question', 'bold'),
    ('answer', 'fg:#00ff87 bold'),
    ('pointer', 'fg:#5f87ff bold'),
    ('highlighted', 'fg:#5f87ff bold'),
    ('selected', 'fg:#00ff87'),
])


class LiveTradingUI:
    """실시간 거래 인터랙티브 UI"""

    def __init__(self):
        pass

    def quick_trade(self):
        """빠른 거래 추천"""
        console.print(Panel(
            "[bold cyan]💡 실시간 거래 추천[/bold cyan]\n"
            "현재 시점의 시장 데이터를 분석하여 거래 결정을 추천합니다.",
            box=box.ROUNDED
        ))

        # 티커 입력
        ticker = questionary.text(
            "티커를 입력하세요:",
            default="AAPL",
            style=custom_style
        ).ask()

        if not ticker:
            return

        # 간격 선택
        interval = questionary.select(
            "분석 간격:",
            choices=["1h (1시간봉)", "4h (4시간봉)", "1day (일봉)"],
            default="1h (1시간봉)",
            style=custom_style
        ).ask()
        interval = interval.split()[0]

        # 메모리 사용
        use_memory = questionary.confirm(
            "과거 학습 메모리를 사용하시겠습니까?",
            default=True,
            style=custom_style
        ).ask()

        # 설정 표시
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("항목", style="cyan")
        table.add_column("값", style="green")
        table.add_row("티커", ticker)
        table.add_row("분석 간격", interval)
        table.add_row("현재 시각", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("메모리 학습", "사용" if use_memory else "미사용")

        console.print("\n[dim]설정:[/dim]")
        console.print(table)

        if not questionary.confirm("\n실행하시겠습니까?", default=True, style=custom_style).ask():
            return

        # 실행
        self._run_live_analysis(ticker, interval, use_memory)

    def _run_live_analysis(self, ticker: str, interval: str, use_memory: bool):
        """실시간 분석 실행"""
        console.print(f"\n[bold cyan]🔍 {ticker} 분석 중...[/bold cyan]\n")

        # 가상환경 Python 찾기
        venv_python = Path(".venv/Scripts/python.exe")
        if not venv_python.exists():
            venv_python = Path(".venv/bin/python")
        python_exe = str(venv_python) if venv_python.exists() else sys.executable

        # 명령어 구성
        cmd = [
            python_exe, "scripts/run_live.py",
            "--ticker", ticker,
            "--interval", interval,
            "--window", "30",
        ]

        if use_memory:
            cmd.append("--use-memory")
        else:
            cmd.append("--no-memory")

        # 환경 변수 설정
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # 실행
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=False,
                text=True
            )

            if result.returncode == 0:
                console.print(f"\n[bold green]✓ 분석 완료![/bold green]\n")
            else:
                console.print(f"\n[bold red]✗ 분석 실패[/bold red]\n")

        except Exception as e:
            console.print(f"\n[bold red]오류 발생:[/bold red] {e}\n")

    def run(self):
        """실시간 거래 메뉴 실행"""
        while True:
            console.print()
            choices = [
                "💡 실시간 거래 추천 (Live Recommendation)",
                "← 뒤로가기"
            ]

            choice = questionary.select(
                "실시간 거래 메뉴",
                choices=choices,
                style=custom_style
            ).ask()

            if not choice or choice == "← 뒤로가기":
                break

            if "실시간 거래 추천" in choice:
                self.quick_trade()
