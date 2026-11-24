from typing import Callable, Optional
import customtkinter as ctk
from src.core.models import DownloadTask, TaskStatus
from src.ui.theme import COLORS, FONTS


class TaskRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        task: DownloadTask,
        on_delete: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )
        self.task_id = task.task_id
        self._on_delete = on_delete
        self.grid_columnconfigure(0, weight=1)

        # Hàng trên: Tiêu đề video + Nhãn trạng thái + Nút xóa
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        top_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            top_frame,
            text=task.title or task.url,
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.status_badge = ctk.CTkLabel(
            top_frame,
            text="ĐANG CHỜ",
            font=FONTS["small"],
            text_color=COLORS["warning"],
            fg_color="#2D2618",
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.status_badge.grid(row=0, column=1, sticky="e")

        if self._on_delete:
            self.delete_btn = ctk.CTkButton(
                top_frame,
                text="✕",
                width=26,
                height=24,
                corner_radius=6,
                font=FONTS["small"],
                fg_color="transparent",
                hover_color="#331B1E",
                text_color=COLORS["text_muted"],
                command=lambda: self._on_delete(self.task_id),
            )
            self.delete_btn.grid(row=0, column=2, sticky="e", padx=(6, 0))

        # Hàng giữa: Thanh tiến trình
        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=8,
            corner_radius=4,
            fg_color=COLORS["bg_input"],
            progress_color=COLORS["primary"],
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=14, pady=4)

        # Hàng dưới: Thông số chi tiết (%, tốc độ, thời gian còn lại / đường dẫn)
        self.detail_label = ctk.CTkLabel(
            self,
            text=f"Chất lượng: {task.resolution} | Đang chờ trong hàng đợi...",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self.detail_label.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 10))

        self.update_state(task)

    def update_state(self, task: DownloadTask) -> None:
        self.title_label.configure(text=task.title or task.url)
        self.progress_bar.set(max(0.0, min(1.0, task.progress / 100.0)))

        if task.status == TaskStatus.PENDING:
            self.status_badge.configure(
                text="ĐANG CHỜ", text_color=COLORS["warning"], fg_color="#2D2618"
            )
            self.detail_label.configure(
                text=f"[{task.task_id}] Chất lượng: {task.resolution} • Đang chờ luồng trống..."
            )

        elif task.status == TaskStatus.DOWNLOADING:
            retry_str = f" (Thử lại #{task.retries})" if task.retries > 0 else ""
            self.status_badge.configure(
                text=f"ĐANG TẢI{retry_str}",
                text_color=COLORS["primary"],
                fg_color="#192841",
            )
            self.progress_bar.configure(progress_color=COLORS["primary"])
            self.detail_label.configure(
                text=(
                    f"[{task.task_id}] {task.progress:.1f}%  •  "
                    f"Tốc độ: {task.speed_text or 'N/A'}  •  "
                    f"Còn lại: {task.eta_text or 'N/A'}"
                )
            )

        elif task.status == TaskStatus.COMPLETED:
            self.status_badge.configure(
                text="HOÀN TẤT", text_color=COLORS["success"], fg_color="#142E25"
            )
            self.progress_bar.configure(progress_color=COLORS["success"])
            self.detail_label.configure(
                text=f"[{task.task_id}] Đã lưu tại: {task.saved_path}",
                text_color=COLORS["success"],
            )

        elif task.status == TaskStatus.FAILED:
            self.status_badge.configure(
                text="LỖI", text_color=COLORS["danger"], fg_color="#331B1E"
            )
            self.progress_bar.configure(progress_color=COLORS["danger"])
            self.detail_label.configure(
                text=f"[{task.task_id}] Thất bại: {task.error}",
                text_color=COLORS["danger"],
            )