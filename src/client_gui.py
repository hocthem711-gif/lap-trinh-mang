"""GUI Client cho xem file, kéo thả vào hàng đợi và theo dõi tải xuống."""

import argparse
import logging
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from client_core import download_file, list_files


class DownloadApp:
    """Giao diện và hàng đợi tải đơn giản, cập nhật widget trên luồng chính."""

    def __init__(self, root: tk.Tk, host: str, port: int, folder: str, limit: int):
        self.root = root
        self.host = host
        self.port = port
        self.folder = folder
        self.limit = limit
        self.active = 0
        self.next_job_id = 1
        self.waiting: list[tuple[str, str]] = []
        self.events: queue.Queue[tuple] = queue.Queue()
        self.drag_name = ""
        self.drag_names: list[str] = []
        self.is_dragging = False
        self.logger = self._make_logger()
        self._make_window()
        self.refresh_files()
        self.root.after(100, self._read_events)

    @staticmethod
    def _make_logger() -> logging.Logger:
        """Ghi log Client ra console và client.log."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            handlers=[
                logging.FileHandler("client.log", encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        return logging.getLogger("udm11.client")

    def _make_window(self) -> None:
        """Tạo hai danh sách file và các nút cơ bản."""
        self.root.title("UDM_11 - Download nhiều file")
        self.root.geometry("1000x580")
        panels = ttk.Panedwindow(self.root, orient="horizontal")
        panels.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(panels, padding=6)
        right = ttk.Frame(panels, padding=6)
        panels.add(left, weight=1)
        panels.add(right, weight=2)

        ttk.Label(left, text="File trên Server").pack(anchor="w")
        self.server_list = ttk.Treeview(
            left, columns=("size",), show="tree headings", selectmode="extended"
        )
        self.server_list.heading("#0", text="Tên file")
        self.server_list.heading("size", text="Kích thước")
        self.server_list.pack(fill="both", expand=True, pady=6)
        ttk.Button(left, text="Refresh", command=self.refresh_files).pack(anchor="e")

        ttk.Label(right, text=f"Download (tối đa {self.limit} file cùng lúc)").pack(anchor="w")
        self.download_list = ttk.Treeview(
            right, columns=("status", "speed", "progress"), show="tree headings"
        )
        self.download_list.heading("#0", text="Tên file")
        self.download_list.heading("status", text="Trạng thái")
        self.download_list.heading("speed", text="Tốc độ")
        self.download_list.heading("progress", text="Tiến trình")
        self.download_list.column("#0", width=220)
        self.download_list.column("status", width=210)
        self.download_list.column("speed", width=100)
        self.download_list.pack(fill="both", expand=True, pady=6)
        ttk.Button(
            right, text="Thêm file đã chọn", command=self.add_selected
        ).pack(anchor="e")

        self.server_list.bind("<ButtonPress-1>", self._drag_start)
        self.server_list.bind("<B1-Motion>", self._drag_motion)
        self.server_list.bind("<ButtonRelease-1>", self._drag_end)

    def refresh_files(self) -> None:
        """Lấy danh sách Server ở thread nền để cửa sổ không bị treo."""
        threading.Thread(target=self._load_files, daemon=True).start()

    def _load_files(self) -> None:
        """Đưa kết quả LIST vào queue để luồng GUI cập nhật."""
        try:
            self.events.put(("files", list_files(self.host, self.port)))
        except (OSError, RuntimeError, ValueError) as error:
            self.events.put(("list_error", str(error)))

    def _drag_start(self, event: tk.Event) -> None:
        """Chụp vùng chọn trước khi thao tác chuột làm thay đổi Treeview."""
        row = self.server_list.identify_row(event.y)
        self.drag_name = self.server_list.item(row, "text") if row else ""
        selected_rows = self.server_list.selection()
        if row and row in selected_rows:
            self.drag_names = [
                self.server_list.item(selected_row, "text")
                for selected_row in selected_rows
            ]
        elif self.drag_name:
            self.drag_names = [self.drag_name]
        else:
            self.drag_names = []
        self.is_dragging = False

    def _drag_motion(self, event: tk.Event) -> None:
        """Ghi nhận thao tác kéo chuột."""
        self.is_dragging = True

    def _drag_end(self, event: tk.Event) -> None:
        """Thả chuột trong Download để đưa cả nhóm file vào hàng đợi."""
        widget = self.download_list
        inside = (
            widget.winfo_rootx() <= event.x_root <= widget.winfo_rootx() + widget.winfo_width()
            and widget.winfo_rooty() <= event.y_root <= widget.winfo_rooty() + widget.winfo_height()
        )
        if inside and self.is_dragging:
            self.add_selected(self.drag_names)
        self.drag_name = ""
        self.drag_names = []
        self.is_dragging = False

    def add_selected(self, dragged_names: list[str] | None = None) -> None:
        """Tạo một lượt tải riêng cho từng file đang chọn."""
        names = [self.server_list.item(row, "text") for row in self.server_list.selection()]
        if dragged_names:
            names = dragged_names

        for name in names:
            if not name:
                continue
            row_id = f"download-{self.next_job_id}"
            self.next_job_id += 1
            self.download_list.insert(
                "", "end", iid=row_id, text=name,
                values=("Chờ trong hàng đợi", "-", self._progress_text(0)),
            )
            self.waiting.append((row_id, name))
        self._start_waiting()

    @staticmethod
    def _progress_text(percent: int) -> str:
        """Hiển thị tiến trình dạng phần trăm đơn giản."""
        return f"{percent}%"

    def _start_waiting(self) -> None:
        """Bắt đầu job tiếp theo nếu còn chỗ trong giới hạn đồng thời."""
        while self.active < self.limit and self.waiting:
            row, filename = self.waiting.pop(0)
            self.active += 1
            self._set_row(row, "Đang tải", "-", self._progress_text(0))
            threading.Thread(
                target=self._download_worker, args=(row, filename), daemon=True
            ).start()

    def _download_worker(self, row: str, filename: str) -> None:
        """Tải file nền; mọi cập nhật GUI được gửi qua queue."""
        def report(done: int, total: int, speed: float) -> None:
            self.events.put(("progress", row, done, total, speed))

        try:
            path, renamed = download_file(
                self.host, self.port, filename, self.folder, report
            )
            self.events.put(("done", row, path, renamed))
        except (OSError, RuntimeError, ValueError) as error:
            self.logger.error("Tải file %s thất bại: %s", filename, error)
            self.events.put(("error", row, str(error)))

    def _set_row(self, row: str, status: str, speed: str, progress: str) -> None:
        """Cập nhật một hàng từ luồng GUI."""
        if self.download_list.exists(row):
            self.download_list.item(row, values=(status, speed, progress))

    def _read_events(self) -> None:
        """Xử lý sự kiện nền trên luồng GUI và xếp lượt tải tiếp theo."""
        # Worker chỉ gửi dữ liệu vào queue; chỉ luồng Tkinter mới cập nhật widget.
        while not self.events.empty():
            event = self.events.get()
            if event[0] == "files":
                self.server_list.delete(*self.server_list.get_children())
                for file in event[1]:
                    size = file["size"]
                    size_text = f"{size / 1024:.1f} KB"
                    self.server_list.insert("", "end", text=file["name"], values=(size_text,))
            elif event[0] == "list_error":
                self.logger.error("Không lấy được danh sách: %s", event[1])
                messagebox.showerror("Lỗi kết nối", event[1])
            elif event[0] == "progress":
                _, row, done, total, speed = event
                percent = 100 if total == 0 else int(done * 100 / total)
                speed_text = f"{speed / 1024:.1f} KB/s"
                if speed >= 1024 * 1024:
                    speed_text = f"{speed / (1024 * 1024):.2f} MB/s"
                self._set_row(row, "Đang tải", speed_text, self._progress_text(percent))
            elif event[0] == "done":
                _, row, path, renamed = event
                status = f"Đã tồn tại - đổi tên: {os.path.basename(path)}" if renamed else "Hoàn thành"
                self._set_row(row, status, "-", self._progress_text(100))
                self.logger.info("Tải xong: %s", path)
                self.active -= 1
            elif event[0] == "error":
                _, row, reason = event
                self._set_row(row, f"Lỗi: {reason[:60]}", "-", self._progress_text(0))
                self.active -= 1
            self._start_waiting()
        self.root.after(100, self._read_events)


def main() -> None:
    """Đọc cấu hình Client rồi mở vòng lặp giao diện Tkinter."""
    parser = argparse.ArgumentParser(description="UDM_11 Client")
    parser.add_argument("--host", required=True, help="IP hoặc hostname của Server")
    parser.add_argument("--port", type=int, required=True, help="Port TCP")
    parser.add_argument("--download-dir", required=True, help="Thư mục lưu file")
    parser.add_argument("--max-downloads", type=int, default=3)
    args = parser.parse_args()
    if args.max_downloads < 1:
        parser.error("--max-downloads phải lớn hơn 0")

    root = tk.Tk()
    DownloadApp(root, args.host, args.port, args.download_dir, args.max_downloads)
    root.mainloop()


if __name__ == "__main__":
    main()
