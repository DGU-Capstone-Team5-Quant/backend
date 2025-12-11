"""메인 메뉴 모듈"""

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel

from cli.backtest_ui import BacktestUI
from cli.live_trading_ui import LiveTradingUI
from cli.memory_ui import MemoryUI

console = Console()

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


class MainMenu:
    """메인 메뉴 컨트롤러"""

    def __init__(self):
        self.running = True

    def show_menu(self):
        """메인 메뉴 표시"""
        choices = [
            "📊 백테스팅 (Backtesting)",
            "🚀 실시간 거래 (Live Trading)",
            "🧠 메모리 관리 (Memory Management)",
            "❌ 종료 (Exit)"
        ]

        answer = questionary.select(
            "무엇을 하시겠습니까?",
            choices=choices,
            style=custom_style,
            instruction="(방향키로 선택, Enter로 확인)"
        ).ask()

        return answer

    def run(self):
        """메인 루프 실행"""
        while self.running:
            try:
                console.print()
                choice = self.show_menu()

                if not choice:  # Ctrl+C 등으로 취소
                    self.running = False
                    continue

                if "백테스팅" in choice:
                    BacktestUI().run()
                elif "실시간 거래" in choice:
                    LiveTradingUI().run()
                elif "메모리 관리" in choice:
                    MemoryUI().run()
                elif "종료" in choice:
                    self.running = False
                    console.print("\n[bold cyan]Quant를 이용해주셔서 감사합니다! 👋[/bold cyan]\n")

            except KeyboardInterrupt:
                console.print("\n[yellow]메인 메뉴로 돌아갑니다...[/yellow]")
                continue
