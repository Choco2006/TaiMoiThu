import ctypes
import os
import sys
import customtkinter as ctk

from src.core.factory import DownloaderFactory
from src.core.models import DownloadTask, TaskStatus
from src.services.manager import DownloadManager
from src.ui.theme import COLORS, FONTS
from src.ui.views.channel_view import YouTubeChannelView
from src.ui.views.facebook_view import FacebookView
from src.ui.views.home_view import HomeView
from src.ui.views.instagram_view import InstagramView
from src.ui.views.playlist_view import YouTubePlaylistView
from src.ui.views.tiktok_profile_view import TikTokProfileView
from src.ui.views.tiktok_view import TikTokView
from src.ui.views.youtube_view import YouTubeView


def _resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


class MediaDownloaderApp(ctk.CTk):
    def __init__(self) -> None:
        self._set_windows_app_id()
        super().__init__()
        ctk.set_appearance_mode("dark")

        self.title("TaiMoiThu — Media Downloader")
        self.geometry("1060x720")
        self.minsize(920, 620)
        self.configure(fg_color=COLORS["bg_main"])
        self._setup_icon()

        self._factory = DownloaderFactory()
        self._manager = DownloadManager(
            factory=self._factory,
            max_workers=3,
            max_retries=2,
            on_task_update=self._on_worker_task_update,
        )

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._nav_buttons = {}
        self._build_sidebar()
        self._build_views()
        self._switch_view("home")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    @staticmethod
    def _set_windows_app_id() -> None:
        if sys.platform.startswith("win"):
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "TaiMoiThu.MediaDownloader.1.0"
                )
            except Exception:
                pass

    def _setup_icon(self) -> None:
        for rel_path in ("assets/app.ico", "assests/app.ico", "app.ico"):
            icon_path = _resource_path(os.path.normpath(rel_path))
            if os.path.exists(icon_path):
                try:
                    self.iconbitmap(icon_path)
                    # CustomTkinter tự set icon mặc định sau ~200ms trên Windows nên cần ghi đè lại
                    self.after(250, lambda p=icon_path: self.iconbitmap(p))
                except Exception:
                    pass
                break

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self,
            width=230,
            fg_color=COLORS["bg_sidebar"],
            corner_radius=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(11, weight=1)

        # Brand Header
        brand_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(24, 20))
        ctk.CTkLabel(
            brand_frame,
            text="TaiMoiThu",
            font=FONTS["brand"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_frame,
            text="Media Engine v1.0",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(anchor="w")

        # Nhóm điều hướng chính
        nav_items = [
            ("home", "Trang chủ", 1),
            ("youtube", "YouTube", 2),
            ("yt_playlist", "YouTube Playlist", 3),
            ("yt_channel", "YouTube Channel", 4),
            ("tiktok", "TikTok", 5),
            ("tiktok_profile", "TikTok Profile", 6),
            ("facebook", "Facebook", 7),
            ("instagram", "Instagram", 8),
        ]
        for key, label, row in nav_items:
            self._add_nav_button(sidebar, key, label, row=row, active=True)

        # Đường kẻ phân cách nhóm mở rộng
        ctk.CTkLabel(
            sidebar,
            text="NỀN TẢNG MỞ RỘNG",
            font=("Segoe UI", 10, "bold"),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=9, column=0, sticky="ew", padx=20, pady=(18, 6))

        self._add_nav_button(sidebar, "twitter", "X / Twitter (Updating...)", row=10, active=False)

        # Bộ đếm trạng thái dưới đáy Sidebar
        self.stats_label = ctk.CTkLabel(
            sidebar,
            text="Hàng đợi: 0 đang xử lý | 0 xong",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["bg_card"],
            corner_radius=8,
            height=34,
        )
        self.stats_label.grid(row=12, column=0, sticky="ew", padx=14, pady=16)

    def _add_nav_button(
        self, parent, key: str, label: str, row: int, active: bool
    ) -> None:
        btn = ctk.CTkButton(
            parent,
            text=label,
            font=FONTS["body_bold"] if active else FONTS["small"],
            text_color=COLORS["text_primary"] if active else COLORS["text_muted"],
            fg_color="transparent",
            hover_color=COLORS["bg_card"],
            anchor="w",
            height=36,
            corner_radius=8,
            command=lambda: self._switch_view(key) if active else self._switch_view("home"),
        )
        btn.grid(row=row, column=0, sticky="ew", padx=12, pady=2)
        if active:
            self._nav_buttons[key] = btn

    def _build_views(self) -> None:
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.grid(row=0, column=1, sticky="nsew")
        self._container.grid_columnconfigure(0, weight=1)
        self._container.grid_rowconfigure(0, weight=1)

        self._views = {
            "home": HomeView(self._container, on_select_platform=self._switch_view),
            "youtube": YouTubeView(self._container, manager=self._manager),
            "yt_playlist": YouTubePlaylistView(self._container, manager=self._manager),
            "yt_channel": YouTubeChannelView(self._container, manager=self._manager),
            "tiktok": TikTokView(self._container, manager=self._manager),
            "tiktok_profile": TikTokProfileView(self._container, manager=self._manager),
            "facebook": FacebookView(self._container, manager=self._manager),
            "instagram": InstagramView(self._container, manager=self._manager),
        }

    def _switch_view(self, view_key: str) -> None:
        if view_key not in self._views:
            return

        for key, view in self._views.items():
            if key == view_key:
                view.grid(row=0, column=0, sticky="nsew")
            else:
                view.grid_forget()

        for key, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=COLORS["bg_card"] if key == view_key else "transparent",
                text_color=COLORS["primary"] if key == view_key else COLORS["text_primary"],
            )

    def _on_worker_task_update(self, task: DownloadTask) -> None:
        self.after(0, self._apply_ui_update, task)

    def _apply_ui_update(self, task: DownloadTask) -> None:
        target_view = self._views.get(task.source)
        if target_view and hasattr(target_view, "render_task_update"):
            target_view.render_task_update(task)

        tasks = self._manager.get_all_tasks()
        active_count = sum(
            1 for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.DOWNLOADING)
        )
        done_count = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        self.stats_label.configure(
            text=f"Hàng đợi: {active_count} đang xử lý | {done_count} xong"
        )

    def _on_close(self) -> None:
        self.destroy()
        os._exit(0)