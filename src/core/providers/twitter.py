import re
from pathlib import Path
from typing import Any, Dict, Optional
import yt_dlp

from src.core.base import BaseDownloader, ProgressCallback
from src.core.models import DownloadProgress, VideoMetadata
from src.utils.system import get_ffmpeg_dir


class TwitterDownloader(BaseDownloader):
    _URL_PATTERN = re.compile(
        r"^(https?://)?(www\.|mobile\.)?(x\.com|twitter\.com|fxtwitter\.com|vxtwitter\.com)/[^/]+/status/\d+.*"
    )

    def can_handle(self, url: str) -> bool:
        return bool(self._URL_PATTERN.match(url.strip()))

    @staticmethod
    def _normalize_url(url: str) -> str:
        cleaned = url.strip()
        cleaned = re.sub(
            r"^(https?://)?(www\.|mobile\.)?(fxtwitter\.com|vxtwitter\.com)/",
            r"https://x.com/",
            cleaned,
        )
        if not cleaned.startswith(("http://", "https://")):
            cleaned = f"https://{cleaned}"
        return cleaned

    def get_info(self, url: str) -> VideoMetadata:
        target_url = self._normalize_url(url)
        options: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if info.get("_type") == "playlist":
                entries = [e for e in (info.get("entries") or []) if e]
                target_info = entries[0] if entries else info
            else:
                target_info = info

            raw_title = (target_info.get("title") or "").replace("\n", " ").strip()
            video_id = target_info.get("id") or "video"
            title = raw_title if raw_title else f"X_Video_{video_id}"

            return VideoMetadata(
                url=target_url,
                title=title[:100],
                uploader=target_info.get("uploader") or target_info.get("channel") or "X User",
                duration_sec=int(target_info.get("duration") or 0),
            )

    def download(
        self,
        url: str,
        output_dir: str,
        resolution: str = "Video (MP4)",
        on_progress: Optional[ProgressCallback] = None,
    ) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        target_url = self._normalize_url(url)
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
            options["format"] = self._build_format_selector(mode)
            options["merge_output_format"] = "mp4"
            target_ext = ".mp4"

        ffmpeg_dir = get_ffmpeg_dir()
        if ffmpeg_dir:
            options["ffmpeg_location"] = ffmpeg_dir

        if on_progress:
            options["progress_hooks"] = [self._wrap_hook(on_progress)]

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(target_url, download=True)
            if info.get("_type") == "playlist":
                entries = [e for e in (info.get("entries") or []) if e]
                target_info = entries[0] if entries else info
            else:
                target_info = info

            raw_path = Path(ydl.prepare_filename(target_info))
            return str(raw_path.with_suffix(target_ext))

    @staticmethod
    def _build_format_selector(mode: str) -> str:
        height = mode.replace("p", "")
        if height.isdigit():
            return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
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