#!/usr/bin/env python3
"""
SecBot - 智能网络安全工具箱
支持: 内网扫描 / AI自动渗透 / CTF解题 / U盘隔离模式
自动检测网络环境: 互联网 / 内网隔离 / 完全隔离
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import SecBotAgent
from core.network_detector import NetworkDetector
from core.task_queue import TaskQueue, Task
from modules.ollama_client import UnifiedClient
from config import MODEL_PROVIDER, DEFAULT_MODEL


def print_banner():
    agent = SecBotAgent()
    status = agent.get_status()
    env_names = {"internet": "🌐 互联网", "intranet": "🔒 内网隔离", "isolated": "⚡ 完全隔离"}
    env = env_names.get(status["environment"], status["environment"])
    provider_names = {"ollama": "本地 Ollama", "openai": "OpenAI 兼容", "anthropic": "Claude"}

    print(f"""
╔══════════════════════════════════════════════════╗
║           SecBot - 智能网络安全工具箱             ║
║  网络: {env:<40}  ║
║  AI:   {provider_names.get(status['provider'], status['provider']):<40}  ║
║  模型: {status['model']:<40}  ║
╚══════════════════════════════════════════════════╝
""")


def menu():
    return f"""
╔══════════════════════════════════════════════════╗
║               SecBot 主菜单                      ║
╠══════════════════════════════════════════════════╣
║  [1]  🔍 内网扫描         - 扫描目标网段/主机     ║
║  [2]  🤖 AI自动渗透       - 扫描→分析→执行全流程  ║
║  [3]  📋 任务列表         - 查看/管理任务队列      ║
║  [4]  ➕ 添加任务         - 手工添加任务           ║
║  [5]  ▶️  执行任务队列    - 运行待执行任务        ║
║  [6]  📤 导出结果         - 导出扫描/任务数据     ║
║  [7]  🔴 渗透测试工具集   - 端口/目录/爆破/API分析║
║  [W]  🌐 Web界面          - 浏览器图形化操作      ║
║                                                  ║
║  [D]  🔧 检查依赖         - 检查/安装缺失组件     ║
║  [S]  切换模式            - Auto/Semi/Manual/UDISK║
║  [P]  切换AI提供商        - Ollama/OpenAI/Claude  ║
║  [C]  CTF解题             - 直接丢题目给我做     ║
║  [R]  刷新状态                                    ║
║                                                  ║
║  [0]  退出                                        ║
╚══════════════════════════════════════════════════╝
"""


def switch_mode(agent):
    print("""
╔══════════════════════════════╗
║  选择运行模式                 ║
╠══════════════════════════════╣
║  [1] AutoRun   - 全自动渗透  ║
║  [2] SemiAuto  - 半自动(每步 ║
║                  确认)       ║
║  [3] Manual    - 全手动      ║
║  [4] UDiskMode - U盘隔离模式 ║
║  [0] 返回                     ║
╚══════════════════════════════╝
""")
    choice = input("> ").strip()
    modes = {"1": "AutoRun", "2": "SemiAuto", "3": "Manual", "4": "UDiskMode"}
    if choice in modes:
        agent.set_mode(modes[choice])
    input("\n按回车继续...")


def switch_provider():
    print("""
╔══════════════════════════════╗
║  选择AI提供商                 ║
╠══════════════════════════════╣
║  [1] Ollama    - 本地模型    ║
║  [2] OpenAI    - OpenAI/vLLM║
║  [3] Claude    - Anthropic  ║
║  [0] 返回                     ║
╚══════════════════════════════╝
""")
    choice = input("> ").strip()
    providers = {"1": "ollama", "2": "openai", "3": "anthropic"}
    if choice in providers:
        os.environ["MODEL_PROVIDER"] = providers[choice]
        print(f"[*] 已切换到: {providers[choice]}")
        print("[!] 请重启 SecBot 使配置生效")
    input("\n按回车继续...")


def do_scan(agent):
    print("\n[*] 内网扫描")
    print("    格式示例: 192.168.1.0/24 或 192.168.1.1")
    target = input("目标> ").strip()
    if not target:
        print("[-] 目标不能为空")
        return

    full = input("全端口扫描? (y/N)> ").strip().lower() == "y"

    filepath = agent.scan_target(target, full_scan=full)
    print(f"\n[+] 扫描结果: {filepath}")

    # 询问是否立即分析
    if agent.network.detect() == "internet":
        cont = input("\n是否让AI自动分析并生成任务? (Y/n)> ").strip().lower()
        if cont != "n":
            # 执行一轮AI规划
            from scanner_iso.isolated_scanner import IsolatedScanner
            scanner = IsolatedScanner()
            # 重新加载结果
            import json
            try:
                with open(filepath) as f:
                    results = json.load(f)
                agent._plan_from_scan_results(results)
            except Exception as e:
                print(f"[!] 自动规划失败: {e}")

    input("\n按回车继续...")


def do_auto_penetrate(agent):
    print("\n[*] AI自动渗透模式")
    network = agent.network.summary()
    print(f"    当前环境: {network['description']}")

    if network["environment"] == "intranet":
        print("[!] 处于内网隔离环境")
        print("    1. 先用内置扫描器收集数据")
        print("    2. 导出数据到U盘")
        print("    3. 拿到互联网机器分析")
        print("    4. 带回任务文件执行")
        target = input("\n目标网段 (直接回车跳过扫描)> ").strip()
        if target:
            agent.scan_target(target)
        export = input("导出U盘数据? (y/N)> ").strip().lower()
        if export == "y":
            path = agent.udisk_export()
            print(f"[+] 已导出到: {path}")
    else:
        target = input("目标网段/IP> ").strip()
        if not target:
            print("[-] 目标不能为空")
            return
        agent.scan_target(target)
        agent.run_tasks(max_iterations=10)

    input("\n按回车继续...")


def do_add_task(agent):
    print("\n[*] 添加任务")
    print("    类型: scan / exploit / recon / analyze / custom")
    task_type = input("任务类型> ").strip()
    description = input("描述> ").strip()
    command = input("命令> ").strip()
    target = input("目标(可选)> ").strip() or None

    if task_type and description and command:
        agent.add_task(task_type, description, command, target)
    else:
        print("[-] 类型、描述、命令不能为空")

    input("\n按回车继续...")


def do_ctf(agent):
    print("\n[*] CTF解题 - 直接粘贴题目内容")
    print("    输入 'back' 返回\n")
    description = input("题目描述/标题> ").strip()
    if description.lower() == "back":
        return

    print("\n[粘贴题目内容，输入空行结束]")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    content = "\n".join(lines)

    print("\n[*] AI分析中...")
    prompt = f"""你是一个专业的CTF选手。请分析以下题目，给出完整解题步骤和最终flag。

## 题目
{description}

## 题目内容
{content}

## 输出格式
## 分析

## 解题步骤
1. ...

## 最终答案
flag{{...}}
"""

    from config import MODEL_PROVIDER
    llm = UnifiedClient(provider=MODEL_PROVIDER)
    result = llm.generate(prompt)

    print("\n" + "=" * 50)
    print("AI 分析结果:")
    print("=" * 50)
    print(result)
    print("=" * 50)

    # 提取flag
    import re
    flags = re.findall(r"flag\{[^}]+\}", result, re.IGNORECASE)
    if flags:
        print(f"\n[!] 找到 FLAG: {flags[0]}")

    input("\n按回车继续...")


def do_check_dependencies():
    """依赖检查与修复"""
    from core.check_dependencies import DependencyChecker

    print()
    checker = DependencyChecker()
    checker.run_all_checks()
    checker.interactive_fix()
    input("\n按回车继续...")


def main():
    # 启动时自动检查依赖（快速模式，不阻塞）
    from core.check_dependencies import DependencyChecker
    try:
        checker = DependencyChecker()
        checker.run_all_checks()
        missing = checker.get_missing_required()
        if missing:
            print()
            print("  [D] 按 D 键查看/修复缺失依赖")
            for m in missing:
                print(f"       - {m['category']}: {m['name']}")
            print()
    except Exception:
        pass

    print_banner()
    agent = SecBotAgent()

    while True:
        try:
            os.system("clear" if os.name != "nt" else "cls")
            print_banner()
            print(menu())

            choice = input("SecBot> ").strip()

            if choice == "0" or choice == "q" or choice == "quit":
                print("\n[i] 再见!")
                break
            elif choice == "1":
                do_scan(agent)
            elif choice == "2":
                do_auto_penetrate(agent)
            elif choice == "3":
                agent.list_tasks()
                input("\n按回车继续...")
            elif choice == "4":
                do_add_task(agent)
            elif choice == "5":
                agent.run_tasks()
                input("\n按回车继续...")
            elif choice == "6":
                path = agent.export_results()
                print(f"[+] 已导出: {path}")
                input("\n按回车继续...")
            elif choice == "7":
                from pentest import run_pentest_menu
                run_pentest_menu()
            elif choice.lower() == "d":
                do_check_dependencies()
            elif choice.lower() == "w":
                import subprocess, sys
                print("\n[*] 正在启动 Web 界面...")
                print("[*] 浏览器打开: http://localhost:8501")
                print("[*] 按 Ctrl+C 停止 Web 服务\n")
                subprocess.run([sys.executable, "-m", "streamlit", "run",
                                 os.path.join(os.path.dirname(__file__), "web_app.py"),
                                 "--server.port", "8501", "--server.headless", "true"])
                input("\n按回车继续...")
            elif choice.lower() == "s":
                switch_mode(agent)
            elif choice.lower() == "p":
                switch_provider()
                input("\n按回车继续...")
            elif choice.lower() == "c":
                do_ctf(agent)
            elif choice.lower() == "r":
                agent.print_status()
                input("\n按回车继续...")
            else:
                print(f"[!] 未知命令: {choice}")

        except KeyboardInterrupt:
            print("\n\n[*] 使用 '0' 退出")
            time.sleep(1)
        except Exception as e:
            print(f"\n[!] 错误: {e}")
            import traceback
            traceback.print_exc()
            input("\n按回车继续...")


if __name__ == "__main__":
    main()
