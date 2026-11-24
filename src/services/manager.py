from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from queue import Queue
import threading
import time
from typing import Callable, Dict, List, Optional, Set

from src.core.factory import DownloaderFactory
from src.core.models import DownloadProgress, DownloadTask, TaskStatus

TaskCallback = Callable[[DownloadTask], None]


class _TaskCancelled(Exception):
    """Ngoại lệ nội bộ để ngắt luồng tải khi tác vụ bị xóa khỏi hàng đợi."""


class DownloadManager:
    def __init__(
        self,
        factory: DownloaderFactory,
        max_workers: int = 3,
        max_retries: int = 2,
        on_task_update: Optional[TaskCallback] = None,
    ) -> None:
        self._factory = factory
        self._max_workers = max_workers
        self._max_retries = max_retries
        self._on_task_update = on_task_update

        self._queue: Queue[Optional[DownloadTask]] = Queue()
        self._tasks: Dict[str, DownloadTask] = {}
        self._removed_ids: Set[str] = set()
        self._task_seq = 0
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        for _ in range(max_workers):
            self._executor.submit(self._worker_loop)

    def add_task(
        self,
        url: str,
        output_dir: str = "downloads",
        resolution: str = "1080p",
        source: str = "youtube",
        title: Optional[str] = None,
    ) -> DownloadTask:
        """Đưa một URL mới vào hàng đợi tải (Producer)."""
        with self._lock:
            self._task_seq += 1
            task_id = f"Task-{self._task_seq}"
            task = DownloadTask(
                task_id=task_id,
                url=url.strip(),
                output_dir=output_dir,
                resolution=resolution,
                source=source,
                title=title,
            )
            self._tasks[task_id] = task

        self._queue.put(task)
        self._notify(task)
        return task

    def has_task(self, task_id: str) -> bool:
        """Kiểm tra tác vụ còn tồn tại trong hàng đợi hay đã bị xóa."""
        with self._lock:
            return task_id in self._tasks

    def remove_task(self, task_id: str) -> None:
        """Xóa 1 tác vụ khỏi hàng đợi (hủy luôn nếu đang chờ hoặc đang tải)."""
        removed_snapshot: Optional[DownloadTask] = None
        with self._lock:
            task = self._tasks.pop(task_id, None)
            self._removed_ids.add(task_id)
            if task is not None:
                removed_snapshot = replace(task)

        if removed_snapshot and self._on_task_update:
            self._on_task_update(removed_snapshot)

    def clear_tasks(self, source: Optional[str] = None) -> None:
        """Xóa toàn bộ tác vụ (hoặc chỉ các tác vụ thuộc một nền tảng/source)."""
        removed_snapshots: List[DownloadTask] = []
        with self._lock:
            target_ids = [
                tid
                for tid, task in self._tasks.items()
                if source is None or task.source == source
            ]
            for tid in target_ids:
                task = self._tasks.pop(tid, None)
                self._removed_ids.add(tid)
                if task is not None:
                    removed_snapshots.append(replace(task))

        if removed_snapshots and self._on_task_update:
            self._on_task_update(removed_snapshots[0])

    def get_all_tasks(self) -> List[DownloadTask]:
        """Trả về bản chụp an toàn trạng thái của toàn bộ tác vụ."""
        with self._lock:
            return [replace(t) for t in self._tasks.values()]

    def wait_all(self) -> None:
        """Chờ cho đến khi toàn bộ tác vụ trong hàng đợi hoàn tất."""
        self._queue.join()

    def shutdown(self) -> None:
        """Gửi tín hiệu dừng (Sentinel) và giải phóng ThreadPool."""
        for _ in range(self._max_workers):
            self._queue.put(None)
        self._executor.shutdown(wait=True)

    def _is_removed(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._removed_ids

    def _worker_loop(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                self._queue.task_done()
                break

            try:
                if not self._is_removed(task.task_id):
                    self._process_task(task)
            finally:
                self._queue.task_done()

    def _process_task(self, task: DownloadTask) -> None:
        if self._is_removed(task.task_id):
            return

        try:
            downloader = self._factory.create(task.url)
        except ValueError as e:
            self._update_task(task, status=TaskStatus.FAILED, error=str(e))
            return

        if not task.title:
            try:
                meta = downloader.get_info(task.url)
                if self._is_removed(task.task_id):
                    return
                self._update_task(task, title=meta.title)
            except Exception:
                pass

        last_error = ""
        for attempt in range(self._max_retries + 1):
            if self._is_removed(task.task_id):
                return

            self._update_task(
                task,
                status=TaskStatus.DOWNLOADING,
                retries=attempt,
                progress=0.0,
            )

            def handle_progress(prog: DownloadProgress) -> None:
                if self._is_removed(task.task_id):
                    raise _TaskCancelled()
                self._update_task(
                    task,
                    progress=prog.percent,
                    speed_text=prog.speed_text,
                    eta_text=prog.eta_text,
                )

            try:
                saved_path = downloader.download(
                    url=task.url,
                    output_dir=task.output_dir,
                    resolution=task.resolution,
                    on_progress=handle_progress,
                )
                self._update_task(
                    task,
                    status=TaskStatus.COMPLETED,
                    progress=100.0,
                    saved_path=saved_path,
                    error=None,
                )
                return
            except _TaskCancelled:
                return
            except Exception as e:
                if self._is_removed(task.task_id):
                    return
                last_error = str(e)
                if attempt < self._max_retries:
                    time.sleep(2 * (attempt + 1))

        self._update_task(task, status=TaskStatus.FAILED, error=last_error)

    def _update_task(self, task: DownloadTask, **changes) -> None:
        with self._lock:
            if task.task_id in self._removed_ids:
                return
            for key, value in changes.items():
                setattr(task, key, value)
            snapshot = replace(task)

        if self._on_task_update:
            self._on_task_update(snapshot)

    def _notify(self, task: DownloadTask) -> None:
        if self._on_task_update:
            with self._lock:
                if task.task_id in self._removed_ids:
                    return
                snapshot = replace(task)
            self._on_task_update(snapshot)