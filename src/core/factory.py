from typing import List

from src.core.base import BaseDownloader
from src.core.providers.tiktok import TikTokDownloader
from src.core.providers.youtube import YouTubeDownloader


class DownloaderFactory:
    def __init__(self) -> None:
        self._providers: List[BaseDownloader] = [
            YouTubeDownloader(),
            TikTokDownloader(),
        ]

    def create(self, url: str) -> BaseDownloader:
        cleaned_url = url.strip()
        for provider in self._providers:
            if provider.can_handle(cleaned_url):
                return provider
        raise ValueError(f"Chưa hỗ trợ đường dẫn này: {cleaned_url}")