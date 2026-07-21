"""
行情数据获取：akshare ETF 历史 K 线
"""
from typing import Optional
import pandas as pd


def fetch_etf_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """
    获取 ETF 日线 K 线数据。
    返回 DataFrame，包含列: date, open, high, low, close, volume
    """
    try:
        import akshare as ak
        # akshare 基金 ETF 历史行情
        df = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust="qfq")
        if df.empty:
            return None
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume"
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").tail(count).reset_index(drop=True)
        # 确保数值列类型正确
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
        return df.dropna(subset=["close"])
    except ImportError:
        raise ImportError("请先安装 akshare: pip install akshare")
    except Exception as e:
        raise RuntimeError(f"获取 {symbol} 行情失败: {e}")


def fetch_etf_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """
    获取 ETF 分钟级 K 线。
    period: '60' 或 '30'
    """
    try:
        import akshare as ak
        df = ak.fund_etf_hist_em(symbol=symbol, period=period, adjust="qfq")
        if df.empty:
            return None
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume"
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").tail(count).reset_index(drop=True)
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
        return df.dropna(subset=["close"])
    except ImportError:
        raise ImportError("请先安装 akshare: pip install akshare")
    except Exception as e:
        raise RuntimeError(f"获取 {symbol} {period}分钟K线失败: {e}")
