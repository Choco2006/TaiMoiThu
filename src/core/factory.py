from typing import List
from src.core.base import BaseDownloader
from src.core.providers.youtube import YouTubeDownloader


class DownloaderFactory:
    def __init__(self) -> None:
        self._providers: List[BaseDownloader] = [
            YouTubeDownloader(),
        ]

    def register(self, provider: BaseDownloader) -> None:
        """Cho phép đăng ký thêm nền tảng mới lúc runtime."""
        self._providers.append(provider)

    def create(self, url: str) -> BaseDownloader:
        for provider in self._providers:
            if provider.can_handle(url):
                return provider
        raise ValueError(f"Không tìm thấy trình tải phù hợp cho URL: {url}")