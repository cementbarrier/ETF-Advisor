"""
持仓获取：优先 easytrader 自动读取，降级手动输入
"""
from backend.config_manager import get_setting


def get_positions_from_ths() -> dict:
    """
    通过 easytrader 从同花顺客户端读取持仓。
    返回: {"success": True, "data": [...]} 或 {"success": False, "error": "原因"}
    """
    # 1. 检查 easytrader 是否安装
    try:
        import easytrader
    except ImportError:
        return {"success": False, "data": [], "error": "easytrader 未安装，请执行 pip install easytrader"}

    ths_path = get_setting("ths_xiadan_path", r"C:\同花顺软件\xiadan.exe")

    # 2. 检查下单程序路径是否存在
    import os
    if not os.path.exists(ths_path):
        return {
            "success": False,
            "data": [],
            "error": f"找不到同花顺下单程序，请确认路径: {ths_path}\n可在 config/settings.json 中设置 ths_xiadan_path",
        }

    # 3. 连接同花顺
    try:
        user = easytrader.use("ths")
        user.connect(ths_path)
    except Exception as e:
        msg = str(e).split("\n")[0][:120]
        return {
            "success": False,
            "data": [],
            "error": f"连接同花顺失败: {msg}\n请确认: ①同花顺已登录运行 ②窗口未最小化 ③xiadan.exe 已启动",
        }

    # 4. 读取持仓
    try:
        raw = user.position
    except Exception as e:
        msg = str(e).split("\n")[0][:120]
        return {"success": False, "data": [], "error": f"读取持仓失败: {msg}"}

    if raw is None or (hasattr(raw, "empty") and raw.empty):
        return {"success": True, "data": [], "error": ""}

    # 5. 解析持仓数据
    positions = []
    try:
        import pandas as pd
        if isinstance(raw, pd.DataFrame):
            for _, row in raw.iterrows():
                code = str(row.get("证券代码", "")).strip()
                if not code:
                    continue
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
    except Exception as e:
        return {"success": False, "data": [], "error": f"解析持仓数据失败: {e}"}

    return {"success": True, "data": positions, "error": ""}


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
