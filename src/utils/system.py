import os
from pathlib import Path
import shutil
import sys
from typing import Optional


def get_resource_path(relative_path: str) -> Path:
    """Lấy đường dẫn tài nguyên tương thích cả khi chạy code lẫn khi đóng gói PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return Path(base_path) / relative_path
    return Path(__file__).resolve().parents[2] / relative_path


def get_ffmpeg_dir() -> Optional[str]:
    """Tìm thư mục chứa ffmpeg/ffprobe (ưu tiên bản portable trong bin/)."""
    bundled_bin = get_resource_path("bin")
    ffmpeg_bin = bundled_bin / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if ffmpeg_bin.exists():
        return str(bundled_bin)

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return str(Path(system_ffmpeg).parent)

    return None


def get_default_download_dir() -> str:
    """Trả về thư mục Videos của người dùng làm nơi lưu mặc định."""
    videos_dir = Path.home() / "Videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    return str(videos_dir.resolve())