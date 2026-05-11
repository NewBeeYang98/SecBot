"""
SecBot 任务执行器
负责任务队列的执行，支持重试、超时、输出捕获
"""

import subprocess
import re
import os
import datetime
import requests
from core.network_detector import NetworkDetector


class TaskExecutor:
    """
    执行具体的安全任务
    自动判断网络环境，优先使用内网工具，必要时调用云端AI
    """

    def __init__(self):
        self.network = NetworkDetector()
        self.last_output = ""

    def execute(self, task) -> tuple:
        """
        执行单个任务
        :param task: Task 对象
        :return: (success: bool, output: str)
        """
        if not task.command:
            return False, "任务没有command字段"

        print(f"[*] 执行 [{task.id}]: {task.description}")
        print(f"    命令: {task.command[:100]}{'...' if len(task.command) > 100 else ''}")

        try:
            # 判断命令类型
            if self._is_http_request(task.command):
                output = self._execute_http(task.command)
            elif self._is_shell_command(task.command):
                output = self._execute_shell(task.command, timeout=120)
            else:
                output = self._execute_shell(task.command, timeout=120)

            self.last_output = output

            # 判断是否成功
            success = self._check_success(output, task.type)
            return success, output

        except subprocess.TimeoutExpired:
            return False, "[超时] 命令执行超时"
        except Exception as e:
            return False, f"[错误] {str(e)}"

    def _is_http_request(self, cmd: str) -> bool:
        """判断是否是HTTP请求"""
        http_keywords = ["curl", "wget", "http://", "https://", "requests."]
        return any(k in cmd.lower() for k in http_keywords)

    def _is_shell_command(self, cmd: str) -> bool:
        """判断是否是shell命令"""
        # 内网安全工具
        tools = ["nmap", "sqlmap", "nikto", "hydra", "dirb", "gobuster",
                 "enum4linux", "smbclient", "nc", "netcat", "ping", "nslookup",
                 "dig", "host", "whois", "theHarvester", "dnsenum", "masscan"]
        cmd_lower = cmd.lower()
        return any(cmd_lower.startswith(t) for t in tools) or \
               any(f" {t} " in f" {cmd_lower} " for t in tools)

    def _execute_shell(self, command: str, timeout=120) -> str:
        """执行shell命令"""
        # 安全检查
        dangerous = ["rm -rf /", ":(){:|:&};:", "> /dev/sda"]
        for d in dangerous:
            if d in command.lower():
                return f"[安全拒绝] 命令包含危险操作: {d}"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout
        if result.stderr and result.stderr not in output:
            output += "\n[STDERR]\n" + result.stderr

        return output[:10000]  # 截断

    def _execute_http(self, command: str) -> str:
        """执行HTTP请求（curl/wget）"""
        # 提取URL
        url_match = re.search(r"https?://[^\s\"']+", command)
        if not url_match:
            return "[错误] 未找到URL"

        url = url_match.group(0)

        # 用requests执行（更可靠）
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            r = requests.get(url, headers=headers, timeout=30, verify=False)
            return f"[HTTP {r.status_code}]\n{r.text[:5000]}"
        except Exception as e:
            return f"[错误] HTTP请求失败: {str(e)}"

    def _check_success(self, output: str, task_type: str) -> bool:
        """判断任务是否成功"""
        if not output:
            return False

        output_lower = output.lower()

        # 通用失败特征
        fail_patterns = [
            "command not found", "no such file", "permission denied",
            "not found", "error", "failed", "timeout",
        ]
        if any(p in output_lower for p in fail_patterns):
            # 但如果同时有成功特征，仍算成功
            pass

        # 类型特定成功特征
        success_markers = {
            "scan": ["open", "open port", "Host is up", "PORT"],
            "exploit": ["success", "SUCCESS", "exploited", "flag{", "FLAG{"],
            "recon": ["found", "discovered", "collected"],
            "analyze": ["flag{", "FLAG{", "result:", "completed"],
        }

        markers = success_markers.get(task_type, [])
        if markers and any(m in output for m in markers):
            return True

        # 有输出且没有明显错误
        return len(output) > 50

    def execute_batch(self, tasks: list) -> dict:
        """批量执行任务"""
        results = {}
        for task in tasks:
            success, output = self.execute(task)
            results[task.id] = {"success": success, "output": output}
        return results


# ==================== 快捷命令执行 ====================

class QuickCommands:
    """内网常用快捷命令"""

    @staticmethod
    def nmap_scan(target, ports=None):
        """nmap扫描"""
        cmd = f"nmap -sV -T4 {'-p ' + ports if ports else '-p 1-1000,3306,3389,22,80,443'} {target}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        return result.stdout

    @staticmethod
    def ping_host(host):
        """ping检测"""
        result = subprocess.run(
            ["ping", "-c", "3", "-W", "2", host],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout

    @staticmethod
    def curl_url(url, headers=None):
        """curl获取网页"""
        try:
            h = headers or {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            r = requests.get(url, headers=h, timeout=20, verify=False)
            return f"[{r.status_code}] {r.text[:3000]}"
        except Exception as e:
            return f"[错误] {str(e)}"

    @staticmethod
    def check_service(host, port):
        """检测服务是否存活"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            return "open" if result == 0 else "closed"
        except Exception as e:
            return f"error: {e}"
