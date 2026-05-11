"""
SecBot 核心 - 任务队列
持久化存储，支持 Internet/内网分离运行
"""

import json
import os
import datetime
import uuid
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 执行中
    DONE = "done"             # 已完成
    FAILED = "failed"         # 失败
    BLOCKED = "blocked"       # 等待前置任务


class Task:
    """安全任务"""

    def __init__(self, task_type, description, command=None, target=None,
                 depends_on=None, priority=5, tags=None):
        self.id = str(uuid.uuid4())[:8]
        self.type = task_type      # scan/ exploit/ recon/ analyze/ custom
        self.description = description
        self.command = command      # 待执行的shell命令
        self.target = target        # 目标IP/URL
        self.depends_on = depends_on or []  # 依赖的task id列表
        self.priority = priority    # 1-10, 越大越优先
        self.tags = tags or []
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.datetime.now().isoformat()
        self.started_at = None
        self.finished_at = None
        self.attempts = 0
        self.max_attempts = 3

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "command": self.command,
            "target": self.target,
            "depends_on": self.depends_on,
            "priority": self.priority,
            "tags": self.tags,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
        }

    @classmethod
    def from_dict(cls, d):
        t = cls(
            task_type=d["type"],
            description=d["description"],
            command=d.get("command"),
            target=d.get("target"),
            depends_on=d.get("depends_on"),
            priority=d.get("priority", 5),
            tags=d.get("tags", []),
        )
        t.id = d.get("id", t.id)
        t.status = TaskStatus(d.get("status", "pending"))
        t.result = d.get("result")
        t.error = d.get("error")
        t.created_at = d.get("created_at", t.created_at)
        t.started_at = d.get("started_at")
        t.finished_at = d.get("finished_at")
        t.attempts = d.get("attempts", 0)
        t.max_attempts = d.get("max_attempts", 3)
        return t


class TaskQueue:
    """
    持久化任务队列
    所有数据存JSON文件，支持：
    - 内网扫描仪导出结果 → 复制到互联网机器处理
    - 互联网AI规划任务 → 导出任务JSON → 拿回内网执行
    """

    def __init__(self, queue_dir=None):
        self.queue_dir = queue_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tasks"
        )
        os.makedirs(self.queue_dir, exist_ok=True)
        self.tasks_file = os.path.join(self.queue_dir, "queue.json")
        self.results_dir = os.path.join(self.queue_dir, "results")
        os.makedirs(self.results_dir, exist_ok=True)
        self.tasks = self._load()

    def _load(self):
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, encoding="utf-8") as f:
                    data = json.load(f)
                return [Task.from_dict(t) for t in data]
            except Exception:
                return []
        return []

    def _save(self):
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=2)

    # -------------------- CRUD --------------------

    def add(self, task: Task) -> str:
        """添加任务，返回task id"""
        self.tasks.append(task)
        self._save()
        return task.id

    def add_batch(self, tasks):
        """批量添加"""
        for t in tasks:
            self.tasks.append(t)
        self._save()
        return [t.id for t in tasks]

    def get(self, task_id: str) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def get_pending(self) -> list:
        """获取所有待执行任务（按优先级排序）"""
        pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]
        # 检查依赖
        ready = []
        for t in pending:
            deps_done = all(
                self.get(did).status == TaskStatus.DONE
                for did in t.depends_on
                if self.get(did)
            )
            if deps_done or not t.depends_on:
                ready.append(t)
        return sorted(ready, key=lambda x: -x.priority)

    def get_running(self) -> list:
        return [t for t in self.tasks if t.status == TaskStatus.RUNNING]

    def get_done(self) -> list:
        return [t for t in self.tasks if t.status == TaskStatus.DONE]

    def get_failed(self) -> list:
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]

    def update_status(self, task_id: str, status: TaskStatus,
                      result=None, error=None):
        """更新任务状态"""
        t = self.get(task_id)
        if not t:
            return
        t.status = status
        if status == TaskStatus.RUNNING:
            t.started_at = datetime.datetime.now().isoformat()
            t.attempts += 1
        if status in (TaskStatus.DONE, TaskStatus.FAILED):
            t.finished_at = datetime.datetime.now().isoformat()
            t.result = result
            t.error = error
        self._save()

    def remove(self, task_id: str):
        self.tasks = [t for t in self.tasks if t.id != task_id]
        self._save()

    def clear_done(self):
        """清理已完成任务"""
        self.tasks = [t for t in self.tasks if t.status not in (TaskStatus.DONE, TaskStatus.FAILED)]
        self._save()

    # -------------------- 导入导出（U盘模式核心）--------------------

    def export_tasks(self, filepath=None, status_filter=None):
        """
        导出任务到文件（用于内网→互联网数据传递）
        status_filter: 只导出特定状态的任务
        """
        tasks = self.tasks
        if status_filter:
            tasks = [t for t in tasks if t.status.value in status_filter]

        export_data = {
            "exported_at": datetime.datetime.now().isoformat(),
            "total": len(tasks),
            "tasks": [t.to_dict() for t in tasks],
        }
        filepath = filepath or os.path.join(
            self.queue_dir,
            f"tasks_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        return filepath

    def import_tasks(self, filepath) -> int:
        """
        从文件导入任务（用于互联网→内网数据传递）
        返回导入数量
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        imported = 0
        for t_data in data.get("tasks", []):
            # 避免重复ID
            if self.get(t_data["id"]):
                continue
            task = Task.from_dict(t_data)
            # 重置状态为pending（重新执行）
            if task.status == TaskStatus.DONE:
                task.status = TaskStatus.PENDING
                task.result = None
            self.tasks.append(task)
            imported += 1

        self._save()
        return imported

    def export_results(self, task_id: str, result_filepath=None):
        """导出单个任务结果到文件"""
        t = self.get(task_id)
        if not t:
            return None

        result_data = {
            "task_id": t.id,
            "type": t.type,
            "description": t.description,
            "target": t.target,
            "status": t.status.value,
            "result": t.result,
            "error": t.error,
            "finished_at": t.finished_at,
        }
        result_filepath = result_filepath or os.path.join(
            self.results_dir, f"result_{t.id}.json"
        )
        with open(result_filepath, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        return result_filepath

    def export_all_results(self) -> str:
        """导出所有结果（供AI分析）"""
        done = self.get_done()
        failed = self.get_failed()
        all_tasks = done + failed

        summary = {
            "total_tasks": len(self.tasks),
            "done": len(done),
            "failed": len(failed),
            "pending": len(self.get_pending()),
            "exported_at": datetime.datetime.now().isoformat(),
            "results": []
        }

        for t in all_tasks:
            summary["results"].append({
                "id": t.id,
                "type": t.type,
                "description": t.description,
                "target": t.target,
                "status": t.status.value,
                "result": t.result[:2000] if t.result else None,  # 截断
                "error": t.error,
            })

        filepath = os.path.join(
            self.queue_dir,
            f"all_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return filepath

    # -------------------- 统计 --------------------

    def summary(self) -> dict:
        return {
            "total": len(self.tasks),
            "pending": len([t for t in self.tasks if t.status == TaskStatus.PENDING]),
            "running": len([t for t in self.tasks if t.status == TaskStatus.RUNNING]),
            "done": len([t for t in self.tasks if t.status == TaskStatus.DONE]),
            "failed": len([t for t in self.tasks if t.status == TaskStatus.FAILED]),
        }

    def __repr__(self):
        s = self.summary()
        return (f"TaskQueue(total={s['total']}, pending={s['pending']}, "
                f"done={s['done']}, failed={s['failed']})")
