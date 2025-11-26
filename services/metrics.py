from __future__ import annotations

import threading
import time
from typing import Dict


class MetricsTracker:
    """
    Lightweight in-memory metrics tracker for Prometheus-format exposition.
    Thread-safe enough for async usage via a simple lock.
    """

    def __init__(self) -> None:
        self.start_ts = time.time()
        self._lock = threading.Lock()
        self._counts: Dict[str, int] = {
            "simulation_success": 0,
            "simulation_failure": 0,
            "backtest_success": 0,
            "backtest_failure": 0,
            "feedback_success": 0,
            "feedback_failure": 0,
            "feedback_checked": 0,
        }
        self._duration_sum: Dict[str, float] = {"simulation": 0.0, "backtest": 0.0, "feedback": 0.0}
        self._duration_count: Dict[str, int] = {"simulation": 0, "backtest": 0, "feedback": 0}

    def record_simulation(self, *, success: bool, duration: float) -> None:
        with self._lock:
            self._counts["simulation_success" if success else "simulation_failure"] += 1
            self._duration_sum["simulation"] += duration
            self._duration_count["simulation"] += 1

    def record_backtest(self, *, success: bool, duration: float) -> None:
        with self._lock:
            self._counts["backtest_success" if success else "backtest_failure"] += 1
            self._duration_sum["backtest"] += duration
            self._duration_count["backtest"] += 1

    def record_feedback(self, *, success: bool, duration: float, checked_count: int = 0) -> None:
        with self._lock:
            self._counts["feedback_success" if success else "feedback_failure"] += 1
            self._counts["feedback_checked"] += max(0, checked_count)
            self._duration_sum["feedback"] += duration
            self._duration_count["feedback"] += 1

    def render_prometheus(self) -> str:
        with self._lock:
            uptime = int(time.time() - self.start_ts)
            lines = [f"app_uptime_seconds {uptime}"]

            # Simulation
            lines.append(f"simulation_requests_total {self._counts['simulation_success'] + self._counts['simulation_failure']}")
            lines.append(f"simulation_failures_total {self._counts['simulation_failure']}")
            lines.append(f"simulation_duration_seconds_sum {self._duration_sum['simulation']}")
            lines.append(f"simulation_duration_seconds_count {self._duration_count['simulation']}")

            # Backtest
            lines.append(f"backtest_requests_total {self._counts['backtest_success'] + self._counts['backtest_failure']}")
            lines.append(f"backtest_failures_total {self._counts['backtest_failure']}")
            lines.append(f"backtest_duration_seconds_sum {self._duration_sum['backtest']}")
            lines.append(f"backtest_duration_seconds_count {self._duration_count['backtest']}")

            # Feedback checks
            lines.append(f"feedback_checks_total {self._counts['feedback_success'] + self._counts['feedback_failure']}")
            lines.append(f"feedback_check_failures_total {self._counts['feedback_failure']}")
            lines.append(f"feedback_checks_checked_total {self._counts['feedback_checked']}")
            lines.append(f"feedback_check_duration_seconds_sum {self._duration_sum['feedback']}")
            lines.append(f"feedback_check_duration_seconds_count {self._duration_count['feedback']}")

            return "\n".join(lines) + "\n"


metrics_tracker = MetricsTracker()
