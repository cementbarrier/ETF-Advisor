"""
行情数据获取：支持多数据源切换（baostock / akshare），可选 token 认证
"""
import os
import sys
os.environ.setdefault("TQDM_DISABLE", "1")

# 强制禁用代理（akshare 内部新建 session 可能绕开全局 patch）
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['NO_PROXY'] = '*'
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['no_proxy'] = '*'

# Frozen 环境下指向打包的 SSL 证书
if getattr(sys, 'frozen', False):
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
import threading
import pandas as pd

# 项目根目录（backend/ 的上一级）；冻结模式下为 EXE 所在目录
if getattr(sys, 'frozen', False):
    _PROJECT_ROOT = Path(sys.executable).parent
else:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent

# akshare 调用超时（秒）
_AKSHARE_TIMEOUT = 30


def _call_with_timeout(func, timeout: float = _AKSHARE_TIMEOUT):
    """在独立线程中执行 func()，超时抛 TimeoutError（防止 akshare 无超时卡死）"""
    result = {}

    def _worker():
        try:
            result["value"] = func()
        except Exception as e:
            result["error"] = e

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"调用超时（>{timeout}s）")
    if "error" in result:
        raise result["error"]
    return result.get("value")


# ── 数据源配置 ──

DATA_SOURCES = {
    "baostock": {
        "label": "baostock (免费，偶有网络波动)",
        "needs_token": False,
    },
    "akshare": {
        "label": "akshare (免费，东方财富数据)",
        "needs_token": False,
    },
}

_DEFAULT_SOURCE = "baostock"


def get_data_source():
    """从配置文件读取当前数据源"""
    from backend.config_manager import get_setting
    src = get_setting("data_source", _DEFAULT_SOURCE)
    if src not in DATA_SOURCES:
        src = _DEFAULT_SOURCE
    return src


def get_data_source_token():
    """读取数据源 token（仅付费源需要）"""
    from backend.config_manager import get_setting
    return get_setting("data_source_token", "")


# ── baostock 实现 ──

def _ensure_baostock_login():
    import baostock as bs
    lg = bs.login()
    if lg.error_code != '0':
        raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")


def _symbol_to_code(symbol: str) -> str:
    s = symbol.strip()
    if s.startswith("5") or s.startswith("6"):
        return f"sh.{s}"
    else:
        return f"sz.{s}"


def _fetch_baostock_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """baostock 日 K 线"""
    import baostock as bs
    _ensure_baostock_login()
    code = _symbol_to_code(symbol)
    today = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=count * 2)).strftime("%Y-%m-%d")

    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=start, end_date=today,
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
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.sort_values("date").tail(count).reset_index(drop=True).dropna(subset=["close"])


def _fetch_baostock_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """baostock 分钟 K 线"""
    import baostock as bs
    _ensure_baostock_login()
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
    df["date"] = pd.to_datetime(df["time"], format="%Y%m%d%H%M%S%f", errors="coerce")
    df = df.drop(columns=["time"]).sort_values("date").tail(count).reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.dropna(subset=["close"])


# ── akshare 实现 ──

def _fetch_akshare_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """akshare ETF 日 K 线"""
    import akshare as ak
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=count * 3)).strftime("%Y%m%d")

    df = ak.fund_etf_hist_em(symbol=symbol.strip(), period="daily",
                             start_date=start_date, end_date=end_date,
                             adjust="qfq")
    if df is None or df.empty:
        return None

    df = df.rename(columns={
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    })
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.sort_values("date").tail(count).reset_index(drop=True).dropna(subset=["close"])


def _fetch_akshare_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """akshare ETF 分钟 K 线"""
    import akshare as ak
    freq = {"5": "5", "15": "15", "30": "30", "60": "60"}
    period_key = freq.get(period, "60")

    df = ak.fund_etf_hist_min_em(symbol=symbol.strip(), period=period_key)
    if df is None or df.empty:
        return None

    df = df.rename(columns={
        "时间": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    })
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce")
    return df.sort_values("date").tail(count).reset_index(drop=True).dropna(subset=["close"])


# ── 统一入口 ──

def fetch_etf_daily(symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
    """获取 ETF 日 K 线（含今日实时行情），根据配置数据源路由。

    baostock 失败（登录/查询异常）时自动 fallback 到 akshare。
    """
    source = get_data_source()

    if source == "akshare":
        return _fetch_akshare_daily(symbol, count)

    # baostock 优先，失败自动切 akshare
    try:
        df = _fetch_baostock_daily(symbol, count)
    except Exception as e:
        _write_debug_log(f"baostock 日线获取失败，fallback 到 akshare: {e}")
        return _fetch_akshare_daily(symbol, count)

    if df is not None:
        last_date = df["date"].max()
        today = datetime.now().strftime("%Y-%m-%d")
        if last_date.strftime("%Y-%m-%d") != today:
            spot = _fetch_realtime_spot(symbol)
            if spot and spot['close'] > 0:
                new_row = pd.DataFrame([spot])
                new_row["date"] = pd.to_datetime(new_row["date"])
                df = pd.concat([df, new_row], ignore_index=True)
                df = df.sort_values("date").tail(count).reset_index(drop=True)
    else:
        # baostock 无数据，尝试 akshare 兜底
        _write_debug_log("baostock 日线返回空，fallback 到 akshare")
        return _fetch_akshare_daily(symbol, count)
    return df


def fetch_etf_minute(symbol: str, period: str = "60", count: int = 200) -> Optional[pd.DataFrame]:
    """获取 ETF 分钟 K 线，根据配置数据源路由。baostock 失败自动 fallback akshare"""
    source = get_data_source()

    if source == "akshare":
        return _fetch_akshare_minute(symbol, period, count)
    try:
        return _fetch_baostock_minute(symbol, period, count)
    except Exception as e:
        _write_debug_log(f"baostock 分钟线获取失败，fallback 到 akshare: {e}")
        return _fetch_akshare_minute(symbol, period, count)


def _write_debug_log(msg: str):
    """写入调试日志（项目根目录），路径不再硬编码到 E: 盘"""
    try:
        log_dir = _PROJECT_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "akshare.log"
        with open(str(log_path), "a", encoding="utf-8") as f:
            import traceback
            f.write(f"[{datetime.now()}] {msg}\n{traceback.format_exc() if 'Traceback' in str(msg) else ''}\n")
    except Exception:
        pass


def _fetch_realtime_spot(symbol: str) -> Optional[dict]:
    """akshare 实时行情（仅 baostock 模式兜底用），带 30s 超时保护"""
    try:
        import akshare as ak

        def _call():
            df = ak.fund_etf_spot_em()
            row = df[df['代码'] == symbol.strip()]
            if row.empty:
                return None
            r = row.iloc[0]
            today = datetime.now().strftime('%Y-%m-%d')
            return {
                'date': today,
                'open': float(r['开盘价']),
                'high': float(r['最高价']),
                'low': float(r['最低价']),
                'close': float(r['最新价']),
                'volume': int(r['成交量']),
            }

        return _call_with_timeout(_call)

    except Exception as e:
        _write_debug_log(f"akshare 实时行情获取失败: {e}")
        return None
