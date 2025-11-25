from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
import pandas as pd

from config import Settings


class MarketDataLoader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.price_url_intraday = str(settings.price_endpoint_intraday or settings.price_endpoint)
        self.price_url_daily = str(settings.price_endpoint_daily or settings.price_endpoint)
        self.news_url = str(settings.news_endpoint)

    async def fetch_prices(
        self,
        ticker: str,
        window: int,
        *,
        mode: str = "intraday",
        interval: str = "1hour",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        headers = {
            "X-RapidAPI-Key": self.settings.rapid_api_key,
            "X-RapidAPI-Host": self.settings.rapid_api_host,
        }
        params: Dict[str, Any] = {"symbol": ticker}
        if mode == "intraday":
            params.update({"interval": interval, "window": window})
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date

        url_template = self.price_url_intraday if mode == "intraday" else self.price_url_daily
        url = url_template.format(symbol=ticker, interval=interval)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                payload = resp.json()
                records = self._parse_price_payload(payload, mode=mode)
                df = pd.DataFrame(records)
                if not df.empty:
                    if "date" in df.columns:
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

    async def fetch_news(self, ticker: str, limit: int = 5, page: int = 0) -> list[dict[str, Any]]:
        headers = {
            "X-RapidAPI-Key": self.settings.rapid_api_key,
            "X-RapidAPI-Host": self.settings.rapid_api_host,
        }
        params = {"tickers": ticker, "limit": limit, "page": page}
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

    async def load_snapshot(
        self,
        ticker: str,
        window: int,
        *,
        mode: str = "intraday",
        interval: str = "1hour",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        news_limit: int = 5,
        news_page: int = 0,
    ) -> Dict[str, Any]:
        prices = await self.fetch_prices(
            ticker,
            window,
            mode=mode,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
        )
        enriched = self.add_indicators(prices)
        latest = enriched.tail(1).to_dict(orient="records")[0]
        news = await self.fetch_news(ticker, limit=news_limit, page=news_page)
        return {
            "ticker": ticker,
            "window": window,
            "mode": mode,
            "interval": interval,
            "from": start_date,
            "to": end_date,
            "latest": latest,
            "news": news,
        }

    @staticmethod
    def _parse_price_payload(payload: Dict[str, Any], mode: str) -> list[dict[str, Any]]:
        """
        FMP 계열 페이로드를 날짜/가격 컬럼으로 정규화합니다.
        """
        if isinstance(payload, list):
            return payload
        if mode == "intraday":
            return payload.get("historical", payload.get("results", [])) or payload.get("prices", [])
        if mode == "daily":
            historical = payload.get("historical", [])
            if historical:
                return historical
        return payload.get("prices", [])

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        return 100 - (100 / (1 + rs))
