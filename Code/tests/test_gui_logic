"""Kiểm tra gom lựa chọn kéo-thả và giới hạn hàng đợi của GUI."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from client_gui import DownloadApp


class FakeTree:
    """Treeview giả để kiểm tra xử lý danh sách mà không mở cửa sổ GUI."""

    def __init__(self):
        self.names = {"one.txt": "one.txt", "two.txt": "two.txt"}

    def identify_row(self, y):
        return "one.txt"

    def selection(self):
        return ("one.txt", "two.txt")

    def item(self, row, option):
        return self.names[row]


class FakeDownloadArea:
    """Treeview giả có tọa độ để kiểm tra nơi thả chuột và thêm file."""

    def __init__(self):
        self.rows = {}
        self.next_id = 1

    def winfo_rootx(self):
        return 100

    def winfo_rooty(self):
        return 100

    def winfo_width(self):
        return 300

    def winfo_height(self):
        return 200

    def insert(self, parent, position, values):
        row = f"row-{self.next_id}"
        self.next_id += 1
        self.rows[row] = values
        return row


class FakeThread:
    """Thread giả ghi nhận số worker được yêu cầu chạy."""

    started = 0

    def __init__(self, target, args, daemon):
        self.target = target
        self.args = args

    def start(self):
        type(self).started += 1


class GuiLogicTests(unittest.TestCase):
    def test_drag_start_saves_all_selected_names(self):
        app = DownloadApp.__new__(DownloadApp)
        app.server_list = FakeTree()

        app._drag_start(SimpleNamespace(y=10))

        self.assertEqual(app.drag_names, ["one.txt", "two.txt"])

    def test_drag_release_adds_saved_group_when_inside_download_area(self):
        app = DownloadApp.__new__(DownloadApp)
        app.download_list = FakeDownloadArea()
        app.drag_names = ["one.txt", "two.txt"]
        app.add_files = lambda names: received_names.extend(names)
        received_names = []

        app._drag_end(SimpleNamespace(x_root=150, y_root=150))

        self.assertEqual(received_names, ["one.txt", "two.txt"])
        self.assertEqual(app.drag_names, [])

    def test_queue_does_not_start_more_than_limit(self):
        app = DownloadApp.__new__(DownloadApp)
        app.limit = 3
        app.active = 0
        app.waiting = [(str(number), f"{number}.txt") for number in range(6)]
        app._set_row = lambda *_: None
        FakeThread.started = 0

        with patch("client_gui.threading.Thread", FakeThread):
            app._start_waiting()

        self.assertEqual(app.active, 3)
        self.assertEqual(len(app.waiting), 3)
        self.assertEqual(FakeThread.started, 3)

    def test_same_file_can_be_added_more_than_once(self):
        app = DownloadApp.__new__(DownloadApp)
        app.server_list = FakeTree()
        app.download_list = FakeDownloadArea()
        app.waiting = []
        app.limit = 3
        app.active = 0
        app._start_waiting = lambda: None

        app.add_files(["one.txt"])
        app.add_files(["one.txt"])

        self.assertEqual(len(app.download_list.rows), 2)
        self.assertEqual(
            [job[1] for job in app.waiting],
            ["one.txt", "one.txt"],
        )


if __name__ == "__main__":
    unittest.main()
