# 项目交接文档 — ETF Trader & Stock Tool

**日期**: 2026-07-22  
**会话**: 当前窗口最后一个任务：stock-tool 新增 JSON 输出

---

## 一、涉及的两个项目

| 项目 | 路径 | GitHub | 定位 |
|------|------|--------|------|
| ETF Trader | `E:\etf-trader` | https://github.com/cementbarrier/ETF-Trader | ETF 多因子分析 + LLM 决策 |
| Stock Tool | `E:\stock-tool` | 待创建 | 板块视频分析 → 批次总结 |

---

## 二、本次会话完成的工作

### ETF Trader（共 12 项变更）

1. 持仓读取增强 — 空仓时读取资金，dict/DataFrame 兼容
2. LLM 输出中文化 — buy/sell/hold → 中文
3. LLM 决策输出增强 — 新增 entry_zone / exit_zone / position_ratio / reasoning
4. 输出排版重构 — 树形分区展示
5. reasoning 换行修复 — Prompt + 正则兜底
6. 周期改为输入天数 — Spinbox 1-365 天
7. 行情数据补充实时行情 — akshare 实时行情追加
8. EXE 打包修复：calendar.json 缺失
9. EXE 打包修复：tqdm stderr NoneType 崩溃
10. 板块舆情联动 — 读取 Stock Tool 输出的 batch summary txt
11. 舆情配置：目录输入 → 浏览文件夹 → 直接选 txt 文件
12. LLM 决策结果自动保存到指定目录

**仓库**：已创建 GitHub 仓库并推送，13 个 commits。  
**详细变更清单**见 `E:\etf-trader\SESSION_CONTEXT.md`

### Stock Tool（本次会话最后一项目）

13. **批次总结新增 JSON 输出** — `batch_parser.py` 的 `_generate_batch_summary()` 函数中，在写入 txt 后新增 Markdown 表格解析，同时生成 `批次总结_{date}.json`

**JSON 结构**：
```json
{
  "date": "2026-07-22",
  "video_count": 22,
  "videos": [{"bvid": "BV...", "opinion": "..."}],
  "entry_signals": [{"sector": "半导体/科创50", "reason": "底部放量反转..."}],
  "raw_text": "完整原始文本"
}
```

---

## 三、两个项目当前的关键文件

### ETF Trader 核心文件

| 文件 | 作用 |
|------|------|
| `gui.py` | Tkinter 主界面，含 `_load_sentiment()` 读取 Stock Tool 舆情 |
| `backend/llm_decision.py` | LLM prompt 构建，含 `{sentiment}` 占位符 |
| `backend/data_fetcher.py` | baostock + akshare 行情，含 `TQDM_DISABLE` 修复 |
| `backend/position_fetcher.py` | 同花顺持仓读取 |
| `gui.spec` | PyInstaller 打包配置，含 akshare file_fold 数据 |
| `config/settings.json` | 运行时配置（API Key、默认ETF、舆情文件路径等） |

### Stock Tool 核心文件

| 文件 | 作用 |
|------|------|
| `backend/batch_parser.py` | 批次总结生成，**已改造**：同时输出 txt + JSON |
| `backend/single_summary_client.py` | 单视频 AI 摘要 + 事实核实 |
| `backend/time_price_judge.py` | 时间-价格判断 |
| `gui/build/gui.py` | 主界面 |
| `scripts/run_pipeline.py` | 命令行流水线入口 |

### 数据管道

```
Stock Tool (E:\stock-tool)
  └─ backend/batch_parser.py
       └─ 输出: E:\video2txt\批次总结_{date}.txt  ← 用户阅读
       └─ 输出: E:\video2txt\批次总结_{date}.json ← ETF Trader 消费（新）
                      │
                      ▼
ETF Trader (E:\etf-trader)
  └─ gui.py 中 _load_sentiment()
       └─ 读取 txt 文件 → 注入 LLM prompt 的 {sentiment} 占位符
       └─ 待改造：优先读取 JSON 而非 txt
```

---

## 四、建议后续任务

### 优先级 1：ETF Trader 消费 JSON

修改 `gui.py` 的 `_load_sentiment()` 函数，让它优先读取 `批次总结_{date}.json`，解析结构化字段（videos / entry_signals）注入 LLM，比现在读纯 txt 更精准。

### 优先级 2：Stock Tool 创建 GitHub 仓库

`E:\stock-tool` 目前没有远程仓库，建议创建并推送。

### 优先级 3：统一 GUI（可选）

将两个项目合并为一个统一界面，左侧 ETF 决策 + 右侧板块舆情。

---

## 五、环境信息

- Python: `D:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.349\runtime\python311\python.exe`
- 工作目录: `E:\etf-trader`
- 桌面快捷方式: `ETF Trader` → `E:\etf-trader\dist\gui.exe`

---

## 六、新窗口提示词建议

复制以下内容，在新对话窗口粘贴即可接续：

> 我继续之前的项目开发。请先读取 E:\etf-trader\SESSION_CONTEXT.md 和 E:\etf-trader\README.md 了解 ETF Trader 项目全貌。然后读取 E:\stock-tool\backend\batch_parser.py 了解批次总结的 JSON 输出格式。  
>
> 第一个任务：修改 ETF Trader 的 gui.py 中 _load_sentiment() 函数，让它优先读取 stock-tool 生成的 JSON 文件（E:\video2txt\批次总结_*.json），解析 videos 和 entry_signals 字段，构造结构化的板块舆情信息注入 LLM 决策。如果 JSON 不存在则 fallback 到 txt。
