"""백테스팅 결과 시각화 모듈"""

import json
from pathlib import Path
from typing import Dict, List, Any
import os
import warnings

# 모든 경고 메시지 완전히 숨기기
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

import matplotlib
matplotlib.use('Agg')  # GUI 없이 백그라운드에서 실행
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np


class BacktestVisualizer:
    """백테스팅 결과를 시각화하는 클래스"""

    def __init__(self):
        # logging 완전히 끄기
        import logging
        logging.getLogger('matplotlib').setLevel(logging.CRITICAL)
        logging.getLogger('PIL').setLevel(logging.CRITICAL)

        # 한글 폰트 설정 (Windows 기본 폰트)
        import matplotlib.font_manager as fm

        # 시스템에 설치된 모든 폰트에서 한글 폰트 찾기
        available_fonts = {f.name for f in fm.fontManager.ttflist}

        # 우선순위대로 한글 폰트 선택
        korean_fonts = ['Malgun Gothic', 'malgun', 'Gulim', 'gulim', 'Batang', 'NanumGothic']
        selected_font = None

        for font_name in korean_fonts:
            # 대소문자 구분 없이 찾기
            for available_font in available_fonts:
                if font_name.lower() in available_font.lower():
                    selected_font = available_font
                    break
            if selected_font:
                break

        if selected_font:
            plt.rcParams['font.family'] = selected_font
            plt.rcParams['font.sans-serif'] = [selected_font] + plt.rcParams['font.sans-serif']
        else:
            # 한글 폰트가 없으면 기본 폰트 사용 (영어로만 표시)
            plt.rcParams['font.family'] = 'sans-serif'

        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

        # 스타일 설정
        try:
            plt.style.use('seaborn-v0_8-darkgrid')
        except:
            try:
                plt.style.use('seaborn-darkgrid')
            except:
                pass  # 스타일 없으면 기본 사용

    def load_result(self, json_path: Path) -> Dict[str, Any]:
        """JSON 결과 파일 로드"""
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def plot_equity_curve(self, result: Dict[str, Any], save_path: Path = None):
        """Equity Curve Chart"""
        trades = result.get('trades', [])
        if not trades:
            print("No trades found.")
            return

        # Extract data
        timestamps = [datetime.strptime(t['ts'], '%Y-%m-%d %H:%M:%S') for t in trades]
        equity_values = [t['equity'] for t in trades]
        initial_capital = result['summary']['initial_capital']

        # Create chart
        fig, ax = plt.subplots(figsize=(14, 6))

        ax.plot(timestamps, equity_values, linewidth=2, color='#2E86AB', label='Equity')
        ax.axhline(y=initial_capital, color='gray', linestyle='--', linewidth=1, alpha=0.7, label=f'Initial Capital (${initial_capital:,.0f})')

        # Fill profit/loss zones
        ax.fill_between(timestamps, equity_values, initial_capital,
                        where=np.array(equity_values) >= initial_capital,
                        alpha=0.3, color='green', label='Profit Zone')
        ax.fill_between(timestamps, equity_values, initial_capital,
                        where=np.array(equity_values) < initial_capital,
                        alpha=0.3, color='red', label='Loss Zone')

        # Labels and title
        ticker = result.get('ticker', 'N/A')
        total_return = result['summary']['total_return'] * 100
        sharpe = result['summary']['sharpe']

        ax.set_title(f'Equity Curve - {ticker}\nTotal Return: {total_return:.2f}% | Sharpe Ratio: {sharpe:.3f}',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Equity ($)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Date format
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Chart saved: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_trades_on_price(self, result: Dict[str, Any], save_path: Path = None):
        """Price Chart with Buy/Sell Signals"""
        trades = result.get('trades', [])
        if not trades:
            print("No trades found.")
            return

        # Extract data
        timestamps = [datetime.strptime(t['ts'], '%Y-%m-%d %H:%M:%S') for t in trades]
        prices = [t['price'] for t in trades]
        actions = [t['action'] for t in trades]

        # Separate buy/sell points
        buy_times = [timestamps[i] for i, a in enumerate(actions) if 'BUY' in a]
        buy_prices = [prices[i] for i, a in enumerate(actions) if 'BUY' in a]
        sell_times = [timestamps[i] for i, a in enumerate(actions) if 'SELL' in a]
        sell_prices = [prices[i] for i, a in enumerate(actions) if 'SELL' in a]

        # Create chart
        fig, ax = plt.subplots(figsize=(14, 6))

        # Price line
        ax.plot(timestamps, prices, linewidth=2, color='#333333', label='Price', zorder=1)

        # Buy/Sell markers
        if buy_times:
            ax.scatter(buy_times, buy_prices, color='green', marker='^', s=100,
                      label='Buy', zorder=3, edgecolors='darkgreen', linewidth=1.5)
        if sell_times:
            ax.scatter(sell_times, sell_prices, color='red', marker='v', s=100,
                      label='Sell', zorder=3, edgecolors='darkred', linewidth=1.5)

        # Labels and title
        ticker = result.get('ticker', 'N/A')
        trades_count = result['summary']['trades_count']

        ax.set_title(f'Price & Trade Signals - {ticker}\nTotal Trades: {trades_count}',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Price ($)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Date format
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Chart saved: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_drawdown(self, result: Dict[str, Any], save_path: Path = None):
        """Drawdown Chart - shows portfolio decline from peak"""
        trades = result.get('trades', [])
        if not trades:
            print("No trades found.")
            return

        # Extract data
        timestamps = [datetime.strptime(t['ts'], '%Y-%m-%d %H:%M:%S') for t in trades]
        equity_values = [t['equity'] for t in trades]

        # Calculate drawdown
        drawdowns = []
        peak = equity_values[0]

        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = ((equity - peak) / peak) * 100  # Percentage from peak
            drawdowns.append(drawdown)

        # Create chart
        fig, ax = plt.subplots(figsize=(14, 6))

        # Plot drawdown as area chart
        ax.fill_between(timestamps, drawdowns, 0,
                        where=np.array(drawdowns) <= 0,
                        color='red', alpha=0.3, label='Drawdown')
        ax.plot(timestamps, drawdowns, linewidth=2, color='darkred', label='Drawdown %')
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=1, alpha=0.5)

        # Mark maximum drawdown
        max_dd_idx = np.argmin(drawdowns)
        max_dd = drawdowns[max_dd_idx]
        max_dd_time = timestamps[max_dd_idx]

        ax.scatter([max_dd_time], [max_dd], color='darkred', s=150,
                  zorder=5, marker='v', edgecolors='black', linewidth=2,
                  label=f'Max Drawdown: {max_dd:.2f}%')

        # Labels and title
        ticker = result.get('ticker', 'N/A')
        max_dd_summary = result['summary']['max_drawdown_pct'] * 100

        ax.set_title(f'Drawdown Chart - {ticker}\nMaximum Drawdown: {max_dd_summary:.2f}%',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Drawdown (%)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Date format
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Chart saved: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_combined_dashboard(self, result: Dict[str, Any], save_path: Path = None):
        """Combined Dashboard (2 charts in one)"""
        trades = result.get('trades', [])
        if not trades:
            print("No trades found.")
            return

        # Prepare data
        timestamps = [datetime.strptime(t['ts'], '%Y-%m-%d %H:%M:%S') for t in trades]
        equity_values = [t['equity'] for t in trades]
        prices = [t['price'] for t in trades]
        actions = [t['action'] for t in trades]
        initial_capital = result['summary']['initial_capital']

        # Separate buy/sell points
        buy_times = [timestamps[i] for i, a in enumerate(actions) if 'BUY' in a]
        buy_prices = [prices[i] for i, a in enumerate(actions) if 'BUY' in a]
        sell_times = [timestamps[i] for i, a in enumerate(actions) if 'SELL' in a]
        sell_prices = [prices[i] for i, a in enumerate(actions) if 'SELL' in a]

        # Create 2 subplots
        fig = plt.figure(figsize=(16, 9))

        # Overall title
        ticker = result.get('ticker', 'N/A')
        total_return = result['summary']['total_return'] * 100
        sharpe = result['summary']['sharpe']
        max_dd = result['summary']['max_drawdown_pct'] * 100

        fig.suptitle(f'Backtest Dashboard - {ticker}\n'
                    f'Total Return: {total_return:.2f}% | Sharpe Ratio: {sharpe:.3f} | Max Drawdown: {max_dd:.2f}%',
                    fontsize=16, fontweight='bold', y=0.97)

        # 1. Equity Curve
        ax1 = plt.subplot(2, 1, 1)
        ax1.plot(timestamps, equity_values, linewidth=2, color='#2E86AB', label='Equity')
        ax1.axhline(y=initial_capital, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        ax1.fill_between(timestamps, equity_values, initial_capital,
                        where=np.array(equity_values) >= initial_capital,
                        alpha=0.3, color='green')
        ax1.fill_between(timestamps, equity_values, initial_capital,
                        where=np.array(equity_values) < initial_capital,
                        alpha=0.3, color='red')
        ax1.set_ylabel('Equity ($)', fontsize=12)
        ax1.set_title('Equity Curve', fontsize=13, fontweight='bold', pad=12)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # 2. Price & Trade Signals
        ax2 = plt.subplot(2, 1, 2)
        ax2.plot(timestamps, prices, linewidth=2, color='#333333', label='Price', zorder=1)
        if buy_times:
            ax2.scatter(buy_times, buy_prices, color='green', marker='^', s=100,
                       label='Buy', zorder=3, edgecolors='darkgreen', linewidth=1.5)
        if sell_times:
            ax2.scatter(sell_times, sell_prices, color='red', marker='v', s=100,
                       label='Sell', zorder=3, edgecolors='darkred', linewidth=1.5)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Price ($)', fontsize=12)
        ax2.set_title('Price & Trade Signals', fontsize=13, fontweight='bold', pad=12)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout(rect=[0, 0, 1, 0.95])

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Dashboard saved: {save_path}")
        else:
            plt.show()

        plt.close()

    def generate_all_charts(self, json_path: Path):
        """Generate and save all charts"""
        result = self.load_result(json_path)

        # Prepare save path
        base_name = json_path.stem
        output_dir = json_path.parent / 'charts'
        output_dir.mkdir(exist_ok=True)

        print(f"\nGenerating charts for: {result.get('ticker', 'N/A')}")

        # Generate individual charts
        self.plot_equity_curve(result, output_dir / f"{base_name}_equity.png")
        self.plot_trades_on_price(result, output_dir / f"{base_name}_trades.png")

        # Combined dashboard
        self.plot_combined_dashboard(result, output_dir / f"{base_name}_dashboard.png")

        print(f"\nAll charts generated! Saved to: {output_dir}")

        return output_dir
