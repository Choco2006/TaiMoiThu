from pathlib import Path
import re
import threading
from tkinter import filedialog
from typing import Dict, List, Optional, Tuple
import customtkinter as ctk

from src.core.models import DownloadTask, PlaylistItem, PlaylistMetadata
from src.core.providers.tiktok import TikTokDownloader
from src.services.manager import DownloadManager
from src.ui.components.task_row import TaskRow
from src.ui.theme import COLORS, FONTS


def _sanitize_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name).strip(". ")
    return cleaned or "TikTok_Profile"


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "--:--"
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}:{mins:02d}:{secs:02d}" if hours else f"{mins:02d}:{secs:02d}"


class TikTokProfileView(ctk.CTkFrame):
    _LIMIT_MAP = {
        "20 mới nhất": 20,
        "50 mới nhất": 50,
        "100 mới nhất": 100,
        "Tất cả video": None,
    }

    def __init__(self, master, manager: DownloadManager, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._manager = manager
        self._extractor = TikTokDownloader()
        self._output_dir = str(Path("downloads").resolve())

        self._current_profile: Optional[PlaylistMetadata] = None
        self._item_vars: List[Tuple[PlaylistItem, ctk.BooleanVar]] = []
        self._task_rows: Dict[str, TaskRow] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        ctk.CTkLabel(
            header,
            text="TikTok Profile Downloader",
            font=FONTS["h1"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Dán đường dẫn trang cá nhân TikTok (hoặc nhập @username) để quét và tải hàng loạt Video hoặc MP3.",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(2, 0))

        # 2. Thanh nhập link tài khoản + Giới hạn số lượng
        fetch_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        fetch_card.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 12))
        fetch_card.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            fetch_card,
            placeholder_text="https://www.tiktok.com/@username hoặc @username",
            height=38,
            fg_color=COLORS["bg_input"],
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=14)

        self.limit_menu = ctk.CTkOptionMenu(
            fetch_card,
            values=list(self._LIMIT_MAP.keys()),
            width=130,
            height=38,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["primary"],
            font=FONTS["small"],
        )
        self.limit_menu.set("50 mới nhất")
        self.limit_menu.grid(row=0, column=1, padx=(0, 8), pady=14)

        self.fetch_btn = ctk.CTkButton(
            fetch_card,
            text="Quét Tài Khoản",
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=38,
            width=145,
            command=self._start_fetch_profile,
        )
        self.fetch_btn.grid(row=0, column=2, padx=(0, 14), pady=14)

        self.status_banner = ctk.CTkLabel(
            fetch_card,
            text="",
            font=FONTS["small"],
            text_color=COLORS["warning"],
            anchor="w",
        )

        # 3. Danh sách video của tài khoản
        select_section = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        select_section.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 12))
        select_section.grid_columnconfigure(0, weight=1)
        select_section.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(select_section, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
        toolbar.grid_columnconfigure(0, weight=1)

        self.profile_title_label = ctk.CTkLabel(
            toolbar,
            text="Danh sách video từ tài khoản (0 mục)",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self.profile_title_label.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            toolbar,
            text="Chọn tất cả",
            width=95,
            height=28,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["bg_card_hover"],
            font=FONTS["small"],
            command=lambda: self._toggle_all(True),
        ).grid(row=0, column=1, padx=4)

        ctk.CTkButton(
            toolbar,
            text="Bỏ chọn",
            width=80,
            height=28,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["bg_card_hover"],
            font=FONTS["small"],
            command=lambda: self._toggle_all(False),
        ).grid(row=0, column=2, padx=(4, 0))

        self.items_scroll = ctk.CTkScrollableFrame(
            select_section,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            height=135,
        )
        self.items_scroll.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        self.items_scroll.grid_columnconfigure(0, weight=1)

        # Thanh tùy chọn tải xuống
        action_bar = ctk.CTkFrame(select_section, fg_color="transparent")
        action_bar.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        action_bar.grid_columnconfigure(3, weight=1)

        self.format_menu = ctk.CTkOptionMenu(
            action_bar,
            values=["Video (MP4)", "MP3 (Audio)"],
            width=125,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["primary"],
            font=FONTS["small"],
        )
        self.format_menu.set("Video (MP4)")
        self.format_menu.grid(row=0, column=0, padx=(0, 10))

        self.subfolder_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            action_bar,
            text="Tạo thư mục theo tên tài khoản",
            variable=self.subfolder_var,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=0, column=1, padx=(0, 10))

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
        self.dir_btn.grid(row=0, column=2, columnspan=2, sticky="ew", padx=(0, 10))

        self.download_btn = ctk.CTkButton(
            action_bar,
            text="Tải video đã chọn",
            font=FONTS["body_bold"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=34,
            width=165,
            state="disabled",
            command=self._submit_selected,
        )
        self.download_btn.grid(row=0, column=4, sticky="e")

        # 4. Khu vực tiến độ tải
        self.queue_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_input"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
            height=140,
        )
        self.queue_scroll.grid(row=3, column=0, sticky="nsew", padx=28, pady=(0, 20))
        self.queue_scroll.grid_columnconfigure(0, weight=1)

    def _choose_directory(self) -> None:
        selected = filedialog.askdirectory(initialdir=self._output_dir)
        if selected:
            self._output_dir = selected
            self.dir_btn.configure(text=f"Lưu tại: .../{Path(selected).name}")

    def _start_fetch_profile(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            return

        selected_limit = self._LIMIT_MAP[self.limit_menu.get()]

        self.fetch_btn.configure(state="disabled", text="Đang quét...")
        self.status_banner.configure(
            text="Đang lấy danh sách video từ tài khoản TikTok...",
            text_color=COLORS["primary"],
        )
        self.status_banner.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 10))

        def _worker():
            try:
                meta = self._extractor.get_profile_info(url, max_items=selected_limit)
                self.after(0, self._on_fetch_success, meta)
            except Exception as exc:
                self.after(0, self._on_fetch_error, str(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_fetch_success(self, meta: PlaylistMetadata) -> None:
        self.fetch_btn.configure(state="normal", text="Quét Tài Khoản")
        self.status_banner.grid_forget()
        self._current_profile = meta

        for widget in self.items_scroll.winfo_children():
            widget.destroy()
        self._item_vars.clear()

        self.profile_title_label.configure(
            text=f"Tài khoản: {meta.title}  ({len(meta.items)} video tìm thấy)"
        )

        for row_idx, item in enumerate(meta.items):
            var = ctk.BooleanVar(value=item.is_available)
            duration_str = _format_duration(item.duration_sec)
            label = f"#{item.index:02d}  [{duration_str}]  {item.title}"

            cb = ctk.CTkCheckBox(
                self.items_scroll,
                text=label,
                variable=var,
                font=FONTS["small"],
                text_color=COLORS["text_primary"] if item.is_available else COLORS["text_muted"],
                state="normal" if item.is_available else "disabled",
                checkbox_width=18,
                checkbox_height=18,
            )
            cb.grid(row=row_idx, column=0, sticky="w", padx=8, pady=4)
            if item.is_available:
                self._item_vars.append((item, var))

        self.download_btn.configure(state="normal" if self._item_vars else "disabled")

    def _on_fetch_error(self, error_msg: str) -> None:
        self.fetch_btn.configure(state="normal", text="Quét Tài Khoản")
        self.status_banner.configure(text=f"Lỗi: {error_msg}", text_color=COLORS["danger"])

    def _toggle_all(self, value: bool) -> None:
        for _item, var in self._item_vars:
            var.set(value)

    def _submit_selected(self) -> None:
        if not self._current_profile:
            return

        selected_items = [item for item, var in self._item_vars if var.get()]
        if not selected_items:
            return

        target_dir = Path(self._output_dir)
        if self.subfolder_var.get():
            target_dir = target_dir / _sanitize_folder_name(self._current_profile.title)

        selected_format = self.format_menu.get()
        for item in selected_items:
            self._manager.add_task(
                url=item.url,
                output_dir=str(target_dir),
                resolution=selected_format,
                source="tiktok_profile",
                title=f"{item.index:02d} - {item.title}",
            )

    def render_task_update(self, task: DownloadTask) -> None:
        if task.task_id not in self._task_rows:
            row_idx = len(self._task_rows)
            row = TaskRow(self.queue_scroll, task)
            row.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=6)
            self._task_rows[task.task_id] = row
        else:
            self._task_rows[task.task_id].update_state(task)