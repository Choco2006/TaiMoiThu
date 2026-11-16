from abc import ABC, abstractmethod
from typing import Callable, Optional
from src.core.models import DownloadProgress, VideoMetadata

ProgressCallback = Callable[[DownloadProgress], None]


class BaseDownloader(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Kiểm tra URL có thuộc nền tảng này không."""
        pass

    @abstractmethod
    def get_info(self, url: str) -> VideoMetadata:
        """Lấy thông tin cơ bản của video trước khi tải."""
        pass

    @abstractmethod
    def download(
        self,
        url: str,
        output_dir: str,
        resolution: str = "1080p",
        on_progress: Optional[ProgressCallback] = None,
    ) -> str:
        """Tải video, báo tiến độ qua callback và trả về đường dẫn file thành phẩm."""
        pass