"""
CTF解题框架
根据题目类型自动调用对应策略，集成Ollama大模型分析
"""

import re
import os
import subprocess
from modules.ollama_client import ModelClient as OllamaClient


# CTF提示词模板
CTF_PROMPT_TEMPLATES = {
    "web": """你是一个专业的CTF Web安全选手。
擅长: SQL注入、XSS、SSRF、文件上传、命令注入、反序列化、变量覆盖、认证绕过等。
解题原则:
1. 先分析题目，判断漏洞类型
2. 先试最简单payload: ' or '1'='1, " or "1"="1, admin'--
3. 确认注入点后再深入
4. 复杂技术留给简单方法搞不定时再用

请分析以下Web题目，给出解题步骤和最终flag。""",

    "reverse": """你是一个专业的CTF Reverse选手。
擅长: 反编译(IDA/Ghidra)、静态分析、动态调试、代码混淆、ELF/PE分析。
解题原则:
1. 先用file/nm/objdump/readelf分析文件结构
2. 找到main函数入口
3. 分析伪代码逻辑
4. 必要时用gdb/strace辅助调试

请分析以下Reverse题目，给出解题步骤和最终flag。""",

    "crypto": """你是一个专业的CTF Crypto选手。
擅长: AES/RSA/DSA加密解密、编码转换(URL/Hex/Base64)、哈希长度扩展攻击、Padding Oracle。
解题原则:
1. 先识别加密/编码类型
2. 分析密钥或算法弱点
3. 尝试已知明文攻击、选择密文攻击等

请分析以下Crypto题目，给出解题步骤和最终flag。""",

    "pwn": """你是一个专业的CTF Pwn选手。
擅长: 栈溢出、堆溢出、格式化字符串、ROP链构造、libc泄漏。
解题原则:
1. 先分析二进制保护(NX/PIE/RELRO/Canary)
2. 找到溢出点
3. 计算偏移量
4. 构造ROP链或shellcode

请分析以下Pwn题目，给出解题步骤和最终flag。""",

    "misc": """你是一个专业的CTF Misc选手。
擅长: 流量分析(pcap)、隐写(zsteg/strings)、编码转换、图片元数据、内存镜像。
解题原则:
1. 先识别文件类型
2. 提取可疑字符串和十六进制数据
3. 用binwalk/strings/stegsolve进一步分析
4. 注意文件附加数据和伪加密

请分析以下Misc题目，给出解题步骤和最终flag。""",

    "forensics": """你是一个专业的CTF取证选手。
擅长: 文件恢复、内存取证、磁盘镜像分析、日志分析、流量重组。
解题原则:
1. 确定取证类型(内存/磁盘/网络)
2. 用对应工具提取关键数据
3. 时间线重建
4. 寻找隐藏数据或恶意代码痕迹

请分析以下Forensics题目，给出解题步骤和最终flag。""",
}


class CTFSolver:
    """CTF题目求解器"""

    def __init__(self, ollama_client=None):
        self.ollama = ollama_client or OllamaClient()

    def detect_type(self, content):
        """自动检测CTF题型"""
        content_lower = content.lower()

        # 关键词匹配
        if any(k in content_lower for k in ["注入", "sql", "xss", "ssrf", "上传", "rce", "webshell", "web", "login", "admin"]):
            return "web"
        if any(k in content_lower for k in ["反编译", "逆向", "reverse", "elf", "pe", "ida", "main", "汇编", "binary"]):
            return "reverse"
        if any(k in content_lower for k in ["加密", "crypto", "rsa", "aes", "cipher", "encode", "解码"]):
            return "crypto"
        if any(k in content_lower for k in ["pwn", "溢出", "栈", "heap", "buffer", "rop", "shellcode", "ret2"]):
            return "pwn"
        if any(k in content_lower for k in ["隐写", "misc", "流量", "pcap", "strings", "zsteg", "图片", "流量分析"]):
            return "misc"
        if any(k in content_lower for k in ["取证", "forensics", "内存", "disk", "img", "镜像", "日志"]):
            return "forensics"

        # 尝试从题目描述中提取类型
        type_patterns = [
            (r"WEB", "web"),
            (r"REVERSE|逆向", "reverse"),
            (r"CRYPTO|密码", "crypto"),
            (r"PWN|漏洞", "pwn"),
            (r"MISC|杂项", "misc"),
            (r"FORENSICS|取证", "forensics"),
        ]
        for pattern, ptype in type_patterns:
            if re.search(pattern, content):
                return ptype

        return "misc"  # 默认杂项

    def solve(self, task_content, task_type=None, flag_format=None):
        """
        解题主入口
        :param task_content: 题目描述
        :param task_type: 手动指定题型
        :param flag_format: flag格式提示
        """
        # 自动检测题型
        if not task_type:
            task_type = self.detect_type(task_content)

        template = CTF_PROMPT_TEMPLATES.get(task_type, CTF_PROMPT_TEMPLATES["misc"])

        # 拼接完整提示词
        full_prompt = f"{template}\n\n## 题目\n{task_content}\n\n"
        if flag_format:
            full_prompt += f"## Flag格式\n{flag_format}\n\n"
        full_prompt += "请给出完整解题过程和flag。"

        # 调用Ollama
        result = self.ollama.generate(full_prompt)

        # 提取flag
        flag = self.extract_flag(result)

        return result

    def extract_flag(self, text):
        """从结果中提取flag"""
        patterns = [
            r"flag\{[^}]+\}",
            r"FLAG\{[^}]+\}",
            r"ctf\{[^}]+\}",
            r"CTF\{[^}]+\}",
            r"flag\{[a-zA-Z0-9_]+}",
            r"\[FLAG\]\s*([a-zA-Z0-9_\{\}]+)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(0)
        return None

    def batch_solve(self, tasks):
        """批量解题"""
        results = []
        for task in tasks:
            task_type = task.get("type")
            content = task.get("content")
            result = self.solve(content, task_type)
            results.append({"task": content[:50], "result": result})
        return results


if __name__ == "__main__":
    # 简单测试
    solver = CTFSolver()
    print(solver.detect_type("SQL注入题目，flag格式flag{xxx}"))
    print(solver.detect_type("这是一个PWN题目，栈溢出"))
