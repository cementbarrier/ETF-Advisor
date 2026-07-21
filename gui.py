"""
ETF 交易决策系统 - tkinter GUI
"""
import sys
import os
import threading
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import tkinter as tk
from tkinter import ttk, scrolledtext

from backend.config_manager import get_setting, set_setting, get_risk_params
from backend.data_fetcher import fetch_etf_daily
from backend.factor_engine import run_factor_pipeline
from backend.llm_decision import decide


def _log(msg: str):
    if hasattr(_log, "widget") and _log.widget:
        _log.widget.insert(tk.END, msg + "\n")
        _log.widget.see(tk.END)


def _save_api_key(*_):
    """失焦时自动保存 API Key"""
    key = api_var.get().strip()
    if key:
        set_setting("llm_api_key", key)
        status.config(text="API Key 已保存")
    else:
        status.config(text="请填写 API Key")


def _run_analysis():
    btn.config(state="disabled", text="分析中...")

    symbol = etf_var.get().strip()
    period = period_var.get()
    risk = risk_var.get()

    # 确保最新 API Key 已保存
    _save_api_key()

    try:
        _log(f"=== {symbol} {period} {risk} ===")
        _log("[1/3] 获取行情...")

        max_bars = get_setting("max_bars", 200)
        df = fetch_etf_daily(symbol, count=max_bars)
        if df is None or df.empty:
            _log(f"错误: 无法获取 {symbol} 行情数据")
            return

        _log(f"  获取 {len(df)} 条数据, 最新 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")

        _log("[2/3] 计算技术指标...")
        risk_params = get_risk_params(risk)
        factor = run_factor_pipeline(df, risk_params)
        _log(f"  价格: {factor['price']}  趋势: {factor['trend']}")
        _log(f"  信号: {', '.join(factor['signals']) or '无'}")

        _log("[3/3] LLM 决策...")
        result = decide(symbol, factor, period=period, risk_profile=risk)

        if "error" in result:
            _log(f"错误: {result['error']}")
            return

        action = result.get("action", "hold").upper()
        _log("")
        _log(f"  ◆ 决策: {action}")
        _log(f"  ◆ 趋势: {result.get('trend', 'N/A')}")
        _log(f"  ◆ 置信度: {result.get('confidence', 'N/A')}")
        _log(f"  ◆ 当前价: {factor['price']}")
        _log(f"  ◆ 支撑: {result.get('support_price')}  压力: {result.get('resistance_price')}")
        _log(f"  ◆ 止损: {result.get('stop_loss_price')}  止盈: {result.get('take_profit_price')}")
        _log("─" * 40)

    except Exception as e:
        _log(f"异常: {e}")
    finally:
        btn.config(state="normal", text="开始分析")


def on_run():
    threading.Thread(target=_run_analysis, daemon=True).start()


# ── 界面 ──
root = tk.Tk()
root.title("ETF 交易决策")
root.geometry("700x580")
root.resizable(True, True)

top = ttk.Frame(root, padding=10)
top.pack(fill="x")

# Row 0: API Key
ttk.Label(top, text="API Key:").grid(row=0, column=0, sticky="w", padx=(0, 5))
api_var = tk.StringVar(value=get_setting("llm_api_key", ""))
api_entry = ttk.Entry(top, textvariable=api_var, width=55, show="*")
api_entry.grid(row=0, column=1, columnspan=6, sticky="ew")
api_entry.bind("<FocusOut>", _save_api_key)
api_entry.bind("<Return>", _save_api_key)

# Row 1: 参数
ttk.Label(top, text="ETF代码:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(8, 0))
etf_var = tk.StringVar(value=get_setting("default_etf", "510050"))
etf_entry = ttk.Entry(top, textvariable=etf_var, width=10)
etf_entry.grid(row=1, column=1, sticky="w", pady=(8, 0))

ttk.Label(top, text="周期:").grid(row=1, column=2, sticky="w", padx=(15, 5), pady=(8, 0))
period_var = tk.StringVar(value=get_setting("default_period", "short"))
period_cb = ttk.Combobox(top, textvariable=period_var, values=["short", "long"], state="readonly", width=8)
period_cb.grid(row=1, column=3, sticky="w", pady=(8, 0))

ttk.Label(top, text="档位:").grid(row=1, column=4, sticky="w", padx=(15, 5), pady=(8, 0))
risk_var = tk.StringVar(value=get_setting("risk_profile", "standard"))
risk_cb = ttk.Combobox(top, textvariable=risk_var, values=["conservative", "standard", "aggressive"], state="readonly", width=10)
risk_cb.grid(row=1, column=5, sticky="w", pady=(8, 0))

btn = ttk.Button(top, text="开始分析", command=on_run)
btn.grid(row=1, column=6, padx=(15, 0), sticky="w", pady=(8, 0))

# 输出区
output = scrolledtext.ScrolledText(root, font=("Consolas", 10), wrap="word", state="normal")
output.pack(fill="both", expand=True, padx=10, pady=(0, 10))
_log.widget = output

# 状态栏
status_text = "API Key 已就绪" if get_setting("llm_api_key", "") else "请填写 API Key"
status = ttk.Label(root, text=status_text, relief="sunken", anchor="w", padding=(5, 2))
status.pack(fill="x", side="bottom")

if __name__ == "__main__":
    root.mainloop()
