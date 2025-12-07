#!/usr/bin/env python3
"""
Quant Trading System - Interactive CLI
메모리 기반 멀티 에이전트 트레이딩 시스템
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
import questionary
from questionary import Style

from cli.menu import MainMenu
from cli.system_check import SystemCheck
from cli.dashboard import Dashboard

console = Console()

# 커스텀 스타일
custom_style = Style([
    ('qmark', 'fg:#5f87ff bold'),
    ('question', 'bold'),
    ('answer', 'fg:#00ff87 bold'),
    ('pointer', 'fg:#5f87ff bold'),
    ('highlighted', 'fg:#5f87ff bold'),
    ('selected', 'fg:#00ff87'),
    ('separator', 'fg:#6c6c6c'),
    ('instruction', 'fg:#6c6c6c'),
])


def show_banner():
    """시스템 배너 표시"""
    # 그라데이션 효과를 위한 배너
    console.print()
    console.print("[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]                                                              [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]     [bold magenta]█████[/bold magenta]  [bold blue]██   ██[/bold blue] [bold cyan]███████[/bold cyan] [bold green]██   ██[/bold green] [bold yellow]████████[/bold yellow]     [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]    [bold magenta]██   ██[/bold magenta] [bold blue]██   ██[/bold blue] [bold cyan]██   ██[/bold cyan] [bold green]███  ██[/bold green]    [bold yellow]██[/bold yellow]        [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]    [bold magenta]██   ██[/bold magenta] [bold blue]██   ██[/bold blue] [bold cyan]███████[/bold cyan] [bold green]██ █ ██[/bold green]    [bold yellow]██[/bold yellow]        [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]    [bold magenta]██▄▄██[/bold magenta] [bold blue]██   ██[/bold blue] [bold cyan]██   ██[/bold cyan] [bold green]██  ███[/bold green]    [bold yellow]██[/bold yellow]        [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]     [bold magenta]████[/bold magenta]   [bold blue]███████[/bold blue] [bold cyan]██   ██[/bold cyan] [bold green]██   ██[/bold green]    [bold yellow]██[/bold yellow]        [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]                                                              [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]          [bold white]Memory-Based Multi-Agent Trading System[/bold white]         [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]║[/bold cyan]                                                              [bold cyan]║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]")
    console.print()
    console.print("                [dim]Version 1.0.0[/dim] [bold cyan]│[/bold cyan] [dim]LLM Agents & Redis Memory[/dim]")
    console.print()


def main():
    """메인 엔트리포인트"""
    try:
        # 배너 표시
        show_banner()

        # 시스템 상태 체크
        system_check = SystemCheck()
        if not system_check.run():
            console.print("\n[bold red]⚠️  시스템 요구사항이 충족되지 않았습니다.[/bold red]")
            console.print("[yellow]위 문제를 해결한 후 다시 실행해주세요.[/yellow]")
            return

        console.print("\n[bold green]✓ 시스템 준비 완료![/bold green]\n")

        # 메인 메뉴 실행
        menu = MainMenu()
        menu.run()

    except KeyboardInterrupt:
        console.print("\n\n[yellow]프로그램을 종료합니다.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]오류 발생:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
