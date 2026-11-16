from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from queue import Queue
import threading
import time
from typing import Callable, Dict, List, Optional

from src.core.factory import DownloaderFactory
from src.core.models import DownloadProgress, DownloadTask, TaskStatus

TaskCallback = Callable[[DownloadTask], None]


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
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # Khởi chạy sẵn các luồng Consumer chờ lấy việc từ Queue
        for _ in range(max_workers):
            self._executor.submit(self._worker_loop)

    def add_task(
        self,
        url: str,
        output_dir: str = "downloads",
        resolution: str = "1080p",
    ) -> DownloadTask:
        """Đưa một URL mới vào hàng đợi tải (Producer)."""
        with self._lock:
            task_id = f"Task-{len(self._tasks) + 1}"
            task = DownloadTask(
                task_id=task_id,
                url=url.strip(),
                output_dir=output_dir,
                resolution=resolution,
            )
            self._tasks[task_id] = task

        self._queue.put(task)
        self._notify(task)
        return task

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

    def _worker_loop(self) -> None:
        """Vòng lặp chạy trên từng luồng nền để rút tác vụ từ Queue."""
        while True:
            task = self._queue.get()
            if task is None:
                self._queue.task_done()
                break

            try:
                self._process_task(task)
            finally:
                self._queue.task_done()

    def _process_task(self, task: DownloadTask) -> None:
        # 1. Chọn đúng Provider qua Factory (lỗi URL không hợp lệ thì không retry)
        try:
            downloader = self._factory.create(task.url)
        except ValueError as e:
            self._update_task(task, status=TaskStatus.FAILED, error=str(e))
            return

        # 2. Thử lấy tiêu đề video trước để hiển thị cho thân thiện
        try:
            meta = downloader.get_info(task.url)
            self._update_task(task, title=meta.title)
        except Exception:
            pass

        # 3. Thực thi tải kèm cơ chế tự động thử lại (Retry)
        last_error = ""
        for attempt in range(self._max_retries + 1):
            self._update_task(
                task,
                status=TaskStatus.DOWNLOADING,
                retries=attempt,
                progress=0.0,
            )

            def handle_progress(prog: DownloadProgress) -> None:
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
            except Exception as e:
                last_error = str(e)
                if attempt < self._max_retries:
                    time.sleep(2 * (attempt + 1))

        self._update_task(task, status=TaskStatus.FAILED, error=last_error)

    def _update_task(self, task: DownloadTask, **changes) -> None:
        """Cập nhật thuộc tính tác vụ dưới sự bảo vệ của Lock và báo lên UI."""
        with self._lock:
            for key, value in changes.items():
                setattr(task, key, value)
            snapshot = replace(task)

        if self._on_task_update:
            self._on_task_update(snapshot)

    def _notify(self, task: DownloadTask) -> None:
        if self._on_task_update:
            with self._lock:
                snapshot = replace(task)
            self._on_task_update(snapshot)