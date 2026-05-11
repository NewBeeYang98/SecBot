"""
SecBot 网络环境检测
自动识别当前网络环境: 互联网 / 内网半隔离 / 完全隔离
"""

import socket
import requests
import urllib.request
import urllib.error
import time


class NetworkDetector:
    """
    检测当前网络环境
    Internet: 可访问互联网
    Intranet: 纯内网，无法访问互联网
    """

    # 检测互联网的地址
    CHECK_HOSTS = [
        ("https://www.baidu.com", 5),
        ("https://www.google.com", 5),
        ("https://114.114.114.114", 3),  # 腾讯DNS
    ]

    # 内网IP段
    PRIVATE_RANGES = [
        ("10.0.0.0", "10.255.255.255"),
        ("172.16.0.0", "172.31.255.255"),
        ("192.168.0.0", "192.168.255.255"),
        ("127.0.0.0", "127.255.255.255"),
    ]

    def __init__(self):
        self._env = None
        self._local_ip = None
        self._gateway = None

    def detect(self) -> str:
        """
        返回: "internet" / "intranet" / "isolated"
        """
        if self._env:
            return self._env

        # 尝试访问互联网
        if self._check_internet():
            self._env = "internet"
        elif self._check_local_network():
            self._env = "intranet"
        else:
            self._env = "isolated"

        return self._env

    def _check_internet(self) -> bool:
        """检测能否访问互联网"""
        for url, timeout in self.CHECK_HOSTS:
            try:
                if url.startswith("https://"):
                    r = requests.get(url, timeout=timeout, allow_redirects=True)
                    if r.status_code < 500:
                        return True
            except Exception:
                try:
                    # 备用: 直接socket连接
                    host = url.replace("https://", "").split("/")[0]
                    sock = socket.socket()
                    sock.settimeout(timeout)
                    sock.connect((host, 443))
                    sock.close()
                    return True
                except Exception:
                    pass
        return False

    def _check_local_network(self) -> bool:
        """检测是否有内网"""
        return self.get_local_ip() is not None

    def get_local_ip(self) -> str:
        """获取本机IP"""
        if self._local_ip:
            return self._local_ip

        # 方法1: 连接外网socket（不发送数据）
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            # 连DNS（不发数据）
            sock.connect(("8.8.8.8", 53))
            self._local_ip = sock.getsockname()[0]
            sock.close()
            return self._local_ip
        except Exception:
            pass

        # 方法2: 读本机路由信息
        try:
            import subprocess
            # Linux
            result = subprocess.run(
                ["ip", "route", "get", "1.1.1.1"],
                capture_output=True, text=True, timeout=3
            )
            for line in result.stdout.splitlines():
                if "src" in line:
                    parts = line.split()
                    if "src" in parts:
                        idx = parts.index("src")
                        if idx + 1 < len(parts):
                            self._local_ip = parts[idx + 1]
                            return self._local_ip
        except Exception:
            pass

        # 方法3: 读/proc
        try:
            with open("/proc/net/route") as f:
                for line in f.readlines()[1:]:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        iface = parts[0]
                        dest = parts[1]
                        if dest == "00000000":  # 默认路由
                            # 读网卡IP
                            with open(f"/proc/net/route") as _f:
                                pass
                            break
        except Exception:
            pass

        return None

    def get_gateway(self) -> str:
        """获取网关IP"""
        if self._gateway:
            return self._gateway

        try:
            import subprocess
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=3
            )
            for line in result.stdout.splitlines():
                parts = line.split()
                if parts and parts[0] == "default":
                    # default via 192.168.1.1 dev eth0
                    if "via" in parts:
                        idx = parts.index("via")
                        self._gateway = parts[idx + 1]
                        return self._gateway
        except Exception:
            pass

        return None

    def get_netmask(self) -> str:
        """根据本机IP推断网段"""
        local = self.get_local_ip()
        if not local:
            return "unknown"

        first = int(local.split(".")[0])
        if first == 10:
            return "10.0.0.0/8"
        elif first == 172:
            return "172.16.0.0/12"
        elif first == 192:
            return "192.168.0.0/16"
        else:
            return f"{local}/24"

    def is_private_ip(self, ip: str) -> bool:
        """判断是否私网IP"""
        try:
            parts = list(map(int, ip.split(".")))
            if len(parts) != 4:
                return False
            p = parts[0] << 24 | parts[1] << 16 | parts[2] << 8 | parts[3]

            for start, end in [
                (0x0A000000, 0x0AFFFFFF),
                (0xAC100000, 0xAC1FFFFF),
                (0xC0A80000, 0xC0A8FFFF),
                (0x7F000000, 0x7FFFFFFF),
            ]:
                if start <= p <= end:
                    return True
            return False
        except Exception:
            return False

    def get_local_subnet(self) -> str:
        """推断本机所在网段"""
        local = self.get_local_ip()
        if not local:
            return "unknown"

        parts = list(map(int, local.split(".")))
        first = parts[0]

        if first == 10:
            return "10.0.0.0/8"
        elif first == 172:
            return "172.16.0.0/12"
        elif first == 192:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        else:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

    def summary(self) -> dict:
        """返回完整网络信息"""
        env = self.detect()
        return {
            "environment": env,
            "local_ip": self.get_local_ip(),
            "gateway": self.get_gateway(),
            "subnet": self.get_local_subnet(),
            "can_access_internet": env == "internet",
            "description": {
                "internet": "可访问互联网（正常模式）",
                "intranet": "纯内网，无法访问互联网（隔离模式）",
                "isolated": "完全隔离，网络不可用",
            }.get(env, "未知"),
        }

    def __repr__(self):
        s = self.summary()
        return (f"NetworkDetector(env={s['environment']}, "
                f"ip={s['local_ip']}, gateway={s['gateway']})")
