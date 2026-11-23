from pathlib import Path
from tkinter import filedialog
from typing import Dict
import customtkinter as ctk

from src.core.models import DownloadTask
from src.services.manager import DownloadManager
from src.ui.components.task_row import TaskRow
from src.ui.theme import COLORS, FONTS


class InstagramView(ctk.CTkFrame):
    def __init__(self, master, manager: DownloadManager, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._manager = manager
        self._output_dir = str(Path("downloads").resolve())
        self._task_rows: Dict[str, TaskRow] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        ctk.CTkLabel(
            header,
            text="Instagram Downloader",
            font=FONTS["h1"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Dán đường dẫn Reels hoặc Video công khai trên Instagram (mỗi dòng 1 link).",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(2, 0))

        # 2. Khung nhập URL & Chọn định dạng
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
            height=86,
            fg_color=COLORS["bg_input"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
            corner_radius=8,
        )
        self.url_textbox.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 10))

        action_bar = ctk.CTkFrame(input_card, fg_color="transparent")
        action_bar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        action_bar.grid_columnconfigure(1, weight=1)

        self.format_menu = ctk.CTkOptionMenu(
            action_bar,
            values=["Video (MP4)", "MP3 (Audio)"],
            width=130,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["primary"],
            font=FONTS["small"],
        )
        self.format_menu.set("Video (MP4)")
        self.format_menu.grid(row=0, column=0, padx=(0, 10))

        self.dir_btn = ctk.CTkButton(
            action_bar,
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
        self.dir_btn.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            action_bar,
            text="Xóa ô nhập",
            width=95,
            height=34,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["bg_card_hover"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            font=FONTS["small"],
            command=lambda: self.url_textbox.delete("1.0", "end"),
        ).grid(row=0, column=2, padx=(0, 10))

        self.download_btn = ctk.CTkButton(
            action_bar,
            text="Tải xuống",
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=34,
            width=140,
            command=self._submit_urls,
        )
        self.download_btn.grid(row=0, column=3, sticky="e")

        # 3. Khu vực hàng đợi tải
        self.queue_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_input"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.queue_scroll.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 20))
        self.queue_scroll.grid_columnconfigure(0, weight=1)

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
        if not urls:
            return

        selected_format = self.format_menu.get()
        for url in urls:
            self._manager.add_task(
                url=url,
                output_dir=self._output_dir,
                resolution=selected_format,
                source="instagram",
            )

        self.url_textbox.delete("1.0", "end")

    def render_task_update(self, task: DownloadTask) -> None:
        if task.task_id not in self._task_rows:
            row_idx = len(self._task_rows)
            row = TaskRow(self.queue_scroll, task)
            row.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=6)
            self._task_rows[task.task_id] = row
        else:
            self._task_rows[task.task_id].update_state(task)