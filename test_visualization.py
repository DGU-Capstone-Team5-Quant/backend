"""시각화 테스트 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from cli.visualization import BacktestVisualizer

# 테스트할 결과 파일 (최신)
import glob
result_files = sorted(glob.glob("results/backtest_*.json"), key=lambda x: Path(x).stat().st_mtime, reverse=True)
if result_files:
    result_file = Path(result_files[0])
else:
    result_file = Path("results/backtest_AAPL_42_20251209_174021.json")

if not result_file.exists():
    print(f"결과 파일을 찾을 수 없습니다: {result_file}")
    sys.exit(1)

print(f"차트 생성 중: {result_file}")

# Visualizer 생성
visualizer = BacktestVisualizer()

# 모든 차트 생성
try:
    output_dir = visualizer.generate_all_charts(result_file)
    print(f"\n✓ 성공! 차트 저장 위치: {output_dir}")
except Exception as e:
    print(f"\n✗ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
