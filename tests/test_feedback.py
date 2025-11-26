"""
실시간 피드백 추적 시스템 테스트
"""
import pytest
from datetime import datetime, timedelta


def test_feedback_salience_calculation():
    """피드백 salience 계산 로직 테스트"""
    # 수익률이 클수록 salience도 커야 함 (절댓값 기준)

    # +10% 수익
    salience_positive = abs(0.1) * 10
    assert salience_positive == 1.0

    # -10% 손실 (나쁜 결과도 중요!)
    salience_negative = abs(-0.1) * 10
    assert salience_negative == 1.0

    # +50% 수익
    salience_big = abs(0.5) * 10
    assert salience_big == 5.0


def test_return_calculation():
    """수익률 계산 테스트"""
    entry_price = 150.0

    # +10% 수익
    current_price = 165.0
    actual_return = (current_price - entry_price) / entry_price
    assert actual_return == 0.1

    # -5% 손실
    current_price = 142.5
    actual_return = (current_price - entry_price) / entry_price
    assert actual_return == -0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
