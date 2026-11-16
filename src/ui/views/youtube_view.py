from pathlib import Path
from tkinter import filedialog
from typing import Dict
import customtkinter as ctk

from src.core.models import DownloadTask
from src.services.manager import DownloadManager
from src.ui.components.task_row import TaskRow
from src.ui.theme import COLORS, FONTS


class YouTubeView(ctk.CTkFrame):
    def __init__(self, master, manager: DownloadManager, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._manager = manager
        self._output_dir = str(Path("downloads").resolve())
        self._task_rows: Dict[str, TaskRow] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Tiêu đề màn hình
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        ctk.CTkLabel(
            header,
            text="YouTube Video Downloader",
            font=FONTS["h1"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Dán một hoặc nhiều đường link YouTube (mỗi link một dòng) để đưa vào hàng đợi tải đa luồng.",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(2, 0))

        # 2. Khung nhập liệu & Tùy chọn
        input_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        input_card.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        input_card.grid_columnconfigure(0, weight=1)

        self.url_textbox = ctk.CTkTextbox(
            input_card,
            height=90,
            fg_color=COLORS["bg_input"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
            corner_radius=8,
        )
        self.url_textbox.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))

        # Thanh công cụ dưới ô nhập
        controls = ctk.CTkFrame(input_card, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        controls.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            controls, text="Độ phân giải:", font=FONTS["body"], text_color=COLORS["text_secondary"]
        ).grid(row=0, column=0, padx=(0, 8))

        self.res_menu = ctk.CTkOptionMenu(
            controls,
            values=["1080p", "720p", "480p", "best"],
            width=105,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["primary"],
            font=FONTS["body"],
        )
        self.res_menu.set("1080p")
        self.res_menu.grid(row=0, column=1, padx=(0, 14))

        self.dir_btn = ctk.CTkButton(
            controls,
            text=f"Lưu tại: .../{Path(self._output_dir).name}",
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["bg_card_hover"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            font=FONTS["small"],
            anchor="w",
            command=self._choose_directory,
        )
        self.dir_btn.grid(row=0, column=2, sticky="ew", padx=(0, 14))

        self.download_btn = ctk.CTkButton(
            controls,
            text="Thêm vào hàng đợi tải",
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=36,
            width=180,
            command=self._submit_urls,
        )
        self.download_btn.grid(row=0, column=3, sticky="e")

        # 3. Khu vực danh sách tiến độ tải
        queue_header = ctk.CTkFrame(self, fg_color="transparent")
        queue_header.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 20))
        queue_header.grid_columnconfigure(0, weight=1)
        queue_header.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            queue_header,
            text="Tiến độ hàng đợi (Tối đa 3 luồng song song)",
            font=FONTS["h2"],
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.queue_scroll = ctk.CTkScrollableFrame(
            queue_header,
            fg_color=COLORS["bg_input"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.queue_scroll.grid(row=1, column=0, sticky="nsew")
        self.queue_scroll.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.queue_scroll,
            text="Chưa có video nào trong hàng đợi. Hãy dán link YouTube ở phía trên để bắt đầu.",
            font=FONTS["body"],
            text_color=COLORS["text_muted"],
        )
        self.empty_label.grid(row=0, column=0, pady=40)

    def _choose_directory(self) -> None:
        selected = filedialog.askdirectory(initialdir=self._output_dir)
        if selected:
            self._output_dir = selected
            self.dir_btn.configure(text=f"Lưu tại: .../{Path(selected).name}")

    def _submit_urls(self) -> None:
        raw_text = self.url_textbox.get("1.0", "end").strip()
        if not raw_text:
            return

        urls = [line.strip() for line in raw_text.splitlines() if line.strip()]
        resolution = self.res_menu.get()

        for url in urls:
            self._manager.add_task(
                url=url,
                output_dir=self._output_dir,
                resolution=resolution,
            )

        self.url_textbox.delete("1.0", "end")

    def render_task_update(self, task: DownloadTask) -> None:
        """Hàm này luôn được gọi trên Main UI Thread."""
        if self.empty_label.winfo_exists():
            self.empty_label.destroy()

        if task.task_id not in self._task_rows:
            row_idx = len(self._task_rows)
            row = TaskRow(self.queue_scroll, task)
            row.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=6)
            self._task_rows[task.task_id] = row
        else:
            self._task_rows[task.task_id].update_state(task)