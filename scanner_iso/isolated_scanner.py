#!/usr/bin/env python3
"""
SecBot 隔离扫描仪 - 零依赖内网扫描器
可在完全断网的内网机器上运行（纯Python标准库）
用于 U盘模式: 内网扫描 → 导出JSON → 拿到互联网机器分析

使用方法:
  python isolated_scanner.py 192.168.1.0/24
  python isolated_scanner.py --target 192.168.1.1 --port 80,443,3306
  python isolated_scanner.py --full        # 全扫描（慢）
  python isolated_scanner.py --export      # 从之前的结果导出
"""

import socket
import struct
import json
import os
import sys
import datetime
import random
import argparse
import subprocess
import re
import hashlib
import urllib.parse


# ==================== 纯标准库扫描器 ====================

class SimpleScanner:
    """
    纯Python实现的内网扫描器
    不依赖nmap，零外部依赖
    支持: TCP端口扫描、banner获取、HTTP探测
    """

    # 常用端口
    COMMON_PORTS = [
        21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
        993, 995, 1723, 3306, 3389, 5900, 8080, 8443, 8888, 9000, 9200,
    ]

    # 全端口段(快速扫)
    FULL_PORTS = list(range(1, 1001)) + [1433, 1521, 1723, 3306, 3389,
                                           5432, 5900, 6379, 8080, 8443, 9200, 27017]

    def __init__(self, timeout=2, max_workers=100):
        self.timeout = timeout
        self.max_workers = max_workers
        self._lock = None  # 无线程锁，简化
        self.results = []

    def parse_target(self, target):
        """解析目标: IP / CIDR / URL"""
        if "/" in target:
            return self._cidr_to_ips(target)
        elif target.startswith("http"):
            return [target]
        else:
            return [target]

    def _cidr_to_ips(self, cidr):
        """CIDR转IP列表"""
        try:
            parts = cidr.split("/")
            ip_str = parts[0]
            prefix = int(parts[1]) if len(parts) > 1 else 32

            # 转32位整数
            ip_int = self._ip_to_int(ip_str)
            mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
            network = ip_int & mask
            broadcast = network | (~mask & 0xFFFFFFFF)

            ips = []
            # 限制扫描范围
            count = min(broadcast - network - 1, 254)
            start = network + 1

            for i in range(count):
                ips.append(self._int_to_ip(start + i))
            return ips
        except Exception as e:
            return [cidr]  # fallback

    def _ip_to_int(self, ip):
        parts = list(map(int, ip.split(".")))
        return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]

    def _int_to_ip(self, n):
        return f"{(n >> 24) & 0xFF}.{(n >> 16) & 0xFF}.{(n >> 8) & 0xFF}.{n & 0xFF}"

    def tcp_connect_scan(self, host, port, timeout=None):
        """TCP连接扫描（同步，跨平台）"""
        timeout = timeout or self.timeout
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def get_banner(self, host, port, timeout=None):
        """获取服务banner"""
        timeout = timeout or self.timeout
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))

            # HTTP端口发HTTP请求
            if port in (80, 8080, 8443, 443, 8888, 9090):
                sock.sendall(b"HEAD / HTTP/1.0\r\nHost: %s\r\n\r\n" % host.encode())

            # 读响应
            sock.settimeout(2)
            data = sock.recv(512)
            sock.close()
            return data.decode("utf-8", errors="ignore").strip()[:200]
        except Exception:
            return ""

    def detect_service(self, port):
        """根据端口猜服务"""
        services = {
            21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
            53: "dns", 80: "http", 110: "pop3", 111: "rpcbind",
            135: "msrpc", 139: "netbios", 143: "imap",
            443: "https", 445: "smb", 993: "imaps", 995: "pop3s",
            1433: "mssql", 1521: "oracle", 1723: "pptp",
            3306: "mysql", 3389: "rdp", 5432: "postgresql",
            5900: "vnc", 6379: "redis", 8080: "http-proxy",
            8443: "https-alt", 8888: "http-alt", 9000: "cslistener",
            9200: "elasticsearch", 27017: "mongodb",
        }
        return services.get(port, "unknown")

    def scan_host(self, host, ports=None, get_banner_flag=True):
        """扫描单个主机"""
        if ports is None:
            ports = self.COMMON_PORTS

        host_result = {
            "ip": host,
            "hostname": self._resolve_hostname(host),
            "ports": [],
            "os_hint": "",
            "scan_time": datetime.datetime.now().isoformat(),
        }

        for port in ports:
            if self.tcp_connect_scan(host, port):
                port_info = {
                    "port": port,
                    "state": "open",
                    "service": self.detect_service(port),
                    "banner": "",
                }
                if get_banner_flag:
                    banner = self.get_banner(host, port)
                    if banner:
                        port_info["banner"] = banner[:200]

                host_result["ports"].append(port_info)

        return host_result

    def _resolve_hostname(self, ip):
        """反向解析主机名"""
        try:
            name = socket.gethostbyaddr(ip)
            return name[0]
        except Exception:
            return ""

    def scan(self, target, ports=None, full_scan=False):
        """
        主扫描入口
        :param target: IP / CIDR / URL
        :param ports: 端口列表
        :param full_scan: 全端口扫描
        """
        if full_scan:
            ports = self.FULL_PORTS
        elif ports:
            ports = list(map(int, ports.split(",")))
        else:
            ports = self.COMMON_PORTS

        targets = self.parse_target(target)
        results = {
            "target": target,
            "scan_started": datetime.datetime.now().isoformat(),
            "hosts": [],
            "summary": {"total": len(targets), "alive": 0, "open_ports": 0},
        }

        for ip in targets:
            print(f"[*] 扫描 {ip} ...", end="\r")
            host_result = self.scan_host(ip, ports)

            if host_result["ports"]:
                results["hosts"].append(host_result)
                results["summary"]["alive"] += 1
                results["summary"]["open_ports"] += len(host_result["ports"])
                print(f"[+] {ip}: {len(host_result['ports'])} 个开放端口")
            else:
                print(f"    {ip}: 无开放端口")

        results["scan_finished"] = datetime.datetime.now().isoformat()
        return results


# ==================== 主机发现（ARP ping）====================

class HostDiscovery:
    """内网主机发现，不依赖nmap"""

    @staticmethod
    def ping sweep(hosts, timeout=1):
        """Ping发现（发送ICMP+TCP）"""
        alive = []
        scanner = SimpleScanner(timeout=timeout)

        for ip in hosts:
            try:
                # TCP ping (port 80/443)
                if scanner.tcp_connect_scan(ip, 80, timeout=timeout):
                    alive.append({"ip": ip, "method": "tcp80"})
                    continue
                if scanner.tcp_connect_scan(ip, 445, timeout=timeout):
                    alive.append({"ip": ip, "method": "tcp445"})
                    continue

                # 尝试ICMP (需要root)
                try:
                    proc = subprocess.run(
                        ["ping", "-c", "1", "-W", str(timeout), ip],
                        capture_output=True, timeout=timeout + 1
                    )
                    if proc.returncode == 0:
                        alive.append({"ip": ip, "method": "icmp"})
                except Exception:
                    pass

            except Exception:
                pass

        return alive

    @staticmethod
    def get_local_network():
        """获取本机所在网段"""
        try:
            # 读 /proc 或调用ipconfig
            proc = subprocess.run(["ip", "route", "show"], capture_output=True, text=True)
            for line in proc.stdout.splitlines():
                if "src" in line:
                    parts = line.split()
                    idx = parts.index("src") if "src" in parts else -1
                    if idx > 0:
                        return parts[idx - 1] if idx > 0 else None

            # Windows
            proc = subprocess.run(["ipconfig"], capture_output=True, text=True)
            for line in proc.stdout.splitlines():
                if "IPv4" in line or "地址" in line:
                    m = re.search(r"\d+\.\d+\.\d+\.\d+", line)
                    if m:
                        return m.group(0)
        except Exception:
            pass
        return None


# ==================== 渗透信息收集 ====================

class ReconCollector:
    """
    信息收集模块 - 纯标准库
    不依赖外部工具，收集目标的所有公开信息
    """

    def __init__(self):
        self.findings = []

    def collect(self, target):
        """收集目标信息"""
        results = {
            "target": target,
            "collected_at": datetime.datetime.now().isoformat(),
            "dns": {},
            "whois": {},
            "http": {},
            "fingerprints": [],
        }

        # DNS解析
        results["dns"] = self._dns_lookup(target)

        # HTTP探测（如果是URL）
        if target.startswith("http"):
            results["http"] = self._http_probe(target)

        # 端口指纹
        if self._is_ip(target):
            results["fingerprints"] = self._fingerprint(target)

        self.findings.append(results)
        return results

    def _is_ip(self, target):
        return bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target))

    def _dns_lookup(self, target):
        """DNS相关查询"""
        results = {}
        try:
            results["hostname"] = socket.getfqdn(target)
        except Exception:
            pass
        try:
            results["all_ips"] = list(set(
                info[4][0] for info in socket.getaddrinfo(target, None)
            ))
        except Exception:
            pass
        return results

    def _http_probe(self, url):
        """HTTP探测"""
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.netloc.split(":")[0]
            port = parsed.port or (443 if parsed.scheme == "https" else 80)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))

            req = f"GET {parsed.path or '/'} HTTP/1.0\r\nHost: {host}\r\n\r\n"
            sock.sendall(req.encode())
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if len(data) > 8192:
                    break
            sock.close()

            text = data.decode("utf-8", errors="ignore")
            headers = text.split("\r\n\r\n")[0][:1000]

            return {
                "status_line": headers.split("\r\n")[0][:100] if headers else "",
                "server": self._extract_header(headers, "Server"),
                "powered_by": self._extract_header(headers, "X-Powered-By"),
                "title": self._extract_title(text),
                "headers_raw": headers,
            }
        except Exception as e:
            return {"error": str(e)}

    def _extract_header(self, headers_text, header_name):
        for line in headers_text.split("\r\n"):
            if line.lower().startswith(header_name.lower() + ":"):
                return line.split(":", 1)[1].strip()
        return ""

    def _extract_title(self, html_text):
        m = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def _fingerprint(self, ip):
        """简单指纹识别"""
        scanner = SimpleScanner(timeout=2)
        fps = []

        # 检测SMB (445)
        if scanner.tcp_connect_scan(ip, 445):
            fps.append({"port": 445, "service": "smb", "os_hint": "Windows"})

        # 检测SSH版本
        banner = scanner.get_banner(ip, 22)
        if "OpenSSH" in banner:
            fps.append({"port": 22, "service": "ssh", "version": banner[:100]})
        elif "ssh" in banner.lower():
            fps.append({"port": 22, "service": "ssh", "version": banner[:100]})

        # 检测HTTP标题
        banner = scanner.get_banner(ip, 80)
        if banner:
            fps.append({"port": 80, "service": "http", "response": banner[:200]})

        return fps


# ==================== 隔离扫描仪主程序 ====================

class IsolatedScanner:
    """
    隔离扫描仪主类
    生成: scan_result.json（包含所有发现，供AI分析）
    """

    def __init__(self):
        self.scanner = SimpleScanner()
        self.recon = ReconCollector()
        self.results = {}

    def run(self, target, full_scan=False, ports=None, collect_recon=True):
        """执行完整扫描"""
        print(f"[*] 开始扫描目标: {target}")
        print(f"[*] 模式: {'全扫描' if full_scan else '快速扫描'}")
        print("-" * 50)

        self.results = {
            "tool": "SecBot-Isolated-Scanner",
            "version": "1.0",
            "target": target,
            "scan_started": datetime.datetime.now().isoformat(),
        }

        # 1. 主机发现
        print("\n[*] 阶段1: 主机发现...")
        targets = self.scanner.parse_target(target)
        print(f"[*] 待扫描: {len(targets)} 个目标")

        # 2. 端口扫描
        print("\n[*] 阶段2: 端口扫描...")
        scan_result = self.scanner.scan(target, ports=ports, full_scan=full_scan)
        self.results["scan"] = scan_result

        # 3. 信息收集
        if collect_recon:
            print("\n[*] 阶段3: 信息收集...")
            for host_data in scan_result.get("hosts", []):
                ip = host_data["ip"]
                print(f"    收集 {ip} ...")
                recon = self.recon.collect(ip)
                host_data["recon"] = recon

        self.results["scan_finished"] = datetime.datetime.now().isoformat()

        # 4. 生成概览
        self.results["overview"] = self._generate_overview(scan_result)

        return self.results

    def _generate_overview(self, scan_result):
        """生成扫描概览"""
        overview = {
            "total_hosts": scan_result["summary"]["alive"],
            "total_open_ports": scan_result["summary"]["open_ports"],
            "interesting_finds": [],
            "high_value_targets": [],
        }

        for host in scan_result.get("hosts", []):
            ip = host["ip"]
            open_ports = [p["port"] for p in host["ports"]]

            # 高价值目标标记
            hv_ports = {80, 443, 8080, 8443, 3306, 1433, 3389, 22, 21}
            if any(p in hv_ports for p in open_ports):
                overview["high_value_targets"].append({
                    "ip": ip,
                    "ports": open_ports,
                    "hostname": host.get("hostname", ""),
                })

            # 有趣发现
            for p in host["ports"]:
                if p["port"] in (21, 23, 445, 1433, 3306, 3389, 5900):
                    overview["interesting_finds"].append({
                        "ip": ip,
                        "port": p["port"],
                        "service": p["service"],
                        "banner": p.get("banner", "")[:100],
                    })

        return overview

    def export(self, filepath=None):
        """导出扫描结果"""
        if not filepath:
            safe_target = re.sub(r"[^\d\.\/]", "_", self.results.get("target", "scan"))
            filepath = f"scan_result_{safe_target}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n[+] 结果已保存: {filepath}")
        return filepath

    def export_tasks(self, output_path=None):
        """
        导出为SecBot任务队列格式
        直接导入SecBot Core进行分析
        """
        tasks = []

        # 为每个发现的服务生成扫描任务
        for host in self.results.get("scan", {}).get("hosts", []):
            ip = host["ip"]
            for port_info in host["ports"]:
                port = port_info["port"]
                service = port_info["service"]

                # 根据服务类型生成对应任务
                if service == "http" or port in (80, 8080, 8443):
                    tasks.append({
                        "type": "scan",
                        "description": f"Web服务扫描: {ip}:{port}",
                        "command": f"curl -s -I http://{ip}:{port}/",
                        "target": f"http://{ip}:{port}",
                        "tags": ["web", "http"],
                    })
                elif service in ("mysql", "mssql", "postgresql", "mongodb"):
                    tasks.append({
                        "type": "exploit",
                        "description": f"数据库服务: {ip}:{port} ({service})",
                        "command": f"echo '需要凭据'",
                        "target": f"{ip}:{port}",
                        "tags": ["database", service],
                    })
                elif service in ("smb",):
                    tasks.append({
                        "type": "exploit",
                        "description": f"SMB服务: {ip}:{port}",
                        "command": f"enum4linux {ip}",
                        "target": ip,
                        "tags": ["smb", "enum"],
                    })
                elif service in ("ssh",):
                    tasks.append({
                        "type": "scan",
                        "description": f"SSH服务: {ip}:{port}",
                        "command": f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {ip}",
                        "target": f"{ip}:{port}",
                        "tags": ["ssh"],
                    })

        output_path = output_path or "scan_tasks.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "exported_at": datetime.datetime.now().isoformat(),
                "from_scan": self.results.get("target"),
                "tasks": tasks,
            }, f, ensure_ascii=False, indent=2)

        print(f"[+] 任务已导出: {output_path}")
        return output_path


# ==================== 主入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="SecBot 隔离扫描仪 - 零依赖内网扫描",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python isolated_scanner.py 192.168.1.0/24           # 扫描网段
  python isolated_scanner.py 192.168.1.1 --ports 80,443,3306  # 指定端口
  python isolated_scanner.py 192.168.1.0/24 --full  # 全端口扫描
  python isolated_scanner.py --import scan.json       # 从结果导入任务
        """
    )
    parser.add_argument("target", nargs="?", help="目标IP/网段/URL")
    parser.add_argument("--ports", help="指定端口，如 80,443,3306")
    parser.add_argument("--full", action="store_true", help="全端口扫描(慢)")
    parser.add_argument("--import", dest="import_file", help="导入已有扫描结果")
    parser.add_argument("--export-tasks", action="store_true", help="导出为任务队列格式")
    parser.add_argument("-o", "--output", help="输出文件路径")

    args = parser.parse_args()

    # 导入模式
    if args.import_file:
        print(f"[*] 导入文件: {args.import_file}")
        with open(args.import_file, encoding="utf-8") as f:
            data = json.load(f)
        print(f"[+] 共 {len(data.get('tasks', data.get('hosts', [])))} 条记录")
        # 导出为任务
        scanner = IsolatedScanner()
        scanner.results = data
        scanner.export_tasks(args.output or "imported_tasks.json")
        return

    if not args.target:
        parser.print_help()
        return

    scanner = IsolatedScanner()
    results = scanner.run(args.target, full_scan=args.full, ports=args.ports)

    # 导出
    output_file = scanner.export(args.output)

    if args.export_tasks:
        scanner.export_tasks()

    # 打印概览
    overview = results.get("overview", {})
    print("\n" + "=" * 50)
    print("扫描概览:")
    print(f"  存活主机: {overview.get('total_hosts', 0)}")
    print(f"  开放端口: {overview.get('total_open_ports', 0)}")
    print(f"  高价值目标: {len(overview.get('high_value_targets', []))}")
    print(f"  有趣发现: {len(overview.get('interesting_finds', []))}")
    print("=" * 50)
    print(f"\n结果文件: {output_file}")
    print("复制到互联网机器，用 SecBot Core 进行AI分析")


if __name__ == "__main__":
    main()
