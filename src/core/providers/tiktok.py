import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yt_dlp

from src.core.base import BaseDownloader, ProgressCallback
from src.core.models import (
    DownloadProgress,
    PlaylistItem,
    PlaylistMetadata,
    VideoMetadata,
)
from src.utils.system import get_ffmpeg_dir


class TikTokDownloader(BaseDownloader):
    _URL_PATTERN = re.compile(
        r"(https?://)?(www\.|vm\.|vt\.|m\.)?tiktok\.com/.+"
    )
    _PROFILE_PATTERN = re.compile(
        r"(?:https?://)?(?:www\.|m\.)?tiktok\.com/(@[^/?#]+)"
    )

    def can_handle(self, url: str) -> bool:
        return bool(self._URL_PATTERN.match(url.strip()))

    def get_info(self, url: str) -> VideoMetadata:
        options: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_title = (info.get("title") or "").strip()
            video_id = info.get("id") or "video"
            title = raw_title if raw_title else f"TikTok_{video_id}"

            return VideoMetadata(
                url=url,
                title=title[:100],
                uploader=info.get("uploader") or info.get("creator") or "TikTok Creator",
                duration_sec=int(info.get("duration") or 0),
            )

    def get_profile_info(
        self,
        url: str,
        max_items: Optional[int] = 50,
    ) -> PlaylistMetadata:
        """Lấy nhanh danh sách video từ một trang cá nhân TikTok."""
        target_url, handle = self._normalize_profile_url(url)

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

        raw_entries = info.get("entries") or []
        items: List[PlaylistItem] = []

        for idx, entry in enumerate(raw_entries, start=1):
            if not entry:
                continue

            video_id = str(entry.get("id") or "")
            entry_url = entry.get("url") or entry.get("webpage_url") or ""
            if entry_url and not entry_url.startswith("http"):
                entry_url = f"https://www.tiktok.com/{handle}/video/{entry_url}"
            elif not entry_url and video_id:
                entry_url = f"https://www.tiktok.com/{handle}/video/{video_id}"

            raw_title = (entry.get("title") or entry.get("description") or "").strip()
            clean_title = " ".join(raw_title.split())
            if not clean_title:
                clean_title = f"TikTok Video #{idx} ({video_id})" if video_id else f"TikTok Video #{idx}"

            items.append(
                PlaylistItem(
                    index=idx,
                    url=entry_url,
                    title=clean_title[:90],
                    duration_sec=int(entry.get("duration") or 0),
                    is_available=bool(entry_url),
                )
            )

        if not items:
            raise ValueError(f"Không tìm thấy video công khai nào trên tài khoản {handle}.")

        uploader_name = info.get("uploader") or info.get("creator") or handle
        return PlaylistMetadata(
            url=target_url,
            title=uploader_name,
            uploader=uploader_name,
            items=items,
        )

    def download(
        self,
        url: str,
        output_dir: str,
        resolution: str = "Video (MP4)",
        on_progress: Optional[ProgressCallback] = None,
    ) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        mode = resolution.strip().lower()

        options: Dict[str, Any] = {
            "outtmpl": f"{output_dir}/%(title).80s [%(id)s].%(ext)s",
            "windowsfilenames": True,
            "quiet": True,
            "no_warnings": True,
        }

        if "mp3" in mode or "audio" in mode:
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
            target_ext = ".mp3"
        else:
            options["format"] = "bestvideo+bestaudio/best"
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

    def _normalize_profile_url(self, url: str) -> Tuple[str, str]:
        """Chuẩn hóa link trang cá nhân TikTok về dạng https://www.tiktok.com/@username."""
        cleaned = url.strip().split("?")[0].rstrip("/")
        if "/video/" in cleaned or "/photo/" in cleaned:
            raise ValueError("Đây là link bài đăng đơn lẻ, không phải trang cá nhân TikTok.")

        if cleaned.startswith("@"):
            handle = cleaned.split("/")[0]
            return f"https://www.tiktok.com/{handle}", handle

        match = self._PROFILE_PATTERN.match(cleaned)
        if not match:
            raise ValueError(
                "Đường dẫn tài khoản TikTok không hợp lệ (ví dụ: https://www.tiktok.com/@username hoặc @username)."
            )

        handle = match.group(1)
        return f"https://www.tiktok.com/{handle}", handle

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