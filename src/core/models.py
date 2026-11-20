from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


@dataclass(frozen=True)
class VideoMetadata:
    url: str
    title: str
    uploader: str
    duration_sec: int


@dataclass(frozen=True)
class PlaylistItem:
    index: int
    url: str
    title: str
    duration_sec: int
    is_available: bool = True


@dataclass(frozen=True)
class PlaylistMetadata:
    url: str
    title: str
    uploader: str
    items: List[PlaylistItem]


@dataclass(frozen=True)
class DownloadProgress:
    status: str                  # "downloading" | "processing" | "finished"
    percent: float               # Giá trị số từ 0.0 -> 100.0
    speed_text: str              # Ví dụ: "4.52MiB/s"
    eta_text: str                # Ví dụ: "00:12"
    filename: Optional[str] = None


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class DownloadTask:
    task_id: str
    url: str
    output_dir: str = "downloads"
    resolution: str = "1080p"
    source: str = "youtube"      # Phân biệt tác vụ từ màn hình YouTube hay Playlist
    status: TaskStatus = TaskStatus.PENDING
    title: Optional[str] = None
    progress: float = 0.0
    speed_text: str = ""
    eta_text: str = ""
    saved_path: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0