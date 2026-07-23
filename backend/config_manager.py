"""
配置管理器：JSON 读写 + 档位参数查询 + API Key 加密存储
开发模式读写项目内 config/，冻结模式自动迁移到 %APPDATA%/etf-trader/
"""
import json
import os
import shutil
import sys
import base64

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except ImportError:
    HAS_FERNET = False

# ── 加密常量 ──
# 密钥派生：优先使用环境变量 ETF_ADVISOR_KEY，否则使用内置固定密钥
_ENCRYPTION_MARKER = "enc:"  # 前缀标记：加密后的值以此开头

# 冻结模式下的可写配置目录
_IS_FROZEN = getattr(sys, "frozen", False)
if _IS_FROZEN:
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "etf-trader")
    _BUNDLE_CONFIG = os.path.join(sys._MEIPASS, "config", "settings.json")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    _TARGET = os.path.join(CONFIG_DIR, "settings.json")
    if os.path.exists(_BUNDLE_CONFIG) and not os.path.exists(_TARGET):
        shutil.copy2(_BUNDLE_CONFIG, _TARGET)
else:
    CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

# ── 全局默认值：所有模块统一从 DEFAULTS 取回退值，不再各自硬编码路径 ──
DEFAULTS = {
    "llm_provider": "deepseek",
    "llm_model": "deepseek-chat",
    "llm_api_key": "",
    "risk_profile": "standard",
    "default_etf": "510050",
    "default_period": "short",
    "default_days": 60,
    "max_bars": 200,
    "data_source": "baostock",
    "data_source_token": "",
    "sentiment_dir": "",         # 板块舆情文件路径（GUI 中用 get_setting 取，首次空时引导浏览）
    "output_dir": "",            # 决策报告保存目录（空时 GUI 自动回退到项目 output/）
}


# ── 加密工具 ──

def _derive_fernet() -> 'Fernet | None':
    """派生 Fernet 实例。优先环境变量 ETF_ADVISOR_KEY (base64 32-byte key)，
    否则用内置固定密钥（提供基本混淆，防肉眼查看）。"""
    if not HAS_FERNET:
        return None
    env_key = os.environ.get("ETF_ADVISOR_KEY", "")
    if env_key:
        try:
            return Fernet(env_key.encode("utf-8"))
        except Exception:
            pass
    # 固定密钥 — 注意这不是真正的安全方案，仅防明文浏览
    _FIXED_KEY = b"T2jhx9LfQ3mYK1uB8pR6vZ0sN4wE7aC_b5dFgHkXyVc="
    return Fernet(_FIXED_KEY)


def _encrypt_value(plaintext: str) -> str:
    """加密纯文本，返回带标记的密文字符串"""
    f = _derive_fernet()
    if f is None:
        return plaintext
    encrypted = f.encrypt(plaintext.encode("utf-8"))
    return _ENCRYPTION_MARKER + base64.urlsafe_b64encode(encrypted).decode("ascii")


def _decrypt_value(ciphertext: str) -> str | None:
    """解密带标记的密文，失败返回 None"""
    if not ciphertext or not ciphertext.startswith(_ENCRYPTION_MARKER):
        return None
    f = _derive_fernet()
    if f is None:
        return None
    try:
        raw = base64.urlsafe_b64decode(ciphertext[len(_ENCRYPTION_MARKER):])
        return f.decrypt(raw).decode("utf-8")
    except Exception:
        return None


# ── 读写 ──

def _read() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write(data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_setting(key: str, default=None):
    data = _read()
    # API Key 透明解密：如果存储的是加密值，自动解密
    if key == "llm_api_key":
        raw = data.get(key, "")
        if raw and raw.startswith(_ENCRYPTION_MARKER):
            decrypted = _decrypt_value(raw)
            if decrypted is not None:
                return decrypted
            # 解密失败回退到明文
            return raw if not raw.startswith(_ENCRYPTION_MARKER) else (default or "")
        # 明文存储（旧配置）→ 自动迁移加密
        if raw and HAS_FERNET:
            encrypted = _encrypt_value(raw)
            data[key] = encrypted
            _write(data)
        return raw if raw else (default if default is not None else "")
    val = data.get(key)
    if val is None:
        return default if default is not None else DEFAULTS.get(key)
    return val


def set_setting(key: str, value):
    data = _read()
    # API Key 自动加密存储
    if key == "llm_api_key" and value:
        data[key] = _encrypt_value(value)
    else:
        data[key] = value
    _write(data)


def get_risk_params(profile: str = None) -> dict:
    if profile is None:
        profile = get_setting("risk_profile", "standard")
    risk_map = get_setting("risk_params", {})
    return risk_map.get(profile, risk_map.get("standard", {}))
