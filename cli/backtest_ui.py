"""백테스팅 UI 모듈"""

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich.layout import Layout
from rich import box
from datetime import datetime, timedelta
import subprocess
import json
from pathlib import Path
from cli.visualization import BacktestVisualizer

console = Console()

custom_style = Style([
    ('qmark', 'fg:#5f87ff bold'),
    ('question', 'bold'),
    ('answer', 'fg:#00ff87 bold'),
    ('pointer', 'fg:#5f87ff bold'),
    ('highlighted', 'fg:#5f87ff bold'),
    ('selected', 'fg:#00ff87'),
])


class BacktestUI:
    """백테스팅 인터랙티브 UI"""

    def __init__(self):
        self.config = {}

    def quick_backtest(self):
        """빠른 백테스트 (기본 설정)"""
        console.print(Panel(
            "[bold cyan]빠른 백테스트[/bold cyan]\n"
            "기본 설정으로 즉시 백테스트를 실행합니다. (약 1분 소요)",
            box=box.ROUNDED
        ))

        # 티커만 입력
        ticker = questionary.text(
            "티커를 입력하세요:",
            default="AAPL",
            style=custom_style
        ).ask()

        if not ticker:
            return

        # 기본 설정 (빠른 실행을 위해 1일 간격, 고정 기간)
        # 2025-11-21 ~ 2025-12-02 (약 12일 거래일)
        start_date = "2025-11-21"
        end_date = "2025-12-02"

        # 기간에 맞춰 윈도우 자동 계산
        # 12일 기간이면 윈도우 3일로 설정하여 더 많은 거래 기회 제공
        period_days = 12
        window = max(3, min(5, int(period_days * 0.25)))  # 최소 3일, 최대 5일

        config = {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "window": window,
            "interval": "1day",
            "seed": 42,
            "use_memory": True
        }

        console.print("\n[dim]설정:[/dim]")
        self._show_config(config)

        if questionary.confirm("실행하시겠습니까?", default=True, style=custom_style).ask():
            self._run_backtest(config)

    def custom_backtest(self):
        """커스텀 백테스트 (상세 설정)"""
        console.print(Panel(
            "[bold cyan]커스텀 백테스트[/bold cyan]\n"
            "상세 설정으로 백테스트를 실행합니다.",
            box=box.ROUNDED
        ))

        # 티커
        ticker = questionary.text(
            "티커:",
            default="AAPL",
            style=custom_style
        ).ask()

        if not ticker:
            return

        # 시작 날짜 (과거 날짜로 기본값 설정)
        console.print("\n[yellow]⚠️  주의: 과거 날짜만 사용 가능합니다 (오늘/미래 날짜는 데이터 없음)[/yellow]\n")

        start_date = questionary.text(
            "시작 날짜 (YYYY-MM-DD):",
            default=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            style=custom_style
        ).ask()

        # 종료 날짜 (어제 날짜로 설정 - 오늘은 데이터 없을 수 있음)
        end_date = questionary.text(
            "종료 날짜 (YYYY-MM-DD):",
            default=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            style=custom_style
        ).ask()

        # 날짜 검증
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if end >= today:
                console.print(f"\n[red]✗ 오류: 종료 날짜({end_date})가 오늘이거나 미래입니다.[/red]")
                console.print(f"[yellow]오늘/미래 날짜는 주식 데이터가 없습니다. 어제({(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}) 이전 날짜를 사용하세요.[/yellow]\n")
                return

            if start >= end:
                console.print(f"\n[red]✗ 오류: 시작 날짜가 종료 날짜보다 늦습니다.[/red]\n")
                return

        except ValueError:
            console.print("\n[red]✗ 오류: 날짜 형식이 올바르지 않습니다. (YYYY-MM-DD 형식 사용)[/red]\n")
            return

        # 간격 선택
        interval = questionary.select(
            "시간 간격:",
            choices=["1day (일봉)", "1h (1시간봉)", "4h (4시간봉)"],
            default="1day (일봉)",
            style=custom_style
        ).ask()
        interval = interval.split()[0]  # "1day (일봉)" -> "1day"

        # 기간에 맞춰 윈도우 자동 계산
        period_days = (end - start).days

        # Interval에 따른 데이터 포인트 수 추정 및 윈도우 자동 설정
        # 주의: 주식시장은 하루 약 6.5시간만 거래 (09:30-16:00)
        if interval == "1day":
            estimated_data_points = period_days
            window = max(3, min(15, int(period_days * 0.2)))
        elif interval == "1h":
            # 1시간봉: 하루 약 6.5개 (장 시간만)
            estimated_data_points = int(period_days * 6.5)
            window = max(10, min(50, int(estimated_data_points * 0.2)))
        elif interval == "4h":
            # 4시간봉: 하루 약 1.5개 (장 시간 6.5h ÷ 4h)
            estimated_data_points = int(period_days * 1.5)
            window = max(5, min(20, int(estimated_data_points * 0.3)))
        else:
            # 2시간봉: 하루 약 3개
            estimated_data_points = int(period_days * 3)
            window = max(7, min(30, int(estimated_data_points * 0.25)))

        # 예상 거래 횟수 (데이터 포인트 - 윈도우)
        estimated_trades = max(0, estimated_data_points - window)

        # 자동 설정 정보 표시
        console.print(f"\n[dim]✓ 윈도우 자동 설정: {window} (기간 {period_days}일, {interval})[/dim]")
        if estimated_trades > 0:
            console.print(f"[dim]  📊 예상 거래 횟수: 약 {estimated_trades}회[/dim]\n")
        else:
            console.print(f"[yellow]  ⚠️  경고: 기간이 너무 짧아 거래가 불가능할 수 있습니다![/yellow]\n")

        # 시드
        seed = questionary.text(
            "랜덤 시드 (재현성):",
            default="42",
            style=custom_style
        ).ask()

        # 메모리 사용
        use_memory = questionary.confirm(
            "메모리 학습을 사용하시겠습니까?",
            default=True,
            style=custom_style
        ).ask()

        config = {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "window": int(window),
            "interval": interval,
            "seed": int(seed),
            "use_memory": use_memory
        }

        console.print("\n[dim]설정 확인:[/dim]")
        self._show_config(config)

        if questionary.confirm("\n실행하시겠습니까?", default=True, style=custom_style).ask():
            self._run_backtest(config)

    def view_results(self):
        """과거 결과 조회"""
        console.print(Panel(
            "[bold cyan]백테스트 결과 조회[/bold cyan]",
            box=box.ROUNDED
        ))

        results_dir = Path("results")
        if not results_dir.exists():
            console.print("[yellow]아직 실행된 백테스트가 없습니다.[/yellow]")
            return

        # JSON 결과 파일 찾기
        result_files = list(results_dir.glob("backtest_*.json"))

        if not result_files:
            console.print("[yellow]저장된 결과가 없습니다.[/yellow]")
            return

        # 최근 파일부터 정렬
        result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # 파일 선택
        choices = [f.name for f in result_files[:10]]  # 최근 10개만
        choices.append("← 뒤로가기")

        selected = questionary.select(
            "결과 파일을 선택하세요:",
            choices=choices,
            style=custom_style
        ).ask()

        if selected == "← 뒤로가기" or not selected:
            return

        # 결과 표시
        result_path = results_dir / selected
        self._display_result(result_path)

    def _show_config(self, config):
        """설정 테이블 표시"""
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("항목", style="cyan")
        table.add_column("값", style="green")

        table.add_row("티커", config["ticker"])
        table.add_row("기간", f"{config['start_date']} ~ {config['end_date']}")
        if "window" in config:
            table.add_row("윈도우", str(config["window"]))
        if "interval" in config:
            table.add_row("간격", config["interval"])
        table.add_row("시드", str(config["seed"]))
        table.add_row("메모리 학습", "사용" if config.get("use_memory", True) else "미사용")

        console.print(table)

    def _run_backtest(self, config):
        """백테스트 실행"""
        console.print("\n[bold cyan]백테스트를 시작합니다...[/bold cyan]\n")

        # 가상환경의 Python 경로 찾기
        import sys
        import os
        from pathlib import Path

        # .venv의 Python 찾기
        venv_python = Path(".venv/Scripts/python.exe")  # Windows
        if not venv_python.exists():
            venv_python = Path(".venv/bin/python")  # Linux/Mac

        python_exe = str(venv_python) if venv_python.exists() else sys.executable

        # 명령어 구성
        cmd = [
            python_exe, "scripts/run_backtest.py",
            "--ticker", config["ticker"],
            "--start-date", config["start_date"],
            "--end-date", config["end_date"],
            "--seed", str(config["seed"])
        ]

        # 옵셔널 파라미터 추가
        if "window" in config:
            cmd.extend(["--window", str(config["window"])])
        if "interval" in config:
            cmd.extend(["--interval", config["interval"]])

        if config.get("use_memory", True):
            cmd.append("--use-memory")
        else:
            cmd.append("--no-memory")

        # 환경 변수 설정 (버퍼링 비활성화)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # 프로세스 실행
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]백테스트 실행 중...", total=100)

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env
                )

                # 실시간 출력
                total_trades = 100  # 기본값
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        # 전체 거래 횟수 파싱
                        if "예상 거래 결정 횟수:" in line:
                            try:
                                total_trades = int(line.split(":")[1].replace("회", "").strip())
                                progress.update(task, total=total_trades, completed=0)
                            except:
                                pass

                        # 진행률 업데이트
                        if line.startswith("PROGRESS:"):
                            try:
                                parts = line.split(":")[1].strip().split("/")
                                current = int(parts[0])
                                progress.update(task, completed=current)
                            except:
                                pass
                        elif "거래 #" in line or "백테스트" in line:
                            # 거래 로그나 중요 메시지만 표시
                            console.print(f"[dim]{line}[/dim]")
                        elif "예상" in line or "주요 메트릭" in line or "=" in line:
                            # 시작/종료 메시지 표시
                            console.print(f"[dim]{line}[/dim]")

                process.wait()
                progress.update(task, completed=100)

            if process.returncode == 0:
                console.print("\n[bold green]✓ 백테스트 완료![/bold green]")

                # 결과 파일 찾기
                results_dir = Path("results")
                result_files = list(results_dir.glob(f"backtest_{config['ticker']}_*.json"))
                if result_files:
                    latest = max(result_files, key=lambda x: x.stat().st_mtime)
                    console.print(f"\n결과 파일: [cyan]{latest}[/cyan]")

                    if questionary.confirm("결과를 표시하시겠습니까?", default=True, style=custom_style).ask():
                        self._display_result(latest)
            else:
                console.print("\n[bold red]✗ 백테스트 실패[/bold red]")

        except Exception as e:
            console.print(f"\n[bold red]오류 발생:[/bold red] {e}")

    def _display_result(self, result_path: Path):
        """결과 표시"""
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                result = json.load(f)

            console.print(Panel(
                f"[bold cyan]백테스트 결과: {result_path.name}[/bold cyan]",
                box=box.ROUNDED
            ))

            # 메트릭스 테이블
            metrics = result.get("summary", {})  # "metrics" -> "summary"로 수정
            table = Table(title="성과 메트릭", box=box.ROUNDED, show_header=True)
            table.add_column("메트릭", style="cyan", width=20)
            table.add_column("값", style="green", justify="right")

            table.add_row("초기 자본", f"${metrics.get('initial_capital', 0):,.2f}")
            table.add_row("최종 자본", f"${metrics.get('final_equity', 0):,.2f}")
            table.add_row("현금", f"${metrics.get('final_cash', 0):,.2f}")
            table.add_row("총 수익률", f"{metrics.get('total_return', 0):.2%}")
            table.add_row("CAGR", f"{metrics.get('cagr', 0):.2%}")
            table.add_row("샤프 비율", f"{metrics.get('sharpe', 0):.3f}")
            table.add_row("최대 낙폭", f"{metrics.get('max_drawdown_pct', 0):.2%}")
            table.add_row("칼마 비율", f"{metrics.get('calmar', 0):.3f}")
            table.add_row("총 거래 횟수", str(metrics.get('trades_count', 0)))

            console.print(table)

            # 거래 내역
            trades = result.get("trades", [])
            if trades:
                console.print(f"\n[bold]최근 거래 ({len(trades)}건)[/bold]")
                trade_table = Table(box=box.SIMPLE, show_header=True)
                trade_table.add_column("날짜", style="cyan")
                trade_table.add_column("액션", style="yellow")
                trade_table.add_column("가격", justify="right", style="green")
                trade_table.add_column("수익", justify="right")

                for trade in trades[-10:]:  # 최근 10건
                    # trade는 dict이며 ts, action, price, pnl 등의 필드를 가짐
                    ts = trade.get("ts", "")
                    if isinstance(ts, str):
                        # 이미 문자열이면 그대로 사용
                        date_str = ts.split("T")[0] if "T" in ts else ts[:10]
                    else:
                        date_str = str(ts)[:10]

                    action = trade.get("action", "HOLD")
                    price = trade.get("price", 0)
                    pnl = trade.get("pnl", 0)
                    pnl_style = "green" if pnl >= 0 else "red"
                    pnl_text = f"[{pnl_style}]${pnl:+.2f}[/{pnl_style}]"

                    trade_table.add_row(
                        date_str,
                        action,
                        f"${price:.2f}",
                        pnl_text
                    )

                console.print(trade_table)

            # 차트 표시 옵션
            console.print()
            if questionary.confirm("📊 차트를 생성하시겠습니까?", default=True, style=custom_style).ask():
                self._show_charts(result_path)

        except Exception as e:
            console.print(f"[red]결과 파일을 읽을 수 없습니다: {e}[/red]")

    def _show_charts(self, result_path: Path):
        """차트 생성 및 표시 (루프로 여러 차트 선택 가능)"""
        try:
            visualizer = BacktestVisualizer()
            result = visualizer.load_result(result_path)

            # 차트 저장 경로
            base_name = result_path.stem
            output_dir = result_path.parent / 'charts'
            output_dir.mkdir(exist_ok=True)

            # 차트 선택 루프
            while True:
                console.print()

                # 차트 타입 선택
                choices = [
                    "📈 통합 대시보드 (전체 차트)",
                    "💰 자본 변화 그래프",
                    "📊 주가 및 매매 시점",
                    "← 뒤로가기"
                ]

                choice = questionary.select(
                    "어떤 차트를 보시겠습니까?",
                    choices=choices,
                    style=custom_style
                ).ask()

                if not choice or "뒤로가기" in choice:
                    break

                console.print(f"\n[cyan]차트 생성 중...[/cyan]")

                # 선택한 차트 생성
                if "통합 대시보드" in choice:
                    save_path = output_dir / f"{base_name}_dashboard.png"
                    visualizer.plot_combined_dashboard(result, save_path)
                elif "자본 변화" in choice:
                    save_path = output_dir / f"{base_name}_equity.png"
                    visualizer.plot_equity_curve(result, save_path)
                elif "주가 및 매매" in choice:
                    save_path = output_dir / f"{base_name}_trades.png"
                    visualizer.plot_trades_on_price(result, save_path)

                console.print(f"[bold green]✓ 차트가 저장되었습니다: {save_path}[/bold green]")

                # 파일 열기 옵션
                if questionary.confirm("차트 파일을 여시겠습니까?", default=True, style=custom_style).ask():
                    import os
                    os.startfile(save_path)  # Windows에서 기본 이미지 뷰어로 열기

        except Exception as e:
            console.print(f"[red]차트 생성 실패: {e}[/red]")
            import traceback
            traceback.print_exc()

    def run(self):
        """백테스팅 메뉴 실행"""
        while True:
            console.print()
            choices = [
                "⚡ 빠른 백테스트 (Quick Start)",
                "⚙️  커스텀 백테스트 (Custom Setup)",
                "📁 과거 결과 조회 (View Results)",
                "← 뒤로가기"
            ]

            choice = questionary.select(
                "백테스팅 메뉴",
                choices=choices,
                style=custom_style
            ).ask()

            if not choice or choice == "← 뒤로가기":
                break

            if "빠른 백테스트" in choice:
                self.quick_backtest()
            elif "커스텀 백테스트" in choice:
                self.custom_backtest()
            elif "과거 결과 조회" in choice:
                self.view_results()
