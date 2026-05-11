"""
隐写分析模块
支持: 图片隐写检测、文件附加数据、Hex分析、字符串提取
集成 Ollama 大模型做智能分析
"""

import subprocess
import re
import os
import hashlib
import requests
from modules.ollama_client import ModelClient as OllamaClient


class StegoAnalyzer:
    """隐写分析器"""

    def __init__(self, ollama_client=None):
        self.ollama = ollama_client or OllamaClient()
        self.download_dir = os.path.join(os.path.dirname(__file__), "..", "tmp")
        os.makedirs(self.download_dir, exist_ok=True)

    def analyze(self, target):
        """
        主分析入口
        :param target: URL、本地路径、或Hex字符串
        """
        # 判断输入类型
        if target.startswith("http://") or target.startswith("https://"):
            return self._analyze_url(target)
        elif os.path.exists(target):
            return self._analyze_file(target)
        elif self._looks_like_hex(target):
            return self._analyze_hex(target)
        else:
            return self._analyze_text(target)

    def _analyze_url(self, url):
        """分析远程文件"""
        # 下载文件
        local_path = self._download_file(url)
        if not local_path:
            return "[ERROR] 文件下载失败"
        result = self._analyze_file(local_path)
        # 清理
        try:
            os.remove(local_path)
        except Exception:
            pass
        return result

    def _analyze_file(self, filepath):
        """分析本地文件"""
        results = []

        # 1. 基本信息
        info = self._get_file_info(filepath)
        results.append(f"[文件信息]\n{info}\n")

        # 2. 文件类型
        file_type = self._detect_file_type(filepath)
        results.append(f"[文件类型]\n{file_type}\n")

        # 3. 字符串提取
        strings_out = self._extract_strings(filepath)
        if strings_out:
            results.append(f"[字符串提取]\n{strings_out}\n")

        # 4. Binwalk分析
        binwalk_out = self._binwalk(filepath)
        if binwalk_out:
            results.append(f"[Binwalk分析]\n{binwalk_out}\n")

        # 5. Exif元数据(图片)
        if self._is_image(filepath):
            exif_out = self._get_exif(filepath)
            if exif_out:
                results.append(f"[Exif元数据]\n{exif_out}\n")

        # 6. 调用AI深度分析
        ai_result = self._ai_analyze(filepath, results)
        if ai_result:
            results.append(f"[AI深度分析]\n{ai_result}\n")

        return "\n".join(results)

    def _analyze_hex(self, hex_data):
        """分析十六进制字符串"""
        # 清理hex数据
        hex_clean = re.sub(r"[^a-fA-F0-9]", "", hex_data)
        if len(hex_clean) % 2 != 0:
            hex_clean = hex_clean[:-1]

        try:
            # 转换为字节
            byte_data = bytes.fromhex(hex_clean)

            results = []
            results.append(f"[Hex数据长度] {len(byte_data)} 字节\n")

            # 尝试解析为字符串
            ascii_text = self._extract_ascii_from_bytes(byte_data)
            if ascii_text:
                results.append(f"[ASCII文本]\n{ascii_text}\n")

            # 尝试检测文件头
            magic = self._detect_magic(byte_data[:32])
            results.append(f"[检测文件头] {magic}\n")

            # 查找flag
            flags = re.findall(r"flag\{[^}]+\}", ascii_text, re.IGNORECASE)
            if flags:
                results.append(f"[!] 发现flag: {flags}\n")

            # 尝试解码
            decoded = self._try_decode(byte_data)
            if decoded:
                results.append(f"[解码结果]\n{decoded}\n")

            # AI分析
            ai_result = self._ai_analyze_hex(hex_clean)
            if ai_result:
                results.append(f"[AI分析]\n{ai_result}\n")

            return "\n".join(results)

        except Exception as e:
            return f"[ERROR] Hex解析失败: {str(e)}"

    def _analyze_text(self, text):
        """分析文本内容（可能是题目描述）"""
        prompt = f"""你是一个隐写分析专家。分析以下文本，找出可能的隐藏信息。

分析维度:
1. 字符串中是否有Base64/URL/Hex编码
2. 是否有零宽字符隐写
3. 是否有特殊字符替换(如Obfuscated字符)
4. 是否有Unicode方向字符隐写

文本内容:
{text}
"""
        return self.ollama.generate(prompt)

    def _download_file(self, url):
        """下载文件到本地"""
        try:
            r = requests.get(url, timeout=30, stream=True)
            if r.status_code != 200:
                return None

            filename = os.path.basename(url.split("?")[0])
            if not filename or "." not in filename:
                filename = "downloaded_file"

            local_path = os.path.join(self.download_dir, filename)

            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            return local_path
        except Exception as e:
            return None

    def _get_file_info(self, filepath):
        """获取文件基本信息"""
        try:
            size = os.path.getsize(filepath)
            md5 = hashlib.md5(open(filepath, "rb").read()).hexdigest()
            sha256 = hashlib.sha256(open(filepath, "rb").read()).hexdigest()
            return f"  路径: {filepath}\n  大小: {size} bytes ({size/1024:.1f} KB)\n  MD5: {md5}\n  SHA256: {sha256[:32]}..."
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _detect_file_type(self, filepath):
        """检测文件类型(用file命令)"""
        try:
            r = subprocess.run(["file", filepath], capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
        except Exception:
            # 手动检测文件头
            with open(filepath, "rb") as f:
                header = f.read(32)
            return f"文件头(HEX): {header.hex()}"

    def _is_image(self, filepath):
        """判断是否为图片"""
        img_exts = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        return any(filepath.lower().endswith(ext) for ext in img_exts)

    def _extract_strings(self, filepath, min_len=4):
        """提取可打印字符串"""
        try:
            r = subprocess.run(
                ["strings", "-n", str(min_len), filepath],
                capture_output=True, text=True, timeout=10
            )
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]

            # 过滤噪音
            interesting = []
            for line in lines:
                if any(kw in line.lower() for kw in ["flag", "ctf", "password", "secret", "key", "token"]):
                    interesting.append(line)

            if interesting:
                return "\n".join(interesting[:50])  # 限制输出
            return "\n".join(lines[:30])
        except Exception:
            return "[strings命令不可用]"

    def _binwalk(self, filepath):
        """Binwalk分析"""
        try:
            r = subprocess.run(
                ["binwalk", filepath],
                capture_output=True, text=True, timeout=30
            )
            return r.stdout.strip()[:1000]
        except Exception:
            return None

    def _get_exif(self, filepath):
        """获取图片EXIF"""
        try:
            r = subprocess.run(
                ["exiftool", filepath],
                capture_output=True, text=True, timeout=10
            )
            return r.stdout.strip()[:800]
        except Exception:
            return None

    def _looks_like_hex(self, text):
        """判断是否像Hex数据"""
        cleaned = re.sub(r"[^a-fA-F0-9\s]", "", text)
        return len(cleaned) >= 16 and sum(c in "0123456789abcdefABCDEF" for c in cleaned) / len(cleaned) > 0.8

    def _detect_magic(self, data):
        """检测文件魔数"""
        magic_map = {
            b"\x89PNG": "PNG图片",
            b"\xff\xd8\xff": "JPEG图片",
            b"GIF87a": "GIF图片",
            b"GIF89a": "GIF图片",
            b"PK\x03\x04": "ZIP/Office文档",
            b"%PDF": "PDF文档",
            b"\x7fELF": "ELF可执行文件",
            b"MZ": "Windows PE可执行文件",
            b"RIFF": "RIFF音视频(AVI/WAV)",
            b"\x1f\x8b": "Gzip压缩包",
            b"BM": "BMP图片",
            b"\x89HB": "Huffman压缩(Adobe)",
        }
        for magic, ftype in magic_map.items():
            if data.startswith(magic):
                return ftype
        return "未知格式"

    def _extract_ascii_from_bytes(self, data):
        """从字节中提取ASCII文本"""
        text = ""
        for b in data:
            if 32 <= b < 127:
                text += chr(b)
            else:
                text += "."
        # 清理多余的点
        text = re.sub(r"\.+", ".", text)
        return text[:1000]

    def _try_decode(self, data):
        """尝试多种解码"""
        results = []

        # Base64
        import base64
        try:
            decoded = base64.b64decode(data)
            if all(32 <= b < 127 or b in [10, 13] for b in decoded):
                return f"Base64解码:\n{decoded[:500]}"
        except Exception:
            pass

        # URL decode
        from urllib.parse import unquote
        try:
            decoded = unquote(data.decode("utf-8", errors="ignore"))
            if len(decoded) > len(data) * 0.8:
                return f"URL解码:\n{decoded[:500]}"
        except Exception:
            pass

        return None

    def _ai_analyze(self, filepath, manual_results):
        """调用AI分析文件"""
        try:
            prompt = f"""你是隐写分析专家。以下是对一个文件的初步分析结果，请做进一步深度分析:

{chr(10).join(manual_results[:3])}

可能的隐写技术包括:
- LSB隐写(最低有效位)
- 文件附加(ZIP末尾追加数据)
- Exif隐藏
- Steghide/DCT域隐写
- 字符串/注释隐藏

请给出:
1. 你检测到的最可能的隐写方式
2. 提取隐藏数据的具体方法
3. 如果发现了flag，直接给出
"""
            return self.ollama.generate(prompt)
        except Exception:
            return None

    def _ai_analyze_hex(self, hex_data):
        """调用AI分析Hex"""
        try:
            prompt = f"""分析以下十六进制数据，找出隐藏信息:

前100字节(HEX): {hex_data[:200]}

请分析:
1. 文件类型/格式
2. 是否有编码内容(ASCII/UTF等)
3. 是否有隐藏数据
4. 最终答案(flag等)
"""
            return self.ollama.generate(prompt)
        except Exception:
            return None


if __name__ == "__main__":
    a = StegoAnalyzer()
    print(a._looks_like_hex("89504e470d0a1a0a0000000d49484452"))
