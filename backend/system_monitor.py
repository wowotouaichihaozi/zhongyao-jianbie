from __future__ import annotations

import ctypes
import json
import logging
import os
import shutil
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SystemMonitor:
    """Collect a small, read-only runtime snapshot without exposing secrets."""

    def __init__(self, project_root: Path, interval_seconds: int = 30) -> None:
        self.project_root = Path(project_root).resolve()
        self.interval_seconds = max(10, int(interval_seconds))
        self.log_dir = self.project_root / "logs"
        self.log_path = self.log_dir / "system-monitor.jsonl"
        self._start_lock = threading.Lock()
        self._started = False
        self._logger: logging.Logger | None = None

    def start(self) -> None:
        with self._start_lock:
            if self._started:
                return
            self._started = True
            thread = threading.Thread(target=self._collector_loop, name="system-monitor", daemon=True)
            thread.start()

    def snapshot(self) -> dict:
        cpu_percent = self._cpu_percent()
        memory = self._memory_snapshot()
        disk = shutil.disk_usage(self.project_root)
        processes = self._project_processes()
        try:
            load = [round(value, 2) for value in os.getloadavg()]
        except (AttributeError, OSError):
            load = []

        resources = {
            "cpuPercent": cpu_percent,
            "cpuCount": os.cpu_count() or 1,
            "loadAverage": load,
            "memoryPercent": memory["percent"],
            "memoryUsedBytes": memory["used"],
            "memoryTotalBytes": memory["total"],
            "diskPercent": round((disk.used / disk.total) * 100, 1) if disk.total else 0.0,
            "diskUsedBytes": int(disk.used),
            "diskTotalBytes": int(disk.total),
            "uptimeSeconds": self._uptime_seconds(),
        }
        severity = self._severity(resources)
        return {
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "severity": severity,
            "platform": sys.platform,
            "resources": resources,
            "services": self._service_statuses(processes),
            "processes": processes,
        }

    def snapshot_and_record(self) -> dict:
        snapshot = self.snapshot()
        self._monitor_logger().info(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
        return snapshot

    def recent(self, limit: int = 120) -> list[dict]:
        limit = min(500, max(1, int(limit)))
        if not self.log_path.exists():
            return []
        try:
            with self.log_path.open("rb") as stream:
                stream.seek(0, os.SEEK_END)
                size = stream.tell()
                stream.seek(max(0, size - 768 * 1024))
                raw = stream.read().decode("utf-8", errors="ignore")
        except OSError:
            return []
        records = []
        for line in raw.splitlines()[-limit:]:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records

    def _collector_loop(self) -> None:
        while True:
            try:
                self.snapshot_and_record()
            except Exception:
                # Monitoring must never affect the application request path.
                pass
            time.sleep(self.interval_seconds)

    def _monitor_logger(self) -> logging.Logger:
        if self._logger is not None:
            return self._logger
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(f"qzxh.system-monitor.{self.log_path}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not logger.handlers:
            handler = RotatingFileHandler(
                self.log_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
        self._logger = logger
        return logger

    @staticmethod
    def _read_cpu_times() -> tuple[int, int] | None:
        if sys.platform.startswith("linux"):
            try:
                values = [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
                idle = values[3] + (values[4] if len(values) > 4 else 0)
                return idle, sum(values)
            except (OSError, ValueError, IndexError):
                return None
        if sys.platform == "win32":
            idle = ctypes.c_ulonglong()
            kernel = ctypes.c_ulonglong()
            user = ctypes.c_ulonglong()
            if ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
            ):
                return idle.value, kernel.value + user.value
        return None

    def _cpu_percent(self) -> float | None:
        first = self._read_cpu_times()
        if first is None:
            return None
        time.sleep(0.08)
        second = self._read_cpu_times()
        if second is None:
            return None
        idle_delta = second[0] - first[0]
        total_delta = second[1] - first[1]
        if total_delta <= 0:
            return 0.0
        return round(max(0.0, min(100.0, (1 - idle_delta / total_delta) * 100)), 1)

    @staticmethod
    def _memory_snapshot() -> dict:
        if sys.platform.startswith("linux"):
            try:
                values = {}
                for line in Path("/proc/meminfo").read_text().splitlines():
                    key, raw = line.split(":", 1)
                    values[key] = int(raw.strip().split()[0]) * 1024
                total = values.get("MemTotal", 0)
                available = values.get("MemAvailable", values.get("MemFree", 0))
                used = max(0, total - available)
                return {"total": total, "used": used, "percent": round(used / total * 100, 1) if total else 0.0}
            except (OSError, ValueError):
                pass
        if sys.platform == "win32":
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memoryLoad", ctypes.c_ulong),
                    ("totalPhys", ctypes.c_ulonglong),
                    ("availPhys", ctypes.c_ulonglong),
                    ("totalPageFile", ctypes.c_ulonglong),
                    ("availPageFile", ctypes.c_ulonglong),
                    ("totalVirtual", ctypes.c_ulonglong),
                    ("availVirtual", ctypes.c_ulonglong),
                    ("availExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return {
                    "total": int(status.totalPhys),
                    "used": int(status.totalPhys - status.availPhys),
                    "percent": float(status.memoryLoad),
                }
        return {"total": 0, "used": 0, "percent": 0.0}

    @staticmethod
    def _uptime_seconds() -> int | None:
        if sys.platform.startswith("linux"):
            try:
                return int(float(Path("/proc/uptime").read_text().split()[0]))
            except (OSError, ValueError, IndexError):
                return None
        if sys.platform == "win32":
            return int(ctypes.windll.kernel32.GetTickCount64() / 1000)
        return None

    def _project_processes(self) -> list[dict]:
        if not sys.platform.startswith("linux"):
            return [{"pid": os.getpid(), "name": "中药鉴别后端", "memoryMb": None, "state": "running"}]
        keywords = ("feishengwangying", "gunicorn", "uvicorn", "nginx", "vite", "npm run build")
        rows = []
        for proc_dir in Path("/proc").iterdir():
            if not proc_dir.name.isdigit():
                continue
            try:
                command = (proc_dir / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", errors="ignore")
                if not command or not any(keyword in command.lower() for keyword in keywords):
                    continue
                status = (proc_dir / "status").read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            memory_kb = 0
            state = "running"
            for line in status.splitlines():
                if line.startswith("VmRSS:"):
                    memory_kb = int(line.split()[1])
                elif line.startswith("State:"):
                    state = line.split(":", 1)[1].strip()[:40]
            rows.append(
                {
                    "pid": int(proc_dir.name),
                    "name": self._safe_process_name(command),
                    "memoryMb": round(memory_kb / 1024, 1),
                    "state": state,
                }
            )
        return sorted(rows, key=lambda item: (-(item["memoryMb"] or 0), item["pid"]))[:24]

    @staticmethod
    def _safe_process_name(command: str) -> str:
        lowered = command.lower()
        if "nginx" in lowered:
            return "Nginx"
        if "uvicorn" in lowered or "8765" in lowered:
            return "PPT API"
        if "gunicorn" in lowered:
            return "中药鉴别后端"
        if "vite build" in lowered or "npm run build" in lowered:
            return "前端构建"
        if "vite" in lowered:
            return "前端开发服务"
        return "项目进程"

    def _service_statuses(self, processes: list[dict]) -> list[dict]:
        names = {str(item.get("name")) for item in processes}
        return [
            {"name": "学习平台后端", "status": "online", "detail": "当前监控接口可响应"},
            {
                "name": "学习平台前端",
                "status": "online" if (self.project_root / "frontend" / "dist" / "index.html").exists() else "offline",
                "detail": "生产构建产物",
            },
            {
                "name": "超级管理员端",
                "status": "online" if (self.project_root / "admin" / "dist" / "index.html").exists() else "offline",
                "detail": "管理端生产构建",
            },
            {
                "name": "PPT API",
                "status": "online" if self._port_open(8765) else "offline",
                "detail": "127.0.0.1:8765",
            },
            {
                "name": "Nginx",
                "status": "online" if "Nginx" in names else ("not_applicable" if sys.platform == "win32" else "offline"),
                "detail": "公网静态资源与反向代理",
            },
        ]

    @staticmethod
    def _port_open(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            return False

    @staticmethod
    def _severity(resources: dict) -> str:
        values = [resources.get("cpuPercent"), resources.get("memoryPercent"), resources.get("diskPercent")]
        numeric = [float(value) for value in values if value is not None]
        if any(value >= 95 for value in numeric):
            return "critical"
        if any(value >= 85 for value in numeric):
            return "warning"
        return "healthy"
