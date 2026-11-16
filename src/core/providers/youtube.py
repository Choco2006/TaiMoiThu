import re
from pathlib import Path
from typing import Optional
import yt_dlp

from src.core.base import BaseDownloader, ProgressCallback
from src.core.models import DownloadProgress, VideoMetadata
from src.utils.system import get_ffmpeg_dir


class YouTubeDownloader(BaseDownloader):
    _URL_PATTERN = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+")

    def can_handle(self, url: str) -> bool:
        return bool(self._URL_PATTERN.match(url.strip()))

    def get_info(self, url: str) -> VideoMetadata:
        options = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            return VideoMetadata(
                url=url,
                title=info.get("title", "Unknown Title"),
                uploader=info.get("uploader", "Unknown Channel"),
                duration_sec=int(info.get("duration") or 0),
            )

    def download(
        self,
        url: str,
        output_dir: str,
        resolution: str = "1080p",
        on_progress: Optional[ProgressCallback] = None,
    ) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        options = {
            "format": self._build_format_selector(resolution),
            "merge_output_format": "mp4",
            "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
        }

        ffmpeg_dir = get_ffmpeg_dir()
        if ffmpeg_dir:
            options["ffmpeg_location"] = ffmpeg_dir

        if on_progress:
            options["progress_hooks"] = [self._wrap_hook(on_progress)]

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            raw_path = Path(ydl.prepare_filename(info))
            return str(raw_path.with_suffix(".mp4"))

    @staticmethod
    def _build_format_selector(resolution: str) -> str:
        """Chuyển chuỗi '1080p', '720p' thành bộ lọc format của yt-dlp."""
        if resolution == "best":
            return "bestvideo+bestaudio/best"
        height = resolution.lower().replace("p", "")
        if height.isdigit():
            return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
        return "bestvideo+bestaudio/best"

    @staticmethod
    def _wrap_hook(callback: ProgressCallback):
        """Bộ chuyển đổi (Adapter) biến dict của yt-dlp thành DownloadProgress chuẩn."""
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