# ETF-Advisor 项目上下文（2026-07-23）

## 项目概述

ETF-Advisor——配合同花顺软件使用的交易参考工具，基于多因子技术分析 + LLM 决策，输出买入/卖出/观望参考建议。配套项目 BiliDigest（B站视频字幕提取与AI摘要）。

**路径**：`E:\etf-trader`  
**入口**：`gui.py`，PyInstaller 打包为 `E:\etf-trader\dist\gui.exe`  
**桌面快捷方式**：`ETF-Advisor` → `E:\etf-trader\dist\gui.exe`

---

## 核心架构

| 模块 | 路径 | 职责 |
|------|------|------|
| GUI | `gui.py` | Tkinter 主界面，参数输入、持仓管理、分析触发、结果展示 |
| 行情 | `backend/data_fetcher.py` | 多数据源切换（baostock / akshare），历史日线 + 实时行情 |
| 因子 | `backend/factor_engine.py` | 多因子技术指标计算流水线 |
| LLM 决策 | `backend/llm_decision.py` | 构造 prompt、调用 LLM、解析 JSON 结果 |
| 持仓读取 | `backend/position_fetcher.py` | 同花顺 easytrader 持仓 + 资金快照 |
| 配置 | `backend/config_manager.py` | JSON 配置读写，冻结模式自动迁到 %APPDATA%/etf-trader |
| 打包 | `gui.spec` | PyInstaller 规格文件，含 akshare file_fold 数据 + certifi 证书 |

## LLM 决策输入来源

分析时 `decide()` 接收以下信息：
- **技术面**：`factor_engine.run_factor_pipeline()` 输出的趋势/信号/因子数组
- **持仓**：同花顺实际持仓（代码、成本、数量），`position_fetcher.format_positions_for_prompt()`
- **资金**：同花顺账户余额，`position_fetcher.format_balance_for_prompt()`
- **板块舆情**：从 `gui.py` 中 `_load_sentiment()` 读取外部 txt 文件，作为 LLM 额外情绪参考
- **周期**：用户输入的 1-365 天
- **风险档位**：conservative / standard / aggressive

---

## 全部已修复/新增（共 17 项）

### 数据源（2026-07-23）
| # | 变更 | 说明 |
|---|------|------|
| 15 | 可切换数据源 | GUI 新增数据源下拉框（baostock / akshare），配置键 `data_source`，可选 token 输入（为付费源预留） |
| 16 | 冻结环境 SSL 证书 | Frozen EXE 中 `data_fetcher.py` 启动时设置 `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` 指向 certifi，解决 akshare 联网 SSL 报错 |
| 17 | 代理强制禁用 | `data_fetcher.py` 启动时清空所有代理环境变量，避免系统代理干扰 akshare 直连 |

### 打包修复
| # | 变更 | 说明 |
|---|------|------|
| 13 | akshare 数据打包 | gui.spec 的 `datas` 中 `Tree('site-packages/akshare/file_fold')` 动态路径，适配任意 Python 3.11 环境 |
| 14 | spec collect_submodules | gui.spec 添加 `collect_submodules` 递归收集受隐藏 import 的模块 |

### 2026-07-22

| # | 变更 | 说明 |
|---|------|------|
| 1 | 持仓读取增强 | 空仓时读取资金；`_normalize_balance()` 兼容 dict/DataFrame；GUI 新增可用资金/总资产输入框 |
| 2 | LLM 输出中文化 | buy→买入, sell→卖出, hold→观望, bullish→看涨, bearish→看跌, neutral→震荡 |
| 3 | LLM 决策输出增强 | 新增 `entry_zone`、`exit_zone`、`position_ratio`、`reasoning` 字段；GUI 树形分区展示 |
| 4 | reasoning 换行修复 | Prompt 层要求每条独占一行；GUI 正则兜底拆分编号文本 |
| 5 | 周期改为输入天数 | `short`/`long` 下拉框 → Spinbox 1-365 天 |
| 6 | 行情补充实时行情 | akshare `fund_etf_spot_em()` 补充当日实时数据；baostock 缺今日数据时自动追加 |
| 7 | EXE 打包：akshare calendar.json 缺失 | gui.spec datas 添加 akshare file_fold 目录 |
| 8 | EXE 打包：tqdm stderr NoneType 崩溃 | `data_fetcher.py` 首行 `os.environ.setdefault("TQDM_DISABLE", "1")` |
| 9 | 板块舆情联动 | `_load_sentiment()` 自动读取批次总结文件，传入 `decide()` |
| 10 | 舆情目录可配置 | GUI 输入框 + 浏览按钮，`askopenfilename` 过滤 *.txt；兼容旧目录模式 |
| 11 | GitHub 仓库创建 | `https://github.com/cementbarrier/ETF-Trader`，13+ commits |
| 12 | 独立 venv + setup.bat | `.venv` 独立虚拟环境；`requirements.txt` 完整覆盖；`setup.bat` 一键初始化 |

---

## 关键设计决策

- **数据源默认 baostock**：免费稳定，akshare 作为备选。数据源 token 字段为未来付费源预留，当前留空即可。
- **冻结环境 SSL**：PyInstaller 打包后系统证书不可用，必须通过 certifi 提供证书，并在启动时设置环境变量（在 import akshare 之前）。
- **代理处理**：`os.environ` 清空所有代理变量，确保 akshare 内部新建 session 不会被系统代理干扰。
- **spec 动态路径**：akshare `file_fold` 的 datas 路径使用 `Tree()`，不硬编码 Marvis 运行时绝对路径。
- **窗口化 EXE 兼容**：冻结为 windowed EXE 时 `sys.stderr = None`，akshare/tqdm 写 stderr 会崩溃，需 `TQDM_DISABLE=1`。

---

## 构建与部署

### 开发模式运行
```powershell
python E:\etf-trader\gui.py
```

### 构建 EXE
```powershell
cd E:\etf-trader
Get-Process -Name "gui" -ErrorAction SilentlyContinue | Stop-Process -Force
# 用 delete 工具清理 build 和 dist/gui.exe
python -m PyInstaller gui.spec --distpath dist --workpath build --clean --noconfirm
# 验证：exe 时间戳 > 源码时间戳
```

### EXE 输出
- 单文件：`E:\etf-trader\dist\gui.exe`（~50MB）
- 配置：冻结模式自动迁至 `%APPDATA%\etf-trader\settings.json`

### Python 环境
- 路径：`D:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.349\runtime\python311\python.exe`
- PyInstaller：6.21.0

### 一键搭建
```batch
git clone https://github.com/cementbarrier/ETF-Trader.git
cd ETF-Trader
setup.bat
```

---

## 已知问题 / 待办

1. **akshare 实时行情稳定性** — 依赖 akshare `fund_etf_spot_em()` 接口，外部依赖不可控
2. **同花顺 easytrader 依赖** — 需要同花顺客户端运行中才能读取持仓

---

## 相关项目

- `E:\stock-tool` — BiliDigest，产出视频批次总结（用作本工具的板块舆情输入）
- `E:\video2txt` — 批次总结输出目录
