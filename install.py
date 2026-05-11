#!/usr/bin/env python3
"""
SecBot 环境安装脚本
自动检测平台 → 安装依赖 → 配置 AI → 检查环境
支持: Windows / Linux / WSL / Mac
"""

import os
import sys
import subprocess
import json
import shutil
import socket
import urllib.request
import urllib.error


# ==================== 常量 ====================
PROJECT_NAME = "SecBot"
REQUIRED_PYTHON = (3, 8)
REQUIRED_PACKAGES = ["requests"]
OPTIONAL_PACKAGES_LINUX = ["python3-pip", "nmap", "curl", "wget"]
OPTIONAL_PACKAGES_WIN = []

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Windows 色彩支持检测
if os.name == "nt":
    try:
        subprocess.run("", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.system("")  # 启用ANSI
    except Exception:
        pass

def is_windows():
    return os.name == "nt" or (sys.platform == "win32" or "CYGWIN" in sys.platform)

def is_wsl():
    return os.path.exists("/proc/version") and "microsoft" in open("/proc/version").read().lower()

def is_linux():
    return os.name == "posix" and not is_wsl()

def get_platform():
    if is_windows():
        return "windows"
    elif is_wsl():
        return "wsl"
    else:
        return "linux"


# ==================== 输出函数 ====================

def log(msg, color=""):
    prefix = {"green": "[✓] ", "red": "[✗] ", "yellow": "[!] ", "cyan": "[i] "}.get(color, "")
    end = RESET
    print(f"{color}{prefix}{msg}{RESET}")

def log_step(num, msg):
    print(f"\n{CYAN}{BOLD}━━━ 步骤 {num} ━━━{RESET}  {msg}")

def log_ok(msg):
    print(f"  {GREEN}{msg}{RESET}")

def log_fail(msg):
    print(f"  {RED}{msg}{RESET}")

def log_warn(msg):
    print(f"  {YELLOW}{msg}{RESET}")

def log_info(msg):
    print(f"  {CYAN}{msg}{RESET}")

def print_banner():
    plat = get_platform()
    plat_names = {"windows": "Windows", "wsl": "WSL (Linux)", "linux": "Linux"}
    print(f"""
{CYAN}╔═══════════════════════════════════════════════════╗
║         SecBot 环境安装脚本 v1.0                  ║
║         检测到平台: {plat_names.get(plat, plat):<28}║
╚═══════════════════════════════════════════════════╝{RESET}
""")


# ==================== 系统命令 ====================

def run(cmd, timeout=120, check=False, shell=True, capture=True):
    """执行命令，返回 (success, stdout, stderr)"""
    try:
        kw = {"shell": shell, "timeout": timeout}
        if capture:
            kw["capture_output"] = True
            kw["text"] = True
        result = subprocess.run(cmd, **kw)
        ok = (result.returncode == 0) if check else (result.returncode == 0)
        return ok, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return False, "", "命令超时"
    except FileNotFoundError:
        return False, "", "命令未找到"
    except Exception as e:
        return False, "", str(e)


def check_command(cmd):
    """检查命令是否存在"""
    if is_windows():
        ok, _, _ = run(f"where {cmd}", shell=True)
    else:
        ok, _, _ = run(f"which {cmd}", shell=True)
    return ok

def check_internet(url="https://www.baidu.com", timeout=5):
    """检测网络连接"""
    try:
        if is_windows():
            subprocess.run(["ping", "-n", "1", "-w", "1000", "8.8.8.8"],
                         capture_output=True, timeout=5)
        else:
            subprocess.run(["ping", "-c", "1", "-W", "1", "8.8.8.8"],
                         capture_output=True, timeout=5)
        return True
    except Exception:
        pass
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


# ==================== 步骤 1: Python 检查 ====================

def step1_check_python():
    log_step(1, "检查 Python 环境")
    version = sys.version_info
    if version >= REQUIRED_PYTHON:
        log_ok(f"Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
    else:
        log_fail(f"Python 版本过低，需要 {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+")
        return False


# ==================== 步骤 2: 安装系统依赖 ====================

def step2_install_system_deps():
    log_step(2, "安装系统依赖")
    plat = get_platform()

    if plat == "windows":
        return step2_windows()
    elif plat in ("linux", "wsl"):
        return step2_linux()
    else:
        log_warn("未知平台，跳过系统依赖安装")
        return True

def step2_windows():
    """Windows: 检查/提示安装可选工具"""
    log_info("Windows 平台，跳过 nmap 等系统工具自动安装")
    log_info("推荐手动安装以下工具（可选）：")
    log_info("  - nmap: https://nmap.org/download.html")
    log_info("  - sqlmap: https://sqlmap.org/")
    log_info("  - Git Bash (含 curl/wget): https://git-scm.com/download/win")

    # 检查 Chocolatey
    ok, _, _ = run("where choco", shell=True)
    if ok:
        log_info("检测到 Chocolatey，可以用它安装：")
        log_info("  choco install nmap sqlmap -y")
    return True

def step2_linux():
    """Linux/WSL: apt 安装工具"""
    log_info("检测 Linux/WSL 环境")

    # 检查 nmap
    if check_command("nmap"):
        log_ok("nmap 已安装 ✓")
    else:
        log_info("安装 nmap...")
        run("sudo apt-get update -qq && sudo apt-get install -y -qq nmap",
            timeout=180, check=False)

    # 检查 curl
    if check_command("curl"):
        log_ok("curl 已安装 ✓")
    else:
        run("sudo apt-get install -y -qq curl", timeout=60)

    # 检查 git
    if check_command("git"):
        log_ok("git 已安装 ✓")
    else:
        run("sudo apt-get install -y -qq git", timeout=60)

    # 检查 pip
    if check_command("pip3") or check_command("pip"):
        log_ok("pip 已安装 ✓")
    else:
        log_info("安装 pip3...")
        run("sudo apt-get install -y -qq python3-pip", timeout=60)

    # 再次检查
    all_ok = all(check_command(cmd) for cmd in ["nmap", "curl", "pip3"])
    if all_ok:
        log_ok("所有系统工具安装完成 ✓")
    return True


def _pip_install(pkg_spec, timeout=60):
    """pip 安装，带 Ubuntu 24.04 兼容处理"""
    # 先尝试普通安装，再尝试 --break-system-packages (Ubuntu 24.04)
    for flag in ["", "--user", "--break-system-packages"]:
        cmd = f'pip install {pkg_spec}'
        if flag:
            cmd += f" {flag}"
        ok, _, _ = run(cmd, timeout=timeout)
        if ok:
            return True
    return False


# ==================== 步骤 3: 安装 Python 包 ====================

def step3_install_python_packages():
    log_step(3, "安装 Python 依赖包")

    # 检查是否有离线包
    offline_pkg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline", "pip")
    offline_mode = os.path.exists(offline_pkg_dir) and os.listdir(offline_pkg_dir)

    if offline_mode:
        log_info(f"检测到离线包目录: offline/pip/")
        log_info("优先使用离线包安装...")

        pkg_files = [f for f in os.listdir(offline_pkg_dir) if f.endswith((".whl", ".tar.gz"))]
        log_info(f"找到 {len(pkg_files)} 个离线包")

        success = 0
        for pkg_file in pkg_files:
            pkg_path = os.path.join(offline_pkg_dir, pkg_file)
            ok = _pip_install(f'"{pkg_path}" --no-deps', timeout=60)
            if ok:
                success += 1

        log_ok(f"离线包安装完成: {success}/{len(pkg_files)}")
        return True

    # 在线模式
    log_info("无离线包，从 PyPI 在线安装...")
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if os.path.exists(req_file):
        ok = _pip_install(f'-r "{req_file}"', timeout=120)
        if ok:
            log_ok("Python 包安装完成 ✓")
        else:
            log_warn("部分包安装失败，尝试安装核心包...")
            _pip_install("requests colorama", timeout=60)
    else:
        ok = _pip_install("requests colorama", timeout=60)
        if ok:
            log_ok("核心包安装完成 ✓")

    return True


# ==================== 步骤 4: 配置 AI ====================

def step4_config_ai():
    log_step(4, "配置 AI 模型")
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")

    if not os.path.exists(config_file):
        log_fail(f"config.py 未找到，请确保在 {PROJECT_NAME} 目录下运行")
        return False

    print(f"""
{CYAN}  请选择 AI 提供商:{RESET}
""")
    print("  [1] OpenAI (GPT-4o / GPT-4)       ← 推荐，需 API Key")
    print("  [2] Claude (Anthropic)             ← 需 API Key")
    print("  [3] Ollama 本地模型               ← 免费，需本地安装 Ollama")
    print("  [4] vLLM / Groq (OpenAI兼容)     ← 需服务器地址")
    print()

    choice = input(f"  请选择 [1-4] (默认1): ").strip() or "1"

    api_key = ""
    base_url = ""
    model = ""

    if choice == "1":
        api_key = input("  OpenAI API Key: ").strip()
        if not api_key:
            log_warn("未输入 API Key，将使用默认配置")
            api_key = "YOUR_API_KEY"
        model = input("  模型名 [默认: gpt-4o]: ").strip() or "gpt-4o"
        config_value = f'''MODEL_PROVIDER = "openai"
OPENAI_API_KEY = "{api_key}"
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "{model}"'''

    elif choice == "2":
        api_key = input("  Anthropic API Key: ").strip()
        if not api_key:
            api_key = "YOUR_API_KEY"
        model = input("  模型名 [默认: claude-sonnet-4-20250514]: ").strip() or "claude-sonnet-4-20250514"
        config_value = f'''MODEL_PROVIDER = "anthropic"
ANTHROPIC_API_KEY = "{api_key}"
ANTHROPIC_MODEL = "{model}"'''

    elif choice == "3":
        log_info("Ollama 模式")
        model = input("  模型名 [默认: qwen2.5-coder:7b]: ").strip() or "qwen2.5-coder:7b"
        base_url = input("  Ollama 地址 [默认: http://localhost:11434]: ").strip() or "http://localhost:11434"
        config_value = f'''MODEL_PROVIDER = "ollama"
OLLAMA_BASE_URL = "{base_url}"
OLLAMA_MODEL = "{model}"'''

    elif choice == "4":
        base_url = input("  API 地址 (如 https://your-vllm.com/v1): ").strip()
        if not base_url:
            base_url = "http://localhost:8000/v1"
        api_key = input("  API Key (可留空): ").strip() or "EMPTY"
        model = input("  模型名: ").strip() or "qwen2.5-7b"
        config_value = f'''MODEL_PROVIDER = "openai"
OPENAI_API_KEY = "{api_key}"
OPENAI_BASE_URL = "{base_url}"
OPENAI_MODEL = "{model}"'''

    else:
        log_fail("无效选择")
        return False

    # 读取现有 config.py
    with open(config_file, encoding="utf-8") as f:
        config_content = f.read()

    # 替换相关配置块
    import re

    # 替换 MODEL_PROVIDER 块
    new_config = re.sub(
        r'MODEL_PROVIDER\s*=\s*os\.environ\.get\([^)]+\)',
        f'MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "{choice_map_to_provider(choice)}")',
        config_content
    )

    # 追加或替换配置
    marker = "# ==================== 安装脚本配置 ===================="
    new_block = f"""{marker}
# 以下配置由安装脚本自动生成
MODEL_PROVIDER = "{choice_map_to_provider(choice)}"
OPENAI_API_KEY = "{api_key}"
OPENAI_BASE_URL = "{base_url or 'https://api.openai.com/v1'}"
OPENAI_MODEL = "{model}"
OLLAMA_BASE_URL = "{base_url or 'http://localhost:11434'}"
OLLAMA_MODEL = "{model}"
ANTHROPIC_API_KEY = "{api_key}"
ANTHROPIC_MODEL = "{model}"
"""

    if marker in new_config:
        # 替换已有块
        new_config = re.sub(
            rf'{re.escape(marker)}.*?(?=\n#|\Z)',
            new_block.strip(),
            new_config,
            flags=re.DOTALL
        )
    else:
        # 追加
        new_config += "\n" + new_block

    with open(config_file, "w", encoding="utf-8") as f:
        f.write(new_config)

    log_ok("AI 配置已写入 config.py ✓")
    return True


def choice_map_to_provider(choice):
    return {"1": "openai", "2": "anthropic", "3": "ollama", "4": "openai"}.get(choice, "openai")


# ==================== 步骤 5: 检查网络 ====================

def step5_check_network():
    log_step(5, "检查网络连接")

    if check_internet():
        log_ok("网络连接正常 ✓")
        return True
    else:
        log_warn("无法访问互联网")
        log_info("可能处于内网隔离环境")
        log_info("将使用 U盘模式 / Ollama 本地模式")
        return False


# ==================== 步骤 6: 测试 AI ====================

def step6_test_ai():
    log_step(6, "测试 AI 连接")

    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")

    # 读取 provider
    import re
    with open(config_file, encoding="utf-8") as f:
        content = f.read()

    m = re.search(r'MODEL_PROVIDER\s*=\s*"([^"]+)"', content)
    provider = m.group(1) if m else None

    if not provider:
        log_fail("未找到 MODEL_PROVIDER 配置")
        return False

    if provider == "ollama":
        m_url = re.search(r'OLLAMA_BASE_URL\s*=\s*"([^"]+)"', content)
        url = m_url.group(1) if m_url else "http://localhost:11434"
        log_info(f"测试 Ollama: {url}")

        try:
            import requests
            r = requests.get(f"{url}/api/tags", timeout=10)
            if r.status_code == 200:
                models = [x["name"] for x in r.json().get("models", [])]
                log_ok(f"Ollama 在线，可用模型: {models} ✓")
                return True
        except Exception as e:
            log_fail(f"Ollama 连接失败: {e}")
            return False

    elif provider == "openai":
        m_key = re.search(r'OPENAI_API_KEY\s*=\s*"([^"]+)"', content)
        m_url = re.search(r'OPENAI_BASE_URL\s*=\s*"([^"]+)"', content)
        api_key = m_key.group(1) if m_key else ""
        base_url = m_url.group(1) if m_url else "https://api.openai.com/v1"

        if not api_key or api_key == "YOUR_API_KEY":
            log_warn("未配置有效 API Key，跳过测试")
            return False

        log_info("测试 OpenAI API...")
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            r = requests.get(f"{base_url}/models", headers=headers, timeout=15)
            if r.status_code == 200:
                models = r.json().get("data", [])
                log_ok(f"API 连接成功，共 {len(models)} 个模型 ✓")
                return True
            else:
                log_fail(f"API 错误: HTTP {r.status_code}")
        except Exception as e:
            log_fail(f"连接失败: {e}")
        return False

    elif provider == "anthropic":
        m_key = re.search(r'ANTHROPIC_API_KEY\s*=\s*"([^"]+)"', content)
        api_key = m_key.group(1) if m_key else ""

        if not api_key or api_key == "YOUR_API_KEY":
            log_warn("未配置有效 API Key，跳过测试")
            return False

        log_info("测试 Claude API...")
        try:
            import requests
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01",
                      "content-type": "application/json"}
            r = requests.post("https://api.anthropic.com/v1/messages",
                            headers=headers,
                            json={"model": "claude-sonnet-4-20250514",
                                  "max_tokens": 10, "messages": []},
                            timeout=15)
            if r.status_code in (200, 400):  # 400=认证成功但body空
                log_ok("Claude API 连接成功 ✓")
                return True
            else:
                log_fail(f"API 错误: HTTP {r.status_code}")
        except Exception as e:
            log_fail(f"连接失败: {e}")
        return False


# ==================== 步骤 7: 检查/下载安全工具 ====================

def step7_download_tools():
    log_step(7, "检查/下载安全工具")

    tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline", "tools")
    os.makedirs(tools_dir, exist_ok=True)

    # 检查离线工具
    sqlmap_dir = os.path.join(tools_dir, "sqlmap")
    if os.path.exists(sqlmap_dir):
        log_ok(f"sqlmap 已存在 (offline/tools/sqlmap) ✓")
    else:
        # 检查zip
        zip_files = [f for f in os.listdir(tools_dir) if "sqlmap" in f.lower() and f.endswith(".zip")]
        if zip_files:
            log_ok(f"找到 sqlmap 离线包: {zip_files[0]} ✓")
        else:
            log_info("sqlmap 未找到，请手动放入 offline/tools/sqlmap/")
            log_info("下载地址: https://github.com/sqlmapproject/sqlmap/releases")

    # 检查nmap
    nmap_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline", "nmap")
    nmap_files = []
    if os.path.exists(nmap_dir):
        nmap_files = [f for f in os.listdir(nmap_dir) if "nmap" in f.lower() and (f.endswith(".exe") or f.endswith(".zip"))]
    if nmap_files:
        log_ok(f"nmap 已存在: {nmap_files[0]} ✓")
    else:
        plat = get_platform()
        if plat == "windows":
            log_info("nmap 未找到，请下载放入 offline/nmap/")
            log_info("下载地址: https://nmap.org/dist/nmap-7.95-win32.zip")
        else:
            if check_command("nmap"):
                log_ok("nmap 已安装 ✓")
            else:
                log_info("nmap 未安装: sudo apt install nmap")

    return True


# ==================== 步骤 8: 创建快捷启动 ====================

def step8_create_shortcuts():
    log_step(8, "创建快捷启动")

    plat = get_platform()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")

    if plat == "windows":
        # 创建 .bat 启动脚本
        bat_path = os.path.join(script_dir, "SecBot启动.bat")
        bat_content = f'@echo off\ncd /d "{script_dir}"\npython "{main_py}"\npause'
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        log_ok(f"已创建: {bat_path}")

        # 创建桌面快捷方式 (可选)
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        desktop_bat = os.path.join(desktop, "SecBot启动.bat")
        try:
            with open(desktop_bat, "w", encoding="utf-8") as f:
                f.write(bat_content)
            log_ok(f"已创建桌面快捷: {desktop_bat}")
        except Exception:
            pass

    else:
        # Linux/WSL: 创建 shell 脚本
        sh_path = os.path.join(script_dir, "secbot.sh")
        sh_content = f'''#!/bin/bash
cd "{script_dir}"
python3 "{main_py}"
'''
        with open(sh_path, "w", encoding="utf-8") as f:
            f.write(sh_content)
        os.chmod(sh_path, 0o755)
        log_ok(f"已创建: {sh_path}")

        # 桌面快捷方式
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        desktop_sh = os.path.join(desktop, "SecBot.desktop")
        desktop_content = f'''[Desktop Entry]
Name=SecBot
Comment=智能网络安全工具箱
Exec=python3 "{main_py}"
Terminal=true
Type=Application
Categories=Network;Security;
'''
        try:
            with open(desktop_sh, "w", encoding="utf-8") as f:
                f.write(desktop_content)
            os.chmod(desktop_sh, 0o755)
            log_ok(f"已创建桌面快捷: {desktop_sh}")
        except Exception:
            pass

    return True


# ==================== 完成 ====================

def show_complete(has_network, ai_works):
    print(f"""
{GREEN}╔═══════════════════════════════════════════════════╗
║              ✅ SecBot 安装完成!                  ║
╚═══════════════════════════════════════════════════╝{RESET}
""")

    plat = get_platform()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if plat == "windows":
        print(f"  启动方式: SecBot启动.bat 或 python main.py")
    else:
        print(f"  启动方式: bash secbot.sh 或 python3 main.py")

    print(f"""
  启动命令:
    cd {script_dir}
    python main.py        (Linux/WSL)
    python main.py        (Windows)

  AI 配置:
    {'✓ 已配置并测试成功' if ai_works else '⚠  请手动检查 API Key'}
    config.py 已写入 AI 配置

  下一步:
    1. 运行 SecBot: python main.py
    2. 选择 [1] 进行内网扫描
    3. 选择 [2] 启动 AI 自动渗透
    4. 选择 [C] 开始 CTF 解题

  提示:
    - U盘模式: 内网隔离时先扫描导出，再拿到外网分析
    - 按 [P] 切换 AI 提供商
    - 按 [S] 切换运行模式
""")

    if not has_network:
        print(f"""
  {YELLOW}⚠  未检测到互联网连接{RESET}
  将自动使用 Ollama 本地模式或 U盘隔离模式
  请确保 Ollama 已启动: ollama serve
""")


# ==================== 主函数 ====================

def main():
    print_banner()

    # 步骤 1: Python
    if not step1_check_python():
        log_fail("Python 版本不满足要求，安装终止")
        input("\n按回车退出...")
        sys.exit(1)

    # 步骤 2: 系统依赖
    step2_install_system_deps()

    # 步骤 3: Python 包
    step3_install_python_packages()

    # 步骤 4: 配置 AI
    if not step4_config_ai():
        log_fail("AI 配置失败")
        retry = input("是否重试? [Y/n]: ").strip().lower()
        if retry != "n":
            step4_config_ai()

    # 步骤 5: 检查网络
    has_network = step5_check_network()

    # 步骤 6: 测试 AI
    ai_works = step6_test_ai()
    if not ai_works and has_network:
        log_warn("AI 测试失败，检查 API Key 是否正确")
        retry = input("是否重新配置 AI? [y/N]: ").strip().lower()
        if retry == "y":
            step4_config_ai()
            ai_works = step6_test_ai()

    # 步骤 7: 检查工具
    step7_download_tools()

    # 步骤 8: 创建快捷方式
    step8_create_shortcuts()

    # 完成
    show_complete(has_network, ai_works)

    input("\n按回车退出安装程序...")
    sys.exit(0)


if __name__ == "__main__":
    main()
