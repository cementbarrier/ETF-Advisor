"""
ETF 交易决策系统
用法: python run.py [ETF代码] [周期] [档位]

示例:
  python run.py 510050 short           # 上证50ETF，短线，标准档
  python run.py 159915 long aggressive # 创业板ETF，长线，激进档
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.config_manager import get_setting, get_risk_params
from backend.data_fetcher import fetch_etf_daily
from backend.factor_engine import run_factor_pipeline
from backend.llm_decision import decide

# period("short"/"long") → days 映射
_PERIOD_TO_DAYS = {
    "short": 30,
    "long": 90,
}


def run(symbol: str = None, period: str = None, risk: str = None):
    if symbol is None:
        symbol = get_setting("default_etf", "510050")
    if period is None:
        period = get_setting("default_period", "short")
    if risk is None:
        risk = get_setting("risk_profile", "standard")

    risk_params = get_risk_params(risk)
    max_bars = get_setting("max_bars", 200)
    days = _PERIOD_TO_DAYS.get(period, 60)

    print(f"=== ETF 交易决策 ===")
    print(f"标的: {symbol}  周期: {period}  档位: {risk}")
    print()

    # 1. 拉取行情数据
    print("[1/3] 获取行情数据...")
    try:
        df = fetch_etf_daily(symbol, count=max_bars)
        if df is None or df.empty:
            print(f"  错误: 无法获取 {symbol} 行情数据")
            return
        print(f"  获取 {len(df)} 条日线数据，最新日期 {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"  错误: {e}")
        return

    # 2. 计算技术指标（喂给 LLM 的上下文）
    print("[2/3] 计算技术指标...")
    factor_result = run_factor_pipeline(df, risk_params)
    print(f"  价格: {factor_result['price']}")
    print(f"  趋势: {factor_result['trend']}")
    print(f"  信号: {', '.join(factor_result['signals']) or '无'}")

    # 3. LLM 决策
    print("[3/3] LLM 决策中...")
    try:
        result = decide(symbol, factor_result, days=days, risk_profile=risk)
        if "error" in result:
            print(f"  LLM 解析异常: {result['error']}")
            return
    except Exception as e:
        print(f"  LLM 调用失败: {e}")
        print(f"  (请先在 config/settings.json 中设置 llm_api_key)")
        return

    print()
    print("=" * 50)
    print(f"  标的: {symbol}")
    print(f"  当前价: {factor_result['price']}")
    print(f"  决策: {result.get('action', 'N/A').upper()}")
    print(f"  趋势: {result.get('trend', 'N/A')}")
    print(f"  置信度: {result.get('confidence', 'N/A')}")
    print(f"  支撑: {result.get('support_price')}  压力: {result.get('resistance_price')}")
    print(f"  止损: {result.get('stop_loss_price')}  止盈: {result.get('take_profit_price')}")
    print("=" * 50)

    print()
    print("完整结果 JSON:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    period = sys.argv[2] if len(sys.argv) > 2 else None
    risk = sys.argv[3] if len(sys.argv) > 3 else None
    run(symbol, period, risk)
