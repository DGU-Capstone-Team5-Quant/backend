from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
import feedparser
import httpx
import pandas as pd

from config import Settings


class MarketDataLoader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.price_url_intraday = str(settings.price_endpoint_intraday or settings.price_endpoint)
        self.price_url_daily = str(settings.price_endpoint_daily or settings.price_endpoint)
        self.news_url = str(settings.news_endpoint)
        self.logger = logging.getLogger(__name__)
        self._news_cache: Dict[tuple[str, int, int], tuple[float, list[dict[str, Any]]]] = {}
        self._price_cache: Dict[tuple[str, str, str, int, Optional[str], Optional[str]], tuple[float, pd.DataFrame]] = {}
        self._news_cache_ttl = 300.0  # seconds
        self._price_cache_ttl = 120.0  # seconds

    async def fetch_prices(
        self,
        ticker: str,
        window: int,
        *,
        mode: str = "intraday",
        interval: str = "1h",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        interval = self._normalize_interval(interval)
        cached_df = self._get_cached_price(ticker, mode, interval, window, start_date, end_date)
        if cached_df is not None:
            return cached_df

        headers: Dict[str, str] = {}
        if self.settings.rapid_api_key:
            headers["X-RapidAPI-Key"] = self.settings.rapid_api_key
        if self.settings.rapid_api_host:
            headers["X-RapidAPI-Host"] = self.settings.rapid_api_host

        params: Dict[str, Any] = {"symbol": ticker}
        if mode == "intraday":
            params.update({"interval": interval, "outputsize": window, "format": "JSON"})
        else:
            params.update({"interval": "1day", "outputsize": window, "format": "JSON"})
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
                try:
                    # Debug logging: truncate for readability
                    self.logger.info("price payload sample: %s", str(payload)[:800])
                except Exception:
                    pass
                records = self._parse_price_payload(payload, mode=mode)
                df = pd.DataFrame(records)
                if not df.empty:
                    if "date" in df.columns:
                        df["date"] = pd.to_datetime(df["date"])
                        df = df.set_index("date").sort_index()
                    self._set_cached_price(ticker, mode, interval, window, start_date, end_date, df)
                    return df
        except Exception as exc:
            # 네트워크 불가/엔드포인트 미설정 시 샘플 시계열 생성
            self.logger.warning("fetch_prices fallback to stub: %s", exc)

        dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=window, freq="D")
        data = {
            "close": pd.Series(range(window), index=dates).astype(float),
            "open": pd.Series(range(window), index=dates).astype(float),
            "high": pd.Series(range(window), index=dates).astype(float),
            "low": pd.Series(range(window), index=dates).astype(float),
            "volume": pd.Series([1000.0] * window, index=dates),
        }
        df_stub = pd.DataFrame(data)
        self._set_cached_price(ticker, mode, interval, window, start_date, end_date, df_stub)
        return df_stub

    async def fetch_news(self, ticker: str, limit: int = 5, page: int = 0) -> list[dict[str, Any]]:
        cached = self._get_cached_news(ticker, limit, page)
        if cached is not None:
            return cached

        headers = {
        }
        urls = [
            self.news_url.format(symbol=ticker),
            f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en",
        ]
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    resp = await client.get(url, headers=headers)
                    # Google News RSS는 302로 지역/언어 리디렉션이 걸릴 수 있어 follow_redirects=True로 강제.
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)
                    articles = []
                    for entry in feed.entries[:limit]:
                        summary_html = entry.get("summary", "")
                        summary_text = self._strip_html(summary_html)
                        articles.append(
                            {
                                "title": entry.get("title", ""),
                                "summary": summary_text,
                                "link": entry.get("link", ""),
                                "published": entry.get("published", ""),
                            }
                        )
                    if articles:
                        self._set_cached_news(ticker, limit, page, articles)
                        return articles
            except Exception as exc:
                self.logger.warning("fetch_news attempt failed (%s): %s", url, exc)
                continue

        stub = [
            {"title": f"{ticker} placeholder headline", "summary": "시장 뉴스 데이터를 설정하세요.", "source": "stub"}
        ]
        self._set_cached_news(ticker, limit, page, stub)
        return stub

    def _get_cached_news(self, ticker: str, limit: int, page: int) -> Optional[list[dict[str, Any]]]:
        key = (ticker, limit, page)
        item = self._news_cache.get(key)
        if not item:
            return None
        ts, data = item
        if time.monotonic() - ts <= self._news_cache_ttl:
            return data
        self._news_cache.pop(key, None)
        return None

    def _set_cached_news(self, ticker: str, limit: int, page: int, data: list[dict[str, Any]]) -> None:
        key = (ticker, limit, page)
        self._news_cache[key] = (time.monotonic(), data)

    def _get_cached_price(
        self,
        ticker: str,
        mode: str,
        interval: str,
        window: int,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Optional[pd.DataFrame]:
        key = (ticker, mode, interval, window, start_date, end_date)
        item = self._price_cache.get(key)
        if not item:
            return None
        ts, df = item
        if time.monotonic() - ts <= self._price_cache_ttl:
            return df
        self._price_cache.pop(key, None)
        return None

    def _set_cached_price(
        self,
        ticker: str,
        mode: str,
        interval: str,
        window: int,
        start_date: Optional[str],
        end_date: Optional[str],
        df: pd.DataFrame,
    ) -> None:
        key = (ticker, mode, interval, window, start_date, end_date)
        self._price_cache[key] = (time.monotonic(), df)

    @staticmethod
    def _strip_html(text: str) -> str:
        if not text:
            return ""
        try:
            return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
        except Exception:
            return text

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
        # Twelve Data 형태 지원: {"meta": {...}, "values": [{ "datetime": "...", "open": "...", ... }]}
        if "values" in payload and isinstance(payload["values"], list):
            values = []
            for item in payload["values"]:
                if not isinstance(item, dict):
                    continue
                date_key = item.get("datetime") or item.get("date")
                def _to_float(val: Any) -> float:
                    try:
                        return float(val)
                    except Exception:
                        return 0.0

                values.append(
                    {
                        "date": date_key,
                        "open": _to_float(item.get("open")),
                        "high": _to_float(item.get("high")),
                        "low": _to_float(item.get("low")),
                        "close": _to_float(item.get("close")),
                        "volume": _to_float(item.get("volume")),
                    }
                )
            return values

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
    def _normalize_interval(interval: str) -> str:
        mapping = {
            "1hour": "1h",
            "2hour": "2h",
            "4hour": "4h",
            "8hour": "8h",
            "1day": "1day",
            "1week": "1week",
            "1month": "1month",
        }
        if interval in mapping:
            return mapping[interval]
        return interval

    @staticmethod
    def _rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        return 100 - (100 / (1 + rs))
