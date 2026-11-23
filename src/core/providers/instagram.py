import re
from pathlib import Path
from typing import Any, Dict, Optional
import yt_dlp

from src.core.base import BaseDownloader, ProgressCallback
from src.core.models import DownloadProgress, VideoMetadata
from src.utils.system import get_ffmpeg_dir


class InstagramDownloader(BaseDownloader):
    _URL_PATTERN = re.compile(
        r"(https?://)?(www\.|m\.)?(instagram\.com|instagr\.am)/.+"
    )

    def can_handle(self, url: str) -> bool:
        return bool(self._URL_PATTERN.match(url.strip()))

    def get_info(self, url: str) -> VideoMetadata:
        options: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                raw_title = (info.get("title") or info.get("description") or "").strip()
                clean_title = " ".join(raw_title.split())
                video_id = info.get("id") or "reel"
                title = clean_title if clean_title else f"Instagram_{video_id}"

                return VideoMetadata(
                    url=url,
                    title=title[:100],
                    uploader=info.get("uploader") or info.get("channel") or "Instagram User",
                    duration_sec=int(info.get("duration") or 0),
                )
        except Exception as exc:
            msg = str(exc).lower()
            if "login" in msg or "cookies" in msg or "private" in msg:
                raise ValueError(
                    "Không thể tải nội dung này (bài viết riêng tư hoặc Instagram yêu cầu đăng nhập)."
                ) from exc
            raise

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
            if info.get("_type") == "playlist":
                entries = [e for e in (info.get("entries") or []) if e]
                target_info = entries[0] if entries else info
            else:
                target_info = info

            raw_path = Path(ydl.prepare_filename(target_info))
            return str(raw_path.with_suffix(target_ext))

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