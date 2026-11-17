"""Giao diện Tkinter: kéo thả file từ danh sách Server sang khu vực download."""

import argparse
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk

from client_core import download_file, list_files


def format_speed(speed):
    if speed >= 1024 * 1024:
        return f"{speed / (1024 * 1024):.2f} MB/s"
    return f"{speed / 1024:.1f} KB/s"


class DownloadApp:
    """Thread nền chỉ xử lý mạng; chỉ luồng Tkinter được cập nhật widget."""

    def __init__(self, root, host, port, folder, limit):
        self.root = root
        self.host = host
        self.port = port
        self.folder = folder
        self.limit = limit
        self.active = 0
        self.waiting = []
        self.drag_names = []
        self.events = queue.Queue()
        self._make_window()
        self.refresh_files()
        self.root.after(100, self._read_events)

    def _make_window(self):
        self.root.title("UDM_11 - Download nhiều file")
        self.root.geometry("1050x500")

        self.connection_label = ttk.Label(self.root, text="Đang kết nối...")
        self.connection_label.pack(anchor="w", padx=10, pady=(10, 0))

        panels = ttk.Panedwindow(self.root, orient="horizontal")
        panels.pack(fill="both", expand=True, padx=10, pady=10)
        left = ttk.Frame(panels)
        right = ttk.Frame(panels)
        panels.add(left, weight=1)
        panels.add(right, weight=2)

        ttk.Label(left, text="File trên Server (kéo sang bên phải để tải)").pack(anchor="w")
        self.server_list = ttk.Treeview(
            left, columns=("name", "size"), show="headings", selectmode="extended"
        )
        self.server_list.heading("name", text="Tên file")
        self.server_list.heading("size", text="Kích thước")
        self.server_list.column("size", width=90, anchor="e")
        self.server_list.pack(fill="both", expand=True, pady=6)
        ttk.Button(left, text="Làm mới", command=self.refresh_files).pack(anchor="e")

        ttk.Label(right, text=f"File tải xuống (tối đa {self.limit} file cùng lúc)").pack(anchor="w")
        self.download_list = ttk.Treeview(
            right, columns=("name", "status", "speed", "progress"), show="headings"
        )
        for column, title, width in (
            ("name", "Tên file", 200),
            ("status", "Trạng thái", 200),
            ("speed", "Tốc độ", 90),
            ("progress", "Tiến trình", 80),
        ):
            self.download_list.heading(column, text=title)
            self.download_list.column(column, width=width)
        self.download_list.pack(fill="both", expand=True, pady=6)

        self.server_list.bind("<ButtonPress-1>", self._drag_start)
        self.server_list.bind("<ButtonRelease-1>", self._drag_end)

    # ---------- Danh sách file trên Server ----------

    def refresh_files(self):
        """Gọi LIST ở thread nền để giao diện không bị treo."""
        self.connection_label.configure(text="Đang kết nối tới Server...")
        threading.Thread(target=self._load_files, daemon=True).start()

    def _load_files(self):
        try:
            self.events.put(("files", list_files(self.host, self.port)))
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            self.events.put(("list_error", str(error)))

    # ---------- Kéo thả ----------

    def _drag_start(self, event):
        """Lưu các file đang chọn trước khi Treeview đổi lựa chọn."""
        row = self.server_list.identify_row(event.y)
        selected = self.server_list.selection()
        self.drag_names = list(selected) if row in selected else ([row] if row else [])

    def _drag_end(self, event):
        """Thả chuột trong khu vực download thì thêm các file đã kéo vào hàng đợi."""
        area = self.download_list
        inside = (
            area.winfo_rootx() <= event.x_root <= area.winfo_rootx() + area.winfo_width()
            and area.winfo_rooty() <= event.y_root <= area.winfo_rooty() + area.winfo_height()
        )
        if inside:
            self.add_files(self.drag_names)
        self.drag_names = []

    def add_files(self, names):
        """Mỗi file một dòng; file vượt giới hạn sẽ chờ trong hàng đợi."""
        for filename in names:
            row = self.download_list.insert(
                "", "end", values=(filename, "Chờ trong hàng đợi", "-", "0%")
            )
            self.waiting.append((row, filename))
        self._start_waiting()

    # ---------- Tải file ----------

    def _start_waiting(self):
        """Lấy file khỏi hàng đợi khi còn chỗ trống, không vượt quá giới hạn."""
        while self.active < self.limit and self.waiting:
            row, filename = self.waiting.pop(0)
            self.active += 1
            self._set_row(row, "Đang tải", "-", 0)
            threading.Thread(
                target=self._download_worker, args=(row, filename), daemon=True
            ).start()

    def _download_worker(self, row, filename):
        """Chạy ở thread nền: chỉ gửi sự kiện về GUI, không sửa widget."""
        def report(done, total, speed):
            self.events.put(("progress", row, done, total, speed))

        try:
            path, renamed = download_file(self.host, self.port, filename, self.folder, report)
            self.events.put(("done", row, path, renamed))
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            self.events.put(("error", row, str(error)))

    def _set_row(self, row, status, speed, percent):
        self.download_list.set(row, "status", status)
        self.download_list.set(row, "speed", speed)
        self.download_list.set(row, "progress", f"{percent}%")

    # ---------- Nhận sự kiện từ thread nền ----------

    def _read_events(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break

            kind = event[0]
            if kind == "files":
                self.server_list.delete(*self.server_list.get_children())
                for info in event[1]:
                    self.server_list.insert(
                        "", "end", iid=info["name"],
                        values=(info["name"], f"{info['size'] / 1024:.1f} KB"),
                    )
                self.connection_label.configure(
                    text=f"Đã kết nối {self.host}:{self.port} - {len(event[1])} file trên Server"
                )
            elif kind == "list_error":
                self.connection_label.configure(text=f"Kết nối thất bại: {event[1]}")
            elif kind == "progress":
                _, row, done, total, speed = event
                percent = 100 if total == 0 else done * 100 // total
                self._set_row(row, "Đang tải", format_speed(speed), percent)
            elif kind == "done":
                _, row, path, renamed = event
                status = f"Thành công (lưu thành {os.path.basename(path)})" if renamed else "Thành công"
                self._set_row(row, status, "-", 100)
                self.active -= 1
            elif kind == "error":
                _, row, reason = event
                self._set_row(row, f"Thất bại: {reason}", "-", 0)
                self.active -= 1
            self._start_waiting()

        self.root.after(100, self._read_events)


def main():
    parser = argparse.ArgumentParser(description="UDM_11 Client")
    parser.add_argument("--host", required=True, help="IP hoặc hostname của Server")
    parser.add_argument("--port", type=int, required=True, help="Cổng TCP")
    parser.add_argument("--download-dir", required=True, help="Thư mục lưu file tải về")
    parser.add_argument("--max-downloads", type=int, default=3, help="Số file tải cùng lúc tối đa")
    args = parser.parse_args()
    if args.max_downloads < 1:
        parser.error("--max-downloads phải lớn hơn 0")

    root = tk.Tk()
    DownloadApp(root, args.host, args.port, args.download_dir, args.max_downloads)
    root.mainloop()


if __name__ == "__main__":
    main()
