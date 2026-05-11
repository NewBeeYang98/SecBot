"""
SecBot Agent - 核心大脑
自动规划 → 执行 → 分析 → 迭代
支持 Internet/Intranet 两种模式自动切换
"""

import json
import re
import os
import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_queue import TaskQueue, Task, TaskStatus
from core.executor import TaskExecutor
from core.network_detector import NetworkDetector
from modules.ollama_client import ModelClient as UnifiedClient
from config import CURRENT_PROVIDER


class SecBotAgent:
    """
    SecBot 核心Agent

    工作模式:
    1. AutoRun   - 全自动: 扫描→AI分析→生成任务→执行→迭代
    2. SemiAuto  - 半自动: AI分析后等待确认再执行
    3. Manual     - 手动: 所有任务手工创建
    4. UDiskMode  - U盘模式: 内网零依赖扫描→导出→拿到外网分析→带回任务→执行
    """

    def __init__(self, provider=None, model=None):
        self.provider = provider or CURRENT_PROVIDER
        self.model = model
        self.llm = UnifiedClient(provider_name=self.provider)
        self.queue = TaskQueue()
        self.executor = TaskExecutor()
        self.network = NetworkDetector()
        self.mode = "AutoRun"

    # ==================== 模式 ====================

    def set_mode(self, mode: str):
        modes = ["AutoRun", "SemiAuto", "Manual", "UDiskMode"]
        if mode not in modes:
            print(f"[!] 未知模式: {mode}，可用: {modes}")
            return
        self.mode = mode
        print(f"[*] 模式切换: {mode}")

    def get_status(self) -> dict:
        """获取Agent当前状态"""
        env = self.network.detect()
        return {
            "mode": self.mode,
            "environment": env,
            "provider": self.llm.provider_name,
            "model": self.llm.model(),
            "model_status": self.llm.check_status(),
            "queue": self.queue.summary(),
            "network": self.network.summary(),
        }

    def print_status(self):
        """打印状态"""
        status = self.get_status()
        env_names = {"internet": "互联网", "intranet": "内网(隔离)", "isolated": "完全隔离"}
        print("\n" + "=" * 50)
        print(f"  SecBot Agent 状态")
        print("=" * 50)
        print(f"  模式:      {status['mode']}")
        print(f"  环境:      {env_names.get(status['environment'], status['environment'])} ({status['network']['local_ip']})")
        print(f"  AI模型:    {status['provider']} / {status['model']}")
        llm_ok = status['model_status'][0]
        print(f"  AI状态:    {'✓ 可用' if llm_ok else '✗ 不可用'}")
        print("-" * 50)
        print(f"  任务队列:  总 {status['queue']['total']} | 待执行 {status['queue']['pending']} | 完成 {status['queue']['done']} | 失败 {status['queue']['failed']}")
        print("=" * 50)

    # ==================== 扫描 ====================

    def scan_target(self, target: str, full_scan=False) -> str:
        """对目标执行内网扫描"""
        print(f"\n[*] 开始扫描: {target}")

        # 优先用内置扫描器（零依赖）
        try:
            from scanner_iso.isolated_scanner import IsolatedScanner
            scanner = IsolatedScanner()
            results = scanner.run(target, full_scan=full_scan)

            # 保存结果
            output_file = scanner.export()
            print(f"[+] 扫描完成: {output_file}")

            # 自动生成AI分析任务
            if self.network.detect() == "internet":
                self._plan_from_scan_results(results)
            else:
                # 内网隔离模式，导出供后续分析
                scanner.export_tasks()

            return output_file

        except ImportError:
            # 降级: 用nmap
            print("[!] 内置扫描器不可用，尝试nmap...")
            cmd = f"nmap -sV -T4 -p 1-1000,3306,3389,22,80,443,8080 {target}"
            output = self.executor.execute_shell(cmd, timeout=300)
            return output

    def _plan_from_scan_results(self, scan_results: dict):
        """基于扫描结果，让AI规划下一步任务"""
        print("\n[*] 让AI分析扫描结果...")

        prompt = f"""你是一个资深渗透测试工程师。已经完成内网扫描，结果如下:

扫描目标: {scan_results.get('target')}
存活主机: {scan_results['scan']['summary']['alive']} 台

发现的资产:
{json.dumps(scan_results.get('overview', {}), ensure_ascii=False, indent=2)}

请制定渗透测试计划，输出一系列具体任务。
每个任务包含: type( scan/exploit/recon ), description, command, target, tags

重点关注:
1. Web服务探测和指纹识别
2. 高危端口服务(445/1433/3306/3389)的利用可能性
3. 内网横移路径

输出JSON格式的任务数组，例如:
[
  {{"type": "scan", "description": "Web指纹识别", "command": "curl -s http://192.168.1.10", "target": "http://192.168.1.10", "tags": ["web"]}},
  {{"type": "exploit", "description": "SMB版本检测", "command": "nmap --script smb-os-discovery 192.168.1.10", "target": "192.168.1.10", "tags": ["smb"]}}
]
"""

        response = self.llm.generate(prompt)
        print(f"[AI分析]\n{response[:500]}...")

        # 解析任务
        tasks = self._parse_tasks_from_response(response)
        if tasks:
            self.queue.add_batch([Task(**t) for t in tasks])
            print(f"[+] 已添加 {len(tasks)} 个任务到队列")

    def _parse_tasks_from_response(self, response: str) -> list:
        """从AI响应中解析任务列表"""
        # 尝试提取JSON
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 降级: 简单解析markdown列表
        tasks = []
        lines = response.split("\n")
        current = {}
        for line in lines:
            if line.startswith("##") or line.startswith("**"):
                continue
            if "- type:" in line or "type:" in line:
                m = re.search(r'type[:\s]+(\w+)', line)
                if m:
                    current["type"] = m.group(1)
            if "- description:" in line or "description:" in line:
                m = re.search(r'description[:\s]+(.+)', line)
                if m:
                    current["description"] = m.group(1).strip()
            if "- command:" in line or "command:" in line:
                m = re.search(r'command[:\s]+(.+)', line)
                if m:
                    current["command"] = m.group(1).strip()
            if "- target:" in line or "target:" in line:
                m = re.search(r'target[:\s]+(.+)', line)
                if m:
                    current["target"] = m.group(1).strip()

            # 完整对象
            if len(current) >= 3:
                if "type" in current and "description" in current:
                    tasks.append(current.copy())
                current = {}

        return tasks

    # ==================== 任务执行 ====================

    def run_tasks(self, max_iterations=10):
        """
        自动运行任务队列
        支持迭代: 执行 → 收集结果 → AI分析 → 生成新任务 → 重复
        """
        print(f"\n[*] 开始执行任务队列 (模式: {self.mode})")
        print(f"[*] 最多迭代: {max_iterations} 次")
        print("=" * 50)

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- 迭代 {iteration}/{max_iterations} ---")

            pending = self.queue.get_pending()
            if not pending:
                print("[*] 没有待执行任务")
                break

            print(f"[*] 待执行任务: {len(pending)} 个")

            for task in pending[:5]:  # 每轮最多执行5个
                self.queue.update_status(task.id, TaskStatus.RUNNING)
                success, output = self.executor.execute(task)
                self.queue.update_status(
                    task.id,
                    TaskStatus.DONE if success else TaskStatus.FAILED,
                    result=output[:5000],
                    error=None if success else "执行失败"
                )

                # 打印flag
                if success:
                    flags = re.findall(r"flag\{[^}]+\}", output, re.IGNORECASE)
                    if flags:
                        print(f"\n[!] 发现 FLAG: {flags}")

            # 检查是否需要AI继续规划
            if self.mode == "AutoRun" and self.network.detect() == "internet":
                new_tasks = self._plan_from_previous_results()
                if new_tasks:
                    print(f"[+] AI生成了 {len(new_tasks)} 个新任务")
                    continue
                else:
                    print("[*] AI未生成新任务，尝试完成")
                    break
            else:
                # 半自动/隔离模式，等确认
                if self.mode == "SemiAuto":
                    print("[*] SemiAuto模式: 按回车继续，下同 q退出")
                    cmd = input("> ").strip()
                    if cmd.lower() in ("q", "quit", "exit"):
                        break

        # 导出结果
        self.export_results()
        self.print_summary()

    def _plan_from_previous_results(self) -> list:
        """基于之前的结果，让AI继续生成任务"""
        done_results = []
        for t in self.queue.get_done()[-5:]:  # 最近5个结果
            if t.result:
                done_results.append({
                    "task": t.description,
                    "result": t.result[:500],
                })

        if not done_results:
            return []

        prompt = f"""基于以下任务执行结果，制定下一步计划:

{json.dumps(done_results, ensure_ascii=False, indent=2)}

如果发现flag，直接输出flag{{...}}
如果需要继续渗透，给出下一步任务JSON数组。
如果没有明确攻击路径，输出 {{"stop": true}}
"""

        response = self.llm.generate(prompt)

        # 检查是否有flag
        flags = re.findall(r"flag\{[^}]+\}", response, re.IGNORECASE)
        if flags:
            print(f"\n[!] 最终FLAG: {flags}")

        if '{"stop": true}' in response or 'stop' in response.lower():
            return []

        tasks = self._parse_tasks_from_response(response)
        if tasks:
            self.queue.add_batch([Task(**t) for t in tasks])
            return tasks
        return []

    def export_results(self):
        """导出所有结果"""
        filepath = self.queue.export_all_results()
        print(f"\n[+] 结果已导出: {filepath}")
        return filepath

    def print_summary(self):
        """打印执行摘要"""
        summary = self.queue.summary()
        done = self.queue.get_done()
        failed = self.queue.get_failed()

        print("\n" + "=" * 50)
        print("  执行摘要")
        print("=" * 50)
        print(f"  总任务:    {summary['total']}")
        print(f"  已完成:    {summary['done']}")
        print(f"  失败:      {summary['failed']}")
        print(f"  待执行:    {summary['pending']}")
        print("-" * 50)

        # 显示完成的任务
        if done:
            print("  已完成:")
            for t in done[-5:]:
                print(f"    ✓ [{t.id}] {t.description[:50]}")

        # 显示失败的
        if failed:
            print("  失败:")
            for t in failed:
                print(f"    ✗ [{t.id}] {t.description[:50]} - {t.error}")

        print("=" * 50)

    # ==================== U盘模式 ====================

    def udisk_export(self, filepath=None):
        """
        U盘模式: 导出扫描结果和任务队列
        拿到互联网机器上分析
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        export_data = {
            "exported_at": timestamp,
            "environment": "intranet_scan",
            "network": self.network.summary(),
            "queue": [t.to_dict() for t in self.queue.tasks],
            "mode": "udisk_export",
        }

        filepath = filepath or f"secbot_udisk_export_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"[+] U盘导出: {filepath}")
        print("[*] 复制此文件到互联网机器，用 SecBot Internet 模式分析")
        return filepath

    def udisk_import(self, filepath: str):
        """
        U盘模式: 导入AI分析后的任务
        把互联网机器上生成的任务导入执行
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # 导入任务
        imported = 0
        for t_data in data.get("tasks", []):
            task = Task.from_dict(t_data)
            task.status = TaskStatus.PENDING
            self.queue.tasks.append(task)
            imported += 1

        self.queue._save()
        print(f"[+] 已导入 {imported} 个任务")
        print(f"[*] 开始执行...")
        self.run_tasks()

    # ==================== 手动任务 ====================

    def add_task(self, task_type: str, description: str, command: str,
                 target: str = None, tags: list = None):
        """手动添加任务"""
        task = Task(
            task_type=task_type,
            description=description,
            command=command,
            target=target,
            tags=tags or [],
        )
        task_id = self.queue.add(task)
        print(f"[+] 任务已添加: [{task_id}] {description}")
        return task_id

    def add_ctf_task(self, description: str, task_content: str):
        """添加CTF解题任务"""
        prompt = f"""请帮我分析这道CTF题目，给出解题步骤和最终flag。

题目: {description}
内容: {task_content}

输出格式:
## 分析
## 步骤
## flag
flag{{...}}
"""
        return self.add_task("analyze", description, f"echo '{prompt}'", tags=["ctf"])

    def list_tasks(self):
        """列出所有任务"""
        print("\n任务队列:")
        print("-" * 60)
        for t in self.queue.tasks:
            status_icon = {
                "pending": "○", "running": "◐", "done": "✓", "failed": "✗"
            }.get(t.status.value, "?")
            print(f"  {status_icon} [{t.id}] {t.type:8} {t.description[:40]}")
        print("-" * 60)
