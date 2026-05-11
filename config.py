"""
SecBot 统一模型配置
类似 Hermes 的多 provider 体系，同时支持本地/云端/第三方
"""

import os

# ==================== Provider 体系 ====================
# 每个 provider 是独立的 API 端点，配好后可以在菜单里切换
# 格式: "provider名字": { "base_url": "...", "api_key": "...", "model": "默认模型" }

PROVIDERS = {
    # ---- 本地 Ollama ----
    "ollama-local": {
        "type": "ollama",
        "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "api_key": "ollama",          # ollama 不需要 key，留空
        "model": os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"),
    },

    # ---- OpenAI 官方 ----
    "openai": {
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
    },

    # ---- Anthropic Claude ----
    "anthropic": {
        "type": "anthropic",
        "base_url": "https://api.anthropic.com",
        "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    },

    # ---- 自定义 vLLM / Groq / etc. (OpenAI 兼容) ----
    "vllm": {
        "type": "openai",            # 也是 OpenAI 兼容格式
        "base_url": os.environ.get("VLLM_BASE_URL", "https://your-vllm.example.com/v1"),
        "api_key": os.environ.get("VLLM_API_KEY", "EMPTY"),
        "model": os.environ.get("VLLM_MODEL", "qwen2.5-coder-7b"),
    },
}

# ==================== 当前选中的 Provider ====================
# 启动时默认使用哪个 provider
CURRENT_PROVIDER = os.environ.get("SECBOT_PROVIDER", "openai")

# ==================== 扫描配置 ====================
NMAP_SCAN_TYPE = os.environ.get("NMAP_SCAN_TYPE", "-sV -T4")
SCAN_TIMEOUT = int(os.environ.get("SCAN_TIMEOUT", "300"))
DEFAULT_PORTS = "1-1000,3389,3306,22,80,443,8080,8443,21,25,110,143"

# ==================== SQL注入配置 ====================
SQLI_DICT_FILE = os.path.join(os.path.dirname(__file__), "dicts", "sqli_payloads.txt")

# ==================== 暴力破解配置 ====================
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BRUTE_THREADS = int(os.environ.get("BRUTE_THREADS", "10"))
BRUTE_TIMEOUT = int(os.environ.get("BRUTE_TIMEOUT", "5"))

# ==================== 报告配置 ====================
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# ==================== 提示词模板配置 ====================
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")
