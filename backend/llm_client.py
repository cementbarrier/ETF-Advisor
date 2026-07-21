"""
LLM 统一接口：调用 DeepSeek / 火山方舟
"""
import json
import urllib.request
from backend.config_manager import get_setting


def chat(prompt: str) -> str:
    """发送 prompt 到 LLM，返回回复文本"""
    provider = get_setting("llm_provider", "deepseek")
    api_key = get_setting("llm_api_key", "")
    model = get_setting("llm_model", "deepseek-chat")

    if not api_key:
        raise ValueError("API Key 未配置")

    if provider == "volcengine":
        return _volcengine_chat(api_key, model, prompt)
    return _deepseek_chat(api_key, model, prompt)


def _deepseek_chat(api_key: str, model: str, prompt: str) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,  # 低温度，减少随机性
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        body,
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _volcengine_chat(api_key: str, model: str, prompt: str) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        body,
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]
