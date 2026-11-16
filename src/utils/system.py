import sys
from pathlib import Path
from typing import Optional


def get_ffmpeg_dir() -> Optional[str]:
    """Trả về đường dẫn thư mục bin/ ở gốc dự án hoặc trong gói PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)
    else:
        # system.py -> utils -> src -> thư mục gốc dự án
        base_dir = Path(__file__).resolve().parents[2]

    local_bin = base_dir / "bin"
    if (local_bin / "ffmpeg.exe").exists() or (local_bin / "ffmpeg").exists():
        return str(local_bin)
    return None