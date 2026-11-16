# TaiMoiThu — Open-Source Extensible Media Downloader

**TaiMoiThu** là ứng dụng Desktop mã nguồn mở hỗ trợ tải video và âm thanh chất lượng cao (`1080p+`) từ nhiều nền tảng mạng xã hội. Dự án được thiết kế theo **Kiến trúc phân tầng 3 lớp (Layered Architecture)** và **Lập trình hướng đối tượng (OOP)**, giúp tách biệt hoàn toàn giao diện người dùng khỏi tầng xử lý lõi để dễ dàng mở rộng thêm các nền tảng mới.

> **Định hướng phát triển:** Toàn bộ quá trình bóc tách luồng dữ liệu, tải đa luồng và ghép file `FFmpeg` đều thực thi trực tiếp trên máy tính của người dùng (local-first). Cách tiếp cận này giúp tận dụng tối đa băng thông cá nhân, giữ nguyên chất lượng gốc và tránh tình trạng chặn IP thường gặp ở các trang web tải video qua server trung gian. Trong tương lai, dự án sẽ cung cấp sẵn các bản đóng gói độc lập (`.exe`) để người dùng phổ thông tải về và sử dụng ngay.

---

## Tính năng & Lộ trình phát triển

- [x] **Tải video YouTube chất lượng cao:** Tự động chọn luồng hình và tiếng tốt nhất theo chuẩn DASH (`1080p`, `720p`, `480p`, `best`) và ghép thành file `.mp4` hoàn chỉnh qua `FFmpeg`.
- [x] **Hàng đợi tải đa luồng (Multi-threaded Queue):** Hỗ trợ dán nhiều link cùng lúc, xếp hàng FIFO, tải song song tối đa 3 luồng và tự động thử lại (auto-retry) khi kết nối mạng chập chờn.
- [x] **Giao diện Desktop hiện đại:** Xây dựng trên `CustomTkinter` (Dark Mode), cập nhật tiến độ `%`, tốc độ tải (`MiB/s`) và thời gian còn lại (`ETA`) theo thời gian thực.
- [x] **Tích hợp FFmpeg linh hoạt:** Tự động nhận diện `ffmpeg.exe` và `ffprobe.exe` trong thư mục `bin/` nội bộ (tương thích sẵn với cơ chế giải nén `sys._MEIPASS` của PyInstaller).
- [ ] **Mở rộng nền tảng (`Updating...`):**
  - [ ] YouTube Playlist
  - [ ] TikTok (không dính logo / watermark)
  - [ ] Facebook Video & Reels
  - [ ] Instagram Reels & Stories
  - [ ] X (Twitter) Video & GIF
- [ ] **Đóng gói phát hành (Release):** Xuất bản file thực thi `.exe` độc lập kèm sẵn `FFmpeg` thông qua GitHub Releases.

---

## Kiến trúc hệ thống

Dự án áp dụng các nguyên lý thiết kế **SOLID** (đặc biệt là *Open/Closed Principle*) cùng 3 mẫu thiết kế cốt lõi (**Strategy**, **Factory**, **Observer**):

```text
TaiMoiThu/
├── bin/                        # Chứa ffmpeg.exe và ffprobe.exe (không đẩy lên Git)
├── downloads/                  # Thư mục lưu video mặc định
├── src/
│   ├── core/                   # Tầng 3: Logic tải lõi & các mẫu thiết kế OOP
│   │   ├── models.py           # DTO chuẩn hóa dữ liệu (VideoMetadata, DownloadTask...)
│   │   ├── base.py             # Abstract Base Class (BaseDownloader)
│   │   ├── factory.py          # DownloaderFactory tự động chọn Provider theo URL
│   │   └── providers/          # Triển khai riêng cho từng nền tảng
│   │       └── youtube.py      # YouTubeDownloader (bọc yt-dlp & FFmpeg)
│   ├── services/               # Tầng 2: Điều phối hàng đợi & đa luồng
│   │   └── manager.py          # DownloadManager (Queue + ThreadPoolExecutor + Lock)
│   ├── ui/                     # Tầng 1: Giao diện người dùng (CustomTkinter)
│   │   ├── components/         # Các widget tái sử dụng (TaskRow)
│   │   ├── views/              # Các màn hình chức năng (HomeView, YouTubeView)
│   │   ├── app.py              # Cửa sổ chính & cầu nối luồng UI (Thread-safe)
│   │   └── theme.py            # Bảng màu và kiểu chữ dùng chung
│   └── utils/                  # Tiện ích hệ thống (dò đường dẫn FFmpeg)
├── main.py                     # Điểm khởi chạy ứng dụng
├── requirements.txt            # Danh sách thư viện phụ thuộc
├── codebase.md                 # Tài liệu phân tích chi tiết kiến trúc mã nguồn
└── worklog.md                  # Nhật ký phát triển & lộ trình dự án
```

---

## Cài đặt từ mã nguồn (Dành cho Developer)

### 1. Yêu cầu môi trường
- Python **3.10+**
- `FFmpeg` và `FFprobe`

### 2. Các bước thiết lập
```bash
# 1. Clone repository về máy
git clone https://github.com/Choco2006/TaiMoiThu.git
cd TaiMoiThu

# 2. Tạo và kích hoạt môi trường ảo
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 3. Cấu hình FFmpeg nội bộ
Tạo thư mục `bin/` ở thư mục gốc dự án và đặt 2 file thực thi **`ffmpeg.exe`** cùng **`ffprobe.exe`** vào bên trong (hoặc cài đặt `ffmpeg` vào biến môi trường `PATH` của hệ điều hành).

### 4. Khởi chạy ứng dụng
```bash
python main.py
```

---

## Hướng dẫn mở rộng nền tảng mới

Nhờ kiến trúc **Strategy + Factory**, việc bổ sung một nền tảng mới (ví dụ **TikTok**) không làm ảnh hưởng đến các module đang chạy:

1. **Tạo Provider mới:** Tạo file `src/core/providers/tiktok.py`, định nghĩa lớp `TikTokDownloader` kế thừa `BaseDownloader` và triển khai 3 phương thức: `can_handle()`, `get_info()`, `download()`.
2. **Đăng ký vào Factory:** Thêm `TikTokDownloader()` vào danh sách `_providers` trong `src/core/factory.py`.
3. **Mở khóa trên giao diện:** Cập nhật trạng thái sẵn sàng cho thẻ TikTok trong `src/ui/views/home_view.py` và thanh điều hướng tại `src/ui/app.py`.

---

## Giấy phép (License)

Dự án được phát hành dưới giấy phép **MIT License** — bạn tự do sử dụng, chỉnh sửa và phân phối lại mã nguồn cho mục đích học tập và phát triển cộng đồng.
