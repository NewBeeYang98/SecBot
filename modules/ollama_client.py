"""
SecBot 统一模型客户端
支持多 provider 体系: Ollama / OpenAI兼容 / Anthropic Claude
"""

import requests
from config import PROVIDERS, CURRENT_PROVIDER


class ModelClient:
    """
    类似 Hermes 的多 provider 模型客户端
    - 自动路由到对应 provider
    - 支持切换 provider
    - 统一的 generate / chat 接口
    """

    def __init__(self, provider_name=None):
        self.provider_name = provider_name or CURRENT_PROVIDER
        self._provider = PROVIDERS.get(self.provider_name)
        if not self._provider:
            raise ValueError(f"未知的 provider: {self.provider_name}")

    @property
    def ptype(self):
        return self._provider.get("type", "openai")

    @property
    def base_url(self):
        return self._provider.get("base_url", "")

    @property
    def api_key(self):
        return self._provider.get("api_key", "")

    @property
    def model(self):
        return self._provider.get("model", "")

    @property
    def label(self):
        return f"{self.provider_name} ({self.model})"

    # -------------------- 状态检测 --------------------

    def check_status(self):
        """检测当前 provider 是否可用"""
        ptype = self.ptype
        try:
            if ptype == "ollama":
                return self._check_ollama()
            elif ptype == "anthropic":
                return self._check_anthropic()
            else:  # openai compatible
                return self._check_openai()
        except Exception as e:
            return False, str(e)

    def _check_ollama(self):
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                return True, f"在线 | 可用模型: {', '.join(models) if models else '无'}"
            return False, f"HTTP {r.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "连接失败，服务未启动"
        except Exception as e:
            return False, str(e)

    def _check_openai(self):
        if not self.api_key and self.base_url == "https://api.openai.com/v1":
            return False, "未设置 OPENAI_API_KEY"
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            r = requests.get(f"{self.base_url.rstrip('/v1')}/models",
                             headers=headers, timeout=10)
            if r.status_code == 200:
                count = len(r.json().get("data", []))
                return True, f"在线 | 共 {count} 个模型"
            elif r.status_code == 401:
                return False, "API Key 无效"
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)

    def _check_anthropic(self):
        if not self.api_key:
            return False, "未设置 ANTHROPIC_API_KEY"
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={"model": self.model, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                timeout=10,
            )
            if r.status_code in (200, 400):  # 400=key有效但消息格式问题
                return True, "Key 有效"
            elif r.status_code == 401:
                return False, "API Key 无效"
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)

    # -------------------- 文本生成 --------------------

    def generate(self, prompt, system=None, model_override=None, **kwargs):
        """
        统一的 generate 接口
        """
        ptype = self.ptype
        target_model = model_override or self.model

        if ptype == "ollama":
            return self._generate_ollama(prompt, system, target_model, **kwargs)
        elif ptype == "anthropic":
            return self._generate_anthropic(prompt, system, target_model, **kwargs)
        else:
            return self._generate_openai(prompt, system, target_model, **kwargs)

    def _generate_ollama(self, prompt, system, model, stream=False, **kwargs):
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.3),
                "num_predict": kwargs.get("max_tokens", 2048),
            },
        }
        if system:
            payload["system"] = system

        try:
            r = requests.post(
                f"{self.base_url}/api/generate",
                json=payload, timeout=120
            )
            if r.status_code == 200:
                return r.json().get("response", "").strip()
            return f"[ERROR] HTTP {r.status_code}: {r.text[:200]}"
        except requests.exceptions.ConnectionError:
            return "[ERROR] 连接失败，Ollama 未启动"
        except requests.exceptions.Timeout:
            return "[ERROR] 请求超时"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _generate_openai(self, prompt, system, model, **kwargs):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }

        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers, json=payload, timeout=60
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            return f"[ERROR] HTTP {r.status_code}: {r.text[:300]}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _generate_anthropic(self, prompt, system, model, **kwargs):
        messages = [{"role": "user", "content": prompt}]
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.3),
        }
        if system:
            payload["system"] = system

        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers, json=payload, timeout=60
            )
            if r.status_code == 200:
                return r.json()["content"][0]["text"].strip()
            return f"[ERROR] HTTP {r.status_code}: {r.text[:300]}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    # -------------------- 多轮对话 --------------------

    def chat(self, messages, system=None, model_override=None, **kwargs):
        """
        多轮对话
        messages: [{"role": "user"/"assistant", "content": "..."}]
        """
        ptype = self.ptype
        target_model = model_override or self.model

        if ptype == "anthropic":
            return self._chat_anthropic(messages, system, target_model, **kwargs)
        elif ptype == "ollama":
            return self._chat_ollama(messages, system, target_model, **kwargs)
        else:
            return self._chat_openai(messages, system, target_model, **kwargs)

    def _chat_openai(self, messages, system, model, **kwargs):
        all_msgs = []
        if system:
            all_msgs.append({"role": "system", "content": system})
        all_msgs.extend(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": all_msgs,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers, json=payload, timeout=60
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            return f"[ERROR] {r.status_code}: {r.text[:200]}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _chat_anthropic(self, messages, system, model, **kwargs):
        # Anthropic 角色是 human/assistant
        anthropic_msgs = []
        for m in messages:
            role = "user" if m["role"] == "user" else "assistant"
            anthropic_msgs.append({"role": role, "content": m["content"]})

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "messages": anthropic_msgs,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.3),
        }
        if system:
            payload["system"] = system

        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers, json=payload, timeout=60
            )
            if r.status_code == 200:
                return r.json()["content"][0]["text"].strip()
            return f"[ERROR] {r.status_code}: {r.text[:200]}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _chat_ollama(self, messages, system, model, **kwargs):
        all_msgs = []
        if system:
            all_msgs.append({"role": "system", "content": system})
        all_msgs.extend(messages)

        payload = {
            "model": model,
            "messages": all_msgs,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.3),
                "num_predict": kwargs.get("max_tokens", 2048),
            },
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload, timeout=120
            )
            if r.status_code == 200:
                return r.json()["message"]["content"].strip()
            return f"[ERROR] {r.status_code}: {r.text[:200]}"
        except Exception as e:
            return f"[ERROR] {str(e)}"


# -------------------- 兼容性别名 --------------------
OllamaClient = ModelClient
UnifiedClient = ModelClient
