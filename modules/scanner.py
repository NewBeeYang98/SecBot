"""
内网扫描模块
集成 nmap，支持资产发现、端口扫描、服务识别
"""

import subprocess
import re
import socket
from modules.ollama_client import ModelClient as OllamaClient
from config import NMAP_SCAN_TYPE, DEFAULT_PORTS


class Scanner:
    """内网扫描器，封装nmap命令"""

    def __init__(self):
        self.ollama = OllamaClient()

    def scan(self, target, ports=None, scan_type=None):
        """
        执行扫描
        :param target: 目标网段或IP，如 192.168.1.0/24 或 192.168.1.1
        :param ports: 端口范围，如 "22,80,443" 或 "1-1000"
        :param scan_type: nmap扫描类型，如 "-sV -T4"
        """
        ports = ports or DEFAULT_PORTS
        scan_type = scan_type or NMAP_SCAN_TYPE

        # 检查nmap是否安装
        if not self._check_nmap():
            return "[ERROR] nmap 未安装，请先运行: sudo apt install nmap"

        # 验证目标格式
        if not self._validate_target(target):
            return f"[ERROR] 无效的目标: {target}"

        cmd = f"nmap {scan_type} -p {ports} {target} -oX -"
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120
            )
            output = result.stdout

            # 解析XML输出
            hosts = self._parse_nmap_xml(output)

            if not hosts:
                return f"[*] 扫描完成，未发现存活主机 (目标: {target})\n{output[:500]}"

            # 格式化输出
            return self._format_result(hosts, target)

        except subprocess.TimeoutExpired:
            return "[ERROR] 扫描超时"
        except Exception as e:
            return f"[ERROR] 扫描异常: {str(e)}"

    def quick_scan(self, target):
        """快速扫描，只检测存活主机"""
        return self.scan(target, ports="", scan_type="-sn")

    def deep_scan(self, target):
        """深度扫描，全端口+服务版本+OS识别"""
        return self.scan(target, ports="1-65535", scan_type="-sV -sC -O -T4")

    def _check_nmap(self):
        """检查nmap是否安装"""
        try:
            subprocess.run("nmap --version", shell=True, capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def _validate_target(self, target):
        """简单验证目标格式"""
        # CIDR格式
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$", target):
            return True
        # 单IP
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target):
            return True
        # 域名
        if re.match(r"^[a-zA-Z0-9\-\.]+$", target):
            return True
        return False

    def _parse_nmap_xml(self, xml_output):
        """解析nmap XML输出"""
        hosts = []

        # 提取host块
        host_blocks = re.findall(r"<host>(.*?)</host>", xml_output, re.DOTALL)
        for block in host_blocks:
            host_info = {}

            # IP
            ip = re.search(r"<address addr=\"([\d.]+)\" addrtype=\"ipv4\"/>", block)
            if not ip:
                continue
            host_info["ip"] = ip.group(1)

            # 状态
            status = re.search(r"<status state=\"(\w+)\"", block)
            host_info["status"] = status.group(1) if status else "unknown"

            # 端口
            ports = []
            port_blocks = re.findall(r"<port protocol=\"(\w+)\" portid=\"(\d+)\">(.*?)</port>", block, re.DOTALL)
            for proto, port_id, port_data in port_blocks:
                service = re.search(r"<service name=\"([^\"]+)\"", port_data)
                version = re.search(r"<service name=\"[^\"]+\" version=\"([^\"]+)\"", port_data)
                state = re.search(r"<state state=\"(\w+)\"", port_data)
                ports.append({
                    "port": port_id,
                    "protocol": proto,
                    "service": service.group(1) if service else "unknown",
                    "version": version.group(1) if version else "",
                    "state": state.group(1) if state else "unknown",
                })
            host_info["ports"] = ports

            hosts.append(host_info)

        return hosts

    def _format_result(self, hosts, target):
        """格式化扫描结果"""
        lines = [f"=" * 60]
        lines.append(f"  SecBot 扫描报告")
        lines.append(f"  目标: {target}")
        lines.append(f"  发现: {len(hosts)} 个存活主机")
        lines.append(f"=" * 60)

        for h in hosts:
            lines.append(f"\n[*] {h['ip']} ({h['status']})")
            if h.get("ports"):
                lines.append(f"    开放端口:")
                for p in h["ports"]:
                    if p["state"] == "open":
                        ver = f" ({p['version']})" if p.get("version") else ""
                        lines.append(f"      {p['port']}/{p['protocol']} {p['service']}{ver}")

        lines.append("\n" + "=" * 60)

        # 调用AI做进一步分析
        ai_analysis = self._ai_analyze(hosts)
        if ai_analysis:
            lines.append(f"\n[AI分析]\n{ai_analysis}")

        return "\n".join(lines)

    def _ai_analyze(self, hosts):
        """调用Ollama做安全分析"""
        if not hosts:
            return ""

        try:
            prompt = f"""对以下nmap扫描结果进行安全分析:

发现的存活主机和端口:
{self._format_hosts_simple(hosts)}

请指出:
1. 潜在攻击面(高危端口服务)
2. 建议优先测试的入口点
3. 进一步信息收集的建议
"""
            return self.ollama.generate(prompt)
        except Exception:
            return None

    def _format_hosts_simple(self, hosts):
        """简化格式输出主机列表"""
        lines = []
        for h in hosts:
            open_ports = [f"{p['port']}/{p['service']}" for p in h.get("ports", []) if p["state"] == "open"]
            if open_ports:
                lines.append(f"{h['ip']}: {', '.join(open_ports)}")
        return "\n".join(lines) if lines else "无"


if __name__ == "__main__":
    s = Scanner()
    print(s._validate_target("192.168.1.1"))
    print(s._validate_target("192.168.1.0/24"))
