#!/usr/bin/env python3
"""
SecBot 依赖检查器
检查 Python包 / 系统工具 / AI配置 / 网络连接
支持从本地 offline/ 目录自动安装缺失依赖
"""

import os
import sys
import subprocess
import shutil
import importlib.util

# 颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

if os.name == "nt":
    try:
        subprocess.run("", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.system("")
    except Exception:
        pass


def is_windows():
    return os.name == "nt" or sys.platform == "win32"


def run_cmd(cmd, timeout=10):
    """执行命令，返回 (success, stdout, stderr)"""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode == 0, r.stdout, r.stderr
    except Exception:
        return False, "", ""


def check_py_import(module_name):
    """检查Python模块是否可导入"""
    spec = importlib.util.find_spec(module_name)
    return spec is not None


class DependencyChecker:
    """
    检查项定义:
    name        - 显示名称
    check_fn    - 检查函数 () -> (ok: bool, detail: str)
    install_fn  - 安装函数 () -> (ok: bool, msg: str)
    category    - 分类: python / system / ai / network
    required    - 是否必须（False=可选）
    """

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.offline_dir = os.path.join(self.base_dir, "offline")
        self.offline_pip = os.path.join(self.offline_dir, "pip")
        self.offline_tools = os.path.join(self.offline_dir, "tools")
        self.results = []
        self.has_offline = os.path.exists(self.offline_pip)

    # ==================== 检查函数 ====================

    def check_python_version(self):
        ok = sys.version_info >= (3, 8)
        return ok, f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def check_requests(self):
        ok = check_py_import("requests")
        if ok:
            import requests
            return True, f"requests {requests.__version__}"
        return False, "未安装"

    def check_colorama(self):
        ok = check_py_import("colorama")
        return ok, "colorama" if ok else "未安装"

    def check_pycryptodome(self):
        ok = check_py_import("Crypto") or check_py_import("Cryptodome")
        return ok, "pycryptodome" if ok else "未安装"

    def check_nmap(self):
        if is_windows():
            # Windows: 检查PATH或默认安装路径
            ok, _, _ = run_cmd("where nmap")
            if not ok:
                # 检查常见路径
                for path in [r"C:\Program Files (x86)\Nmap\nmap.exe",
                             r"C:\Program Files\Nmap\nmap.exe"]:
                    if os.path.exists(path):
                        return True, path
            return ok, "nmap" if ok else "未安装"
        else:
            ok, out, _ = run_cmd("nmap --version")
            if ok:
                version = out.split("\n")[0] if out else "已安装"
                return True, version[:50]
            return False, "未安装"

    def check_sqlmap(self):
        # 检查系统路径
        ok, _, _ = run_cmd("sqlmap --version")
        if ok:
            return True, "sqlmap (系统)"
        # 检查本地 offline
        local = os.path.join(self.offline_tools, "sqlmap", "sqlmap.py")
        if os.path.exists(local):
            return True, f"sqlmap (本地 {local})"
        return False, "未安装"

    def check_python_packages_full(self):
        """批量检查所有Python包"""
        packages = ["requests", "urllib3", "certifi", "charset_normalizer",
                    "idna", "colorama", "pycryptodome", "pygments"]
        missing = []
        for pkg in packages:
            if not check_py_import(pkg):
                missing.append(pkg)
        if not missing:
            return True, "全部已安装"
        return False, f"缺失: {', '.join(missing)}"

    def check_ai_config(self):
        """检查AI配置是否已填写"""
        config_file = os.path.join(self.base_dir, "config.py")
        if not os.path.exists(config_file):
            return False, "config.py 不存在"

        with open(config_file, encoding="utf-8") as f:
            content = f.read()

        import re

        # 检查是否有未配置的占位符
        if "YOUR_API_KEY" in content or "your-api-key" in content.lower():
            return False, "API Key 未配置"

        # 检查 PROVIDERS 结构
        if "PROVIDERS" not in content:
            return False, "未找到 PROVIDERS 配置"

        # 检查 CURRENT_PROVIDER
        m = re.search(r'CURRENT_PROVIDER\s*=\s*os\.environ\.get\([^,]+,\s*"([^"]+)"\)', content)
        if not m:
            return False, "未设置 CURRENT_PROVIDER"

        current = m.group(1)

        # 检查当前 provider 的 api_key
        # 读取 PROVIDERS 块，找到当前 provider 的 api_key
        providers_start = content.find("PROVIDERS")
        if providers_start == -1:
            return False, "PROVIDERS 块未找到"

        # 简单检查：看当前 provider 对应的 api_key 默认值是否为空
        # "openai": ... "api_key": os.environ.get("OPENAI_API_KEY", "")
        patterns = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "ollama-local": None,  # ollama 不需要 key
            "vllm": "VLLM_API_KEY",
        }
        env_key = patterns.get(current)
        if env_key:
            import os as _os
            key_val = _os.environ.get(env_key, "")
            if not key_val:
                return False, f"{current} API Key 未填写（需设置环境变量 {env_key}）"
        return True, f"已配置: {current}"

    def check_network(self):
        """检查网络连接"""
        try:
            import urllib.request
            urllib.request.urlopen("https://www.baidu.com", timeout=5)
            return True, "可访问互联网"
        except Exception:
            pass
        try:
            import socket
            sock = socket.socket()
            sock.settimeout(3)
            sock.connect(("8.8.8.8", 53))
            sock.close()
            return True, "仅内网可用"
        except Exception:
            pass
        return False, "网络不可用"

    def check_offline_files(self):
        """检查离线包是否已下载"""
        if not self.has_offline:
            return False, "offline/ 目录不存在"

        pip_files = []
        if os.path.exists(self.offline_pip):
            pip_files = [f for f in os.listdir(self.offline_pip) if f.endswith(".whl")]

        tools = []
        if os.path.exists(self.offline_tools):
            tools = os.listdir(self.offline_tools)

        if pip_files:
            return True, f"{len(pip_files)} 个wheel包, {len(tools)} 个工具"
        return False, "offline/ 目录为空"

    def check_git(self):
        ok, out, _ = run_cmd("git --version")
        if ok:
            return True, out.strip()
        return False, "未安装"

    # ==================== 安装函数 ====================

    def install_python_package(self, pkg_name):
        """从本地离线包安装 Python 包"""
        if not self.has_offline:
            return False, "离线包目录不存在"

        # 找对应的 wheel 文件
        wheel_files = [f for f in os.listdir(self.offline_pip) if f.endswith(".whl")]
        matched = None
        for wf in wheel_files:
            # wheel命名: 包名-版本-py版本-平台.whl
            base_name = wf.split("-")[0].lower().replace("_", "-")
            if base_name == pkg_name.lower().replace("_", "-"):
                matched = wf
                break

        if not matched:
            return False, f"本地未找到 {pkg_name} 的wheel文件"

        # 用 pip --no-index --find-links 让 pip 自己挑平台兼容的 wheel
        wheel_dir = self.offline_pip.replace("\\", "/")
        print(f"    安装: {pkg_name}（从本地 wheel）")
        ok, out, err = run_cmd(f'pip install --no-index --find-links="{wheel_dir}" "{pkg_name}" --quiet')
        if ok:
            return True, f"{pkg_name} 安装成功"
        else:
            return False, f"安装失败: {err[:100]}"

    def install_all_python_packages(self):
        """从本地离线包批量安装所有 Python 包（pip 自动处理平台兼容+依赖）"""
        if not self.has_offline:
            return False, "离线包目录不存在"

        wheel_files = [f for f in os.listdir(self.offline_pip) if f.endswith(".whl")]
        if not wheel_files:
            return False, "未找到wheel文件"

        wheel_dir = self.offline_pip.replace("\\", "/")
        print(f"    从 {wheel_dir} 批量安装 {len(wheel_files)} 个 wheel（pip 自动选平台）...")
        # pip install *.whl + --no-index 让 pip 自动处理平台过滤和依赖顺序
        ok, out, err = run_cmd(f'pip install --no-index --find-links="{wheel_dir}" "{wheel_dir}"/*.whl')
        if ok:
            return True, f"批量安装完成"
        else:
            # 失败时回退：逐个安装（忽略平台不兼容的）
            success, failed = 0, []
            for wf in wheel_files:
                wp = os.path.join(self.offline_pip, wf)
                o, _, e = run_cmd(f'pip install "{wp}" --quiet --no-deps')
                if o:
                    success += 1
                else:
                    failed.append(wf.split("-")[0])
            if failed:
                return True, f"已装 {success}/{len(wheel_files)}，平台不兼容可忽略: {', '.join(failed[:5])}"
            return True, f"全部 {success} 个包安装成功"

    def install_nmap(self):
        """安装 nmap"""
        nmap_offline = os.path.join(self.base_dir, "offline", "nmap")
        if not os.path.exists(nmap_offline):
            return False, "offline/nmap/ 目录不存在（需从网络下载）"

        # 找 nmap.exe
        for root, dirs, files in os.walk(nmap_offline):
            if "nmap.exe" in files:
                src = os.path.join(root, "nmap.exe")
                if is_windows():
                    dst = r"C:\Windows\System32\nmap.exe"
                    try:
                        shutil.copy2(src, dst)
                        return True, f"已复制到 {dst}"
                    except Exception as e:
                        return False, f"复制失败: {e}"
                else:
                    # Linux: 复制到 /usr/local/bin
                    try:
                        shutil.copy2(src, "/usr/local/bin/nmap")
                        os.chmod("/usr/local/bin/nmap", 0o755)
                        return True, "已复制到 /usr/local/bin/nmap"
                    except Exception as e:
                        return False, f"需要sudo: {e}"
        return False, "nmap.exe 未找到"

    def install_sqlmap(self):
        """安装 sqlmap（链接到系统 PATH）"""
        sqlmap_local = os.path.join(self.offline_tools, "sqlmap", "sqlmap.py")
        if not os.path.exists(sqlmap_local):
            return False, "本地 sqlmap 不存在"

        if is_windows():
            # Windows: 创建批处理文件到 PATH
            bat_path = r"C:\Windows\System32\sqlmap.bat"
            with open(bat_path, "w") as f:
                f.write(f'@echo off\npython "{sqlmap_local}" %*\n')
            return True, f"已创建 {bat_path}"
        else:
            # Linux: 创建符号链接
            try:
                link_path = "/usr/local/bin/sqlmap"
                if os.path.exists(link_path):
                    os.remove(link_path)
                os.symlink(sqlmap_local, link_path)
                return True, f"已链接到 {link_path}"
            except Exception as e:
                return False, f"需要sudo: {e}"

    def install_system_package(self, pkg_name):
        """通过系统包管理器安装"""
        if is_windows():
            # 检查 Chocolatey
            ok, _, _ = run_cmd("where choco")
            if ok:
                print(f"    通过 Chocolatey 安装: choco install {pkg_name} -y")
                ok2, _, err = run_cmd(f"choco install {pkg_name} -y", timeout=120)
                if ok2:
                    return True, f"{pkg_name} 安装成功"
                return False, f"Chocolatey 安装失败: {err[:100]}"

            return False, f"Windows请手动安装 {pkg_name}"
        else:
            # Linux apt
            print(f"    sudo apt-get install -y {pkg_name}")
            ok, _, err = run_cmd(f"sudo apt-get install -y -qq {pkg_name}", timeout=120)
            if ok:
                return True, f"{pkg_name} 安装成功"
            return False, f"安装失败: {err[:100]}"

    def run_all_checks(self):
        """执行所有检查，返回结果列表"""
        checks = [
            # category, name, required, check_fn
            ("环境", "Python 版本", True, self.check_python_version),
            ("Python", "requests", True, self.check_requests),
            ("Python", "colorama", True, self.check_colorama),
            ("Python", "pycryptodome", False, self.check_pycryptodome),
            ("系统", "nmap", False, self.check_nmap),
            ("系统", "sqlmap", False, self.check_sqlmap),
            ("系统", "git", False, self.check_git),
            ("AI", "AI配置", True, self.check_ai_config),
            ("网络", "网络连接", True, self.check_network),
            ("离线", "离线包", False, self.check_offline_files),
        ]

        self.results = []
        for category, name, required, check_fn in checks:
            try:
                ok, detail = check_fn()
            except Exception as e:
                ok, detail = False, f"检查出错: {e}"

            self.results.append({
                "category": category,
                "name": name,
                "required": required,
                "ok": ok,
                "detail": detail,
                "check_fn": check_fn,
            })

        return self.results

    def print_report(self):
        """打印检查报告"""
        # 按分类分组
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        # 计算状态
        required_ok = sum(1 for r in self.results if r["required"] and r["ok"])
        required_total = sum(1 for r in self.results if r["required"])
        all_ok = all(r["ok"] for r in self.results)

        status = f"{GREEN}✓ 全部就绪" if all_ok else f"{YELLOW}⚠ 部分缺失" if required_ok == required_total else f"{RED}✗ 缺少必要组件"
        print(f"\n{CYAN}{BOLD}━━━ 环境检查报告 ━━━{RESET}")
        print(f"  状态: {status}{RESET}  (必要项 {required_ok}/{required_total} 通过)")
        print()

        for cat, items in categories.items():
            print(f"  {CYAN}{cat}:{RESET}")
            for r in items:
                icon = f"{GREEN}✓" if r["ok"] else f"{RED}✗"
                tag = " [必]" if r["required"] else ""
                detail = r["detail"]
                print(f"    {icon} {r['name']:<20} {detail:<30}{tag}{RESET}")

        print()
        return all_ok, required_ok == required_total

    def get_missing_required(self):
        """获取缺失的必要项"""
        return [r for r in self.results if r["required"] and not r["ok"]]

    def get_missing_optional(self):
        """获取缺失的可选项"""
        return [r for r in self.results if not r["required"] and not r["ok"]]

    def install_missing(self, missing_items):
        """安装缺失的项"""
        print(f"\n{CYAN}━━━ 安装缺失依赖 ━━━{RESET}\n")

        success = []
        failed = []

        for item in missing_items:
            name = item["name"]
            print(f"  {CYAN}→{RESET} 安装 {name}...")

            ok, msg = False, ""

            # 根据名称选择安装方式
            if name == "Python 包":
                ok, msg = self.install_all_python_packages()
            elif name == "nmap":
                ok, msg = self.install_nmap()
            elif name == "sqlmap":
                ok, msg = self.install_sqlmap()
            elif name == "git":
                ok, msg = self.install_system_package("git")
            else:
                # 尝试从离线包安装 Python 包
                ok, msg = self.install_python_package(name)

            if ok:
                print(f"    {GREEN}✓{RESET} {msg}")
                success.append(name)
            else:
                print(f"    {RED}✗{RESET} {msg}")
                failed.append(name)

        print()
        if success:
            print(f"  {GREEN}已安装: {', '.join(success)}{RESET}")
        if failed:
            print(f"  {RED}失败: {', '.join(failed)}{RESET}")
            print(f"  {YELLOW}提示: 部分工具需要系统管理员权限，尝试用 sudo 运行{RESET}")

        return success, failed

    def interactive_fix(self):
        """交互式修复缺失项"""
        all_ok, required_ok = self.print_report()

        if all_ok:
            print(f"  {GREEN}所有组件已就绪，无需安装！{RESET}\n")
            return True

        print(f"\n{CYAN}━━━ 修复选项 ━━━{RESET}\n")
        print("  [1] 安装所有缺失的 Python 包 (从本地离线包)")
        print("  [2] 安装所有缺失的系统工具 (nmap/git/sqlmap)")
        print("  [3] 安装所有缺失项 (Python包 + 系统工具)")
        print("  [4] 重新检查")
        print("  [0] 跳过，继续启动")

        choice = input(f"\n  {CYAN}请选择 [0-4]{RESET}: ").strip()

        if choice == "1":
            # 只装 Python 包
            missing_py = [r for r in self.results if r["category"] == "Python" and not r["ok"]]
            if missing_py:
                self.install_missing(missing_py)
            else:
                print("  所有 Python 包已安装")
            return self.interactive_fix()

        elif choice == "2":
            # 只装系统工具
            missing_sys = [r for r in self.results if r["category"] == "系统" and not r["ok"]]
            if missing_sys:
                self.install_missing(missing_sys)
            else:
                print("  所有系统工具已安装")
            return self.interactive_fix()

        elif choice == "3":
            # 装所有
            all_missing = [r for r in self.results if not r["ok"]]
            if all_missing:
                self.install_missing(all_missing)
            else:
                print("  所有组件已安装")
            return self.interactive_fix()

        elif choice == "4":
            print()
            self.run_all_checks()
            return self.interactive_fix()

        else:
            print("  跳过安装检查")
            return required_ok == len([r for r in self.results if r["required"]])


def quick_check():
    """快速检查，仅打印状态不安装"""
    checker = DependencyChecker()
    checker.run_all_checks()
    all_ok, required_ok = checker.print_report()
    return all_ok


if __name__ == "__main__":
    checker = DependencyChecker()
    checker.run_all_checks()
    checker.interactive_fix()
