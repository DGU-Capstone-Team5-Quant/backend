from __future__ import annotations

from typing import Any, Dict

import httpx
import pandas as pd

from config import Settings


class MarketDataLoader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.price_url = str(settings.price_endpoint)
        self.news_url = str(settings.news_endpoint)

    async def fetch_prices(self, ticker: str, window: int) -> pd.DataFrame:
        headers = {
            "X-RapidAPI-Key": self.settings.rapid_api_key,
            "X-RapidAPI-Host": self.settings.rapid_api_host,
        }
        params = {"symbol": ticker, "window": window}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.price_url, headers=headers, params=params)
                resp.raise_for_status()
                payload = resp.json()
                df = pd.DataFrame(payload.get("prices", []))
                if not df.empty:
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.set_index("date").sort_index()
                    return df
        except Exception:
            # 네트워크 불가/엔드포인트 미설정 시 샘플 시계열 생성
            pass

        dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=window, freq="D")
        data = {
            "close": pd.Series(range(window), index=dates).astype(float),
            "open": pd.Series(range(window), index=dates).astype(float),
            "high": pd.Series(range(window), index=dates).astype(float),
            "low": pd.Series(range(window), index=dates).astype(float),
            "volume": pd.Series([1000.0] * window, index=dates),
        }
        return pd.DataFrame(data)

    async def fetch_news(self, ticker: str, limit: int = 5) -> list[dict[str, Any]]:
        headers = {
            "X-RapidAPI-Key": self.settings.rapid_api_key,
            "X-RapidAPI-Host": self.settings.rapid_api_host,
        }
        params = {"symbol": ticker, "limit": limit}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.news_url, headers=headers, params=params)
                resp.raise_for_status()
                payload = resp.json()
                articles = payload.get("articles") or payload.get("news") or []
                return articles[:limit]
        except Exception:
            return [
                {"title": f"{ticker} placeholder headline", "summary": "시장 뉴스 데이터를 설정하세요.", "source": "stub"}
            ]

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        enriched = df.copy()
        enriched["sma_20"] = enriched["close"].rolling(window=20, min_periods=5).mean()
        enriched["sma_50"] = enriched["close"].rolling(window=50, min_periods=10).mean()
        enriched["rsi_14"] = self._rsi(enriched["close"], period=14)
        return enriched

    async def load_snapshot(self, ticker: str, window: int) -> Dict[str, Any]:
        prices = await self.fetch_prices(ticker, window)
        enriched = self.add_indicators(prices)
        latest = enriched.tail(1).to_dict(orient="records")[0]
        news = await self.fetch_news(ticker)
        return {
            "ticker": ticker,
            "window": window,
            "latest": latest,
            "news": news,
        }

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        return 100 - (100 / (1 + rs))
