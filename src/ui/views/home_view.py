from typing import Callable
import customtkinter as ctk

from src.ui.theme import COLORS, FONTS


class HomeView(ctk.CTkFrame):
    def __init__(
        self, master, on_select_platform: Callable[[str], None], **kwargs
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_select_platform = on_select_platform

        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 20))
        ctk.CTkLabel(
            header,
            text="Chọn nền tảng tải nội dung",
            font=FONTS["h1"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Hỗ trợ tải đa luồng tốc độ cao, tự động ghép hình ảnh và âm thanh chất lượng gốc.",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(4, 0))

        # Grid thẻ nền tảng
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.grid(row=1, column=0, sticky="nsew", padx=32, pady=8)
        for col in range(3):
            grid_frame.grid_columnconfigure(col, weight=1)

        platforms = [
            ("youtube", "YouTube", "Tải video đơn lẻ chất lượng cao", "#EF4444", True),
            ("yt_playlist", "YouTube Playlist", "Tải trọn bộ danh sách phát tự động", "#DC2626", True),
            ("yt_channel", "YouTube Channel", "Quét và tải video, Shorts từ cả kênh", "#B91C1C", True),
            ("tiktok", "TikTok", "Tải video & âm thanh từ TikTok", "#14B8A6", True),
            ("tiktok_profile", "TikTok Profile", "Quét và tải hàng loạt video từ tài khoản", "#0D9488", True),
            ("facebook", "Facebook", "Tải Reels & Video công khai (Updating...)", "#3B82F6", False),
        ]

        for idx, (key, title, desc, accent, active) in enumerate(platforms):
            row, col = divmod(idx, 3)
            self._create_card(grid_frame, row, col, key, title, desc, accent, active)

    def _create_card(
        self,
        parent,
        row: int,
        col: int,
        key: str,
        title: str,
        desc: str,
        accent: str,
        active: bool,
    ) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)

        badge = ctk.CTkFrame(card, width=36, height=6, fg_color=accent, corner_radius=3)
        badge.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))

        ctk.CTkLabel(
            card,
            text=title,
            font=FONTS["h2"],
            text_color=COLORS["text_primary"] if active else COLORS["text_muted"],
        ).grid(row=1, column=0, sticky="w", padx=18)

        ctk.CTkLabel(
            card,
            text=desc,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"] if active else COLORS["text_muted"],
            wraplength=220,
            justify="left",
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(4, 16))

        btn = ctk.CTkButton(
            card,
            text="Mở công cụ" if active else "Sắp ra mắt",
            font=FONTS["small"],
            height=32,
            fg_color=COLORS["primary"] if active else COLORS["bg_input"],
            hover_color=COLORS["primary_hover"] if active else COLORS["bg_input"],
            text_color=COLORS["text_primary"] if active else COLORS["text_muted"],
            state="normal" if active else "disabled",
            command=lambda: self._on_select_platform(key),
        )
        btn.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))