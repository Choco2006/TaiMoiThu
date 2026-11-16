from typing import Callable, List, Tuple
import customtkinter as ctk
from src.ui.theme import COLORS, FONTS


class HomeView(ctk.CTkFrame):
    def __init__(self, master, on_select_platform: Callable[[str], None], **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_select_platform = on_select_platform
        self.grid_columnconfigure(0, weight=1)

        # Header chào mừng
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 18))

        ctk.CTkLabel(
            header,
            text="Trung tâm tải đa phương tiện",
            font=FONTS["h1"],
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Chọn nền tảng bên dưới để bắt đầu tải video chất lượng cao kèm âm thanh gốc.",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        # Thanh thông báo khi người dùng bấm vào nền tảng đang updating
        self.notice_banner = ctk.CTkLabel(
            self,
            text="",
            font=FONTS["small"],
            text_color=COLORS["warning"],
            fg_color="#2D2618",
            corner_radius=8,
            height=34,
        )

        # Lưới 3 cột các nền tảng
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.grid(row=2, column=0, sticky="nsew", padx=28, pady=8)
        grid_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="platform_col")

        platforms: List[Tuple[str, str, str, str, bool]] = [
            ("youtube", "YouTube", "Tải video đơn lẻ hoặc nhiều link cùng lúc (lên tới 1080p+)", "#EF4444", True),
            ("yt_playlist", "YouTube Playlist", "Tải trọn bộ danh sách phát tự động", "#DC2626", False),
            ("tiktok", "TikTok", "Tải video không dính logo (Watermark-free)", "#14B8A6", False),
            ("facebook", "Facebook", "Tải video công khai & Reels chất lượng HD", "#3B82F6", False),
            ("instagram", "Instagram", "Tải Reels, Video bài viết và Stories", "#EC4899", False),
            ("twitter", "X (Twitter)", "Trích xuất video & GIF từ bài đăng", "#9CA3AF", False),
        ]

        for idx, (key, name, desc, accent, is_ready) in enumerate(platforms):
            row, col = divmod(idx, 3)
            card = self._build_platform_card(grid_frame, key, name, desc, accent, is_ready)
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)

    def _build_platform_card(
        self,
        parent,
        key: str,
        name: str,
        desc: str,
        accent: str,
        is_ready: bool,
    ) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["primary"] if is_ready else COLORS["border"],
            cursor="hand2",
        )
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top.grid_columnconfigure(1, weight=1)

        # Chấm tròn nhận diện màu thương hiệu
        dot = ctk.CTkFrame(top, width=12, height=12, corner_radius=6, fg_color=accent)
        dot.grid(row=0, column=0, padx=(0, 8))

        title = ctk.CTkLabel(
            top,
            text=name,
            font=FONTS["h2"],
            text_color=COLORS["text_primary"] if is_ready else COLORS["text_secondary"],
            anchor="w",
        )
        title.grid(row=0, column=1, sticky="w")

        badge_text = "Sẵn sàng" if is_ready else "Updating..."
        badge_fg = "#142E25" if is_ready else "#252932"
        badge_color = COLORS["success"] if is_ready else COLORS["text_muted"]

        badge = ctk.CTkLabel(
            top,
            text=badge_text,
            font=FONTS["small"],
            text_color=badge_color,
            fg_color=badge_fg,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        badge.grid(row=0, column=2, sticky="e")

        desc_label = ctk.CTkLabel(
            card,
            text=desc,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"] if is_ready else COLORS["text_muted"],
            anchor="w",
            justify="left",
            wraplength=230,
        )
        desc_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))

        def handle_click(_event=None):
            if is_ready:
                self.notice_banner.grid_forget()
                self._on_select_platform(key)
            else:
                self.notice_banner.configure(
                    text=f"  Module '{name}' đang ở trạng thái Updating... (Kiến trúc Provider đã sẵn sàng để mở rộng)"
                )
                self.notice_banner.grid(row=1, column=0, sticky="ew", padx=36, pady=(0, 8))

        for widget in (card, top, title, badge, desc_label):
            widget.bind("<Button-1>", handle_click)

        return card