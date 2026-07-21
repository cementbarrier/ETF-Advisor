"""
持仓获取：优先 easytrader 自动读取，降级手动输入
"""
from typing import Optional
from backend.config_manager import get_setting


def get_positions_from_ths() -> list[dict]:
    """
    通过 easytrader 从同花顺客户端读取持仓。
    返回: [{"code": "510050", "name": "上证50ETF", "cost": 3.05, "qty": 10000}, ...]
    失败返回空列表。
    """
    try:
        import easytrader
    except ImportError:
        return []

    ths_path = get_setting("ths_xiadan_path", r"C:\同花顺软件\xiadan.exe")

    try:
        user = easytrader.use("ths")
        user.connect(ths_path)
    except Exception:
        return []

    try:
        raw = user.position
    except Exception:
        return []

    if raw is None or (hasattr(raw, "empty") and raw.empty):
        return []

    positions = []
    try:
        import pandas as pd
        if isinstance(raw, pd.DataFrame):
            for _, row in raw.iterrows():
                code = str(row.get("证券代码", "")).strip()
                if not code:
                    continue
                # ETF 通常以 5/1/5 开头
                if not (code.startswith("5") or code.startswith("1") or code.startswith("5")):
                    # 非 ETF 也保留，交由 LLM 判断
                    pass
                positions.append({
                    "code": code,
                    "name": str(row.get("证券名称", "")).strip(),
                    "cost": float(row.get("成本价", 0)),
                    "qty": int(float(row.get("股票余额", 0))),
                    "market_value": float(row.get("市值", 0)),
                    "pnl_pct": round(float(row.get("盈亏比例", 0) or 0), 2) if "盈亏比例" in row else None,
                })
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    positions.append(item)
    except Exception:
        return []

    return positions


def format_positions_for_prompt(positions: list[dict]) -> str:
    """将持仓列表格式化为 LLM prompt 文本"""
    if not positions:
        return "无持仓信息"

    lines = []
    total_value = 0
    for p in positions:
        code = p.get("code", "?")
        name = p.get("name", "")
        cost = p.get("cost", 0)
        qty = p.get("qty", 0)
        mv = p.get("market_value", 0)
        pnl = p.get("pnl_pct")
        total_value += mv

        label = f"{code} {name}".strip()
        line = f"- {label}: 成本 {cost}, 持有 {qty} 份, 市值 {mv:.0f}"
        if pnl is not None:
            line += f" (浮盈 {pnl:+.2f}%)"
        lines.append(line)

    if total_value > 0:
        lines.append(f"持仓总市值: {total_value:.0f}")

    return "\n".join(lines)
