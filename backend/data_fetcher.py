"""
行情数据获取：baostock ETF 历史 K 线
"""
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import baostock as bs


def _ensure_login():
    """确保 baostock 已登录（幂等）"""
    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")


def _symbol_to_code(symbol: str) -> str:
    """ETF 代码转为 baostock 格式：510050 -> sh.510050"""
    s = symbol.strip()
    if s.startswith("5") or s.startswith("6"):
        return f"sh.{s}"
    else:
        return f"sz.{s}"


def fetch_etf_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """获取 ETF 日 K 线，返回最近 count 条"""
    _ensure_login()
    code = _symbol_to_code(symbol)
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=count * 2)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=start, end_date=end,
        frequency="d", adjustflag="2"
    )
    if rs.error_code != '0':
        raise RuntimeError(f"baostock 查询失败: {rs.error_msg}")

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").tail(count).reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.dropna(subset=["close"])


def fetch_etf_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """获取 ETF 分钟 K 线（baostock 支持 5/15/30/60）"""
    _ensure_login()
    code = _symbol_to_code(symbol)
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=count)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        code, "date,time,open,high,low,close,volume",
        start_date=start, end_date=end,
        frequency=period, adjustflag="2"
    )
    if rs.error_code != '0':
        raise RuntimeError(f"baostock 分钟查询失败: {rs.error_msg}")

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=["date", "time", "open", "high", "low", "close", "volume"])
    # baostock 分钟线 time 字段格式为 YYYYMMDDHHMMSSmmm，直接解析
    df["date"] = pd.to_datetime(df["time"], format="%Y%m%d%H%M%S%f", errors="coerce")
    df = df.drop(columns=["time"]).sort_values("date").tail(count).reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.dropna(subset=["close"])
