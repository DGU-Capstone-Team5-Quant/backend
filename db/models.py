from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    summary: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    simulation_id: Mapped[str] = mapped_column(String(64), ForeignKey("simulations.id"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    window: Mapped[int] = mapped_column(default=0)
    step: Mapped[int] = mapped_column(default=1)
    start_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backtest_id: Mapped[str] = mapped_column(String(64), ForeignKey("backtests.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    action: Mapped[str] = mapped_column(String(16))
    price: Mapped[float] = mapped_column()
    position: Mapped[float] = mapped_column()
    pnl: Mapped[float] = mapped_column()
    cumulative_pnl: Mapped[float] = mapped_column()


class SimulationFeedback(Base):
    __tablename__ = "simulation_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    simulation_id: Mapped[str] = mapped_column(String(64), ForeignKey("simulations.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)

    # 의사결정 시점 정보
    decision_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[float] = mapped_column()
    decision: Mapped[str] = mapped_column(Text())
    report: Mapped[str] = mapped_column(Text())

    # 추적 기간 설정
    check_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # 실제 결과 (나중에 업데이트)
    actual_price: Mapped[Optional[float]] = mapped_column(nullable=True)
    actual_return: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_checked: Mapped[bool] = mapped_column(default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
