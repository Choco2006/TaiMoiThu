import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yt_dlp

from src.core.base import BaseDownloader, ProgressCallback
from src.core.models import (
    DownloadProgress,
    PlaylistItem,
    PlaylistMetadata,
    VideoMetadata,
)
from src.utils.system import get_ffmpeg_dir


class YouTubeDownloader(BaseDownloader):
    _URL_PATTERN = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+")
    _CHANNEL_PATTERN = re.compile(
        r"(https?://)?(www\.)?youtube\.com/(@[^/?#]+|channel/[^/?#]+|c/[^/?#]+|user/[^/?#]+)"
    )
    _CHANNEL_TABS = ("videos", "shorts", "streams")
    _UNAVAILABLE_TITLES = {"[deleted video]", "[private video]"}
    _AUDIO_CODECS = {
        "mp3 (audio)": "mp3",
        "mp3": "mp3",
        "m4a (audio)": "m4a",
        "m4a": "m4a",
    }

    def can_handle(self, url: str) -> bool:
        return bool(self._URL_PATTERN.match(url.strip()))

    def get_info(self, url: str) -> VideoMetadata:
        options: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            return VideoMetadata(
                url=url,
                title=info.get("title", "Unknown Title"),
                uploader=info.get("uploader", "Unknown Channel"),
                duration_sec=int(info.get("duration") or 0),
            )

    def get_playlist_info(self, url: str) -> PlaylistMetadata:
        """Lấy nhanh danh sách video trong Playlist mà không tải nội dung."""
        if not self.can_handle(url):
            raise ValueError("Đường dẫn không phải của YouTube.")

        options: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "noplaylist": False,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        if info.get("_type") != "playlist":
            raise ValueError("Đường dẫn này là video đơn lẻ, không chứa danh sách phát (Playlist).")

        items = self._parse_flat_entries(info.get("entries") or [])
        if not items:
            raise ValueError("Playlist trống hoặc toàn bộ video đang ở chế độ riêng tư.")

        return PlaylistMetadata(
            url=url,
            title=info.get("title") or "YouTube Playlist",
            uploader=info.get("uploader") or info.get("channel") or "Unknown Channel",
            items=items,
        )

    def get_channel_info(
        self,
        url: str,
        tab: str = "videos",
        max_items: Optional[int] = 50,
    ) -> PlaylistMetadata:
        """Lấy nhanh danh sách video từ một kênh YouTube theo tab (videos/shorts/streams)."""
        target_url = self._normalize_channel_url(url, tab)

        options: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "noplaylist": False,
        }
        if max_items and max_items > 0:
            options["playlistend"] = max_items

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(target_url, download=False)

        items = self._parse_flat_entries(info.get("entries") or [])
        if not items:
            raise ValueError(f"Không tìm thấy nội dung nào trong mục '{tab}' của kênh này.")

        raw_title = info.get("channel") or info.get("uploader") or info.get("title") or "YouTube Channel"
        clean_channel_name = re.sub(r"\s*-\s*(Videos|Shorts|Live)$", "", raw_title, flags=re.IGNORECASE)

        return PlaylistMetadata(
            url=target_url,
            title=clean_channel_name,
            uploader=clean_channel_name,
            items=items,
        )

    def download(
        self,
        url: str,
        output_dir: str,
        resolution: str = "1080p",
        on_progress: Optional[ProgressCallback] = None,
    ) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        audio_codec = self._resolve_audio_codec(resolution)

        options: Dict[str, Any] = {
            "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        if audio_codec:
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_codec,
                    "preferredquality": "192",
                }
            ]
            target_ext = f".{audio_codec}"
        else:
            options["format"] = self._build_format_selector(resolution)
            options["merge_output_format"] = "mp4"
            target_ext = ".mp4"

        ffmpeg_dir = get_ffmpeg_dir()
        if ffmpeg_dir:
            options["ffmpeg_location"] = ffmpeg_dir

        if on_progress:
            options["progress_hooks"] = [self._wrap_hook(on_progress)]

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            raw_path = Path(ydl.prepare_filename(info))
            return str(raw_path.with_suffix(target_ext))

    @classmethod
    def _resolve_audio_codec(cls, resolution: str) -> Optional[str]:
        """Trả về 'mp3'/'m4a' nếu người dùng chọn tải âm thanh, ngược lại trả về None."""
        return cls._AUDIO_CODECS.get(resolution.strip().lower())

    def _normalize_channel_url(self, url: str, tab: str) -> str:
        """Chuẩn hóa link kênh về dạng https://www.youtube.com/@handle/<tab>."""
        cleaned = url.strip().split("?")[0].rstrip("/")
        match = self._CHANNEL_PATTERN.match(cleaned)
        if not match:
            raise ValueError(
                "Đường dẫn không phải kênh YouTube hợp lệ (ví dụ: https://www.youtube.com/@TenKenh)."
            )

        selected_tab = tab if tab in self._CHANNEL_TABS else "videos"
        base_channel_url = match.group(0)
        if not base_channel_url.startswith("http"):
            base_channel_url = f"https://{base_channel_url}"

        return f"{base_channel_url}/{selected_tab}"

    def _parse_flat_entries(self, raw_entries: List[Dict[str, Any]]) -> List[PlaylistItem]:
        """Chuyển đổi danh sách dữ liệu thô từ yt-dlp thành danh sách PlaylistItem chuẩn."""
        items: List[PlaylistItem] = []
        for idx, entry in enumerate(raw_entries, start=1):
            if not entry or entry.get("_type") == "playlist":
                continue

            raw_title = (entry.get("title") or f"Video #{idx}").strip()
            is_available = raw_title.lower() not in self._UNAVAILABLE_TITLES

            video_id = entry.get("id")
            entry_url = entry.get("url") or ""
            if entry_url and not entry_url.startswith("http"):
                entry_url = f"https://www.youtube.com/watch?v={entry_url}"
            elif not entry_url and video_id:
                entry_url = f"https://www.youtube.com/watch?v={video_id}"

            items.append(
                PlaylistItem(
                    index=idx,
                    url=entry_url,
                    title=raw_title,
                    duration_sec=int(entry.get("duration") or 0),
                    is_available=is_available and bool(entry_url),
                )
            )
        return items

    @staticmethod
    def _build_format_selector(resolution: str) -> str:
        if resolution == "best":
            return "bestvideo+bestaudio/best"
        height = resolution.lower().replace("p", "")
        if height.isdigit():
            return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
        return "bestvideo+bestaudio/best"

    @staticmethod
    def _wrap_hook(callback: ProgressCallback):
        def _hook(data: dict) -> None:
            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                downloaded = data.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total > 0 else 0.0

                callback(
                    DownloadProgress(
                        status="downloading",
                        percent=round(percent, 1),
                        speed_text=(data.get("_speed_str") or "N/A").strip(),
                        eta_text=(data.get("_eta_str") or "N/A").strip(),
                    )
                )
            elif status == "finished":
                callback(
                    DownloadProgress(
                        status="finished",
                        percent=100.0,
                        speed_text="0B/s",
                        eta_text="00:00",
                        filename=data.get("filename"),
                    )
                )

        return _hook