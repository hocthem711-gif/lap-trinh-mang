"""Kiểm tra phản hồi Server và xử lý tải file phía Client."""

import logging
import os
import socket
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client_core import download_file, list_files
from file_service import handle_request
from protocol import recv_message, send_message


class ClientCoreTests(unittest.TestCase):
    def setUp(self):
        self.shared = tempfile.TemporaryDirectory()
        self.downloads = tempfile.TemporaryDirectory()
        self.logger = logging.getLogger("udm11.client_core.test")

    def tearDown(self):
        self.shared.cleanup()
        self.downloads.cleanup()

    def test_list_rejects_invalid_metadata(self):
        port, thread = self.start_response_server({
            "status": "OK",
            "files": [{"name": "../secret.txt", "size": 1}],
        })

        with self.assertRaisesRegex(ValueError, "Thông tin file"):
            list_files("127.0.0.1", port)
        thread.join(timeout=2)

    def test_list_reports_server_error_code(self):
        port, thread = self.start_response_server({
            "status": "ERROR",
            "code": "LIST_FAILED",
            "message": "Không đọc được thư mục",
        })

        with self.assertRaisesRegex(RuntimeError, "LIST_FAILED"):
            list_files("127.0.0.1", port)
        thread.join(timeout=2)

    def test_download_error_removes_temporary_file(self):
        port, thread = self.start_response_server({
            "status": "ERROR",
            "code": "FILE_NOT_FOUND",
            "message": "Không tìm thấy file",
        })

        with self.assertRaisesRegex(RuntimeError, "FILE_NOT_FOUND"):
            download_file(
                "127.0.0.1", port, "missing.txt", self.downloads.name, lambda *_: None
            )
        thread.join(timeout=2)
        self.assertEqual(os.listdir(self.downloads.name), [])

    def test_download_rejects_invalid_size(self):
        port, thread = self.start_response_server({"status": "OK", "size": True})

        with self.assertRaisesRegex(ValueError, "Kích thước"):
            download_file(
                "127.0.0.1", port, "invalid.txt", self.downloads.name, lambda *_: None
            )
        thread.join(timeout=2)
        self.assertEqual(os.listdir(self.downloads.name), [])

    def test_invalid_filename_is_rejected_before_connecting(self):
        with self.assertRaisesRegex(ValueError, "Tên file"):
            download_file(
                "127.0.0.1", 1, "../secret.txt", self.downloads.name, lambda *_: None
            )
        self.assertEqual(os.listdir(self.downloads.name), [])

    def test_parallel_downloads_get_distinct_names(self):
        content = b"parallel transfer" * 1000
        with open(os.path.join(self.shared.name, "shared.txt"), "wb") as file:
            file.write(content)
        port, thread = self.start_file_server(2)

        def download():
            return download_file(
                "127.0.0.1", port, "shared.txt", self.downloads.name, lambda *_: None
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: download(), range(2)))
        thread.join(timeout=2)

        self.assertEqual(
            {os.path.basename(path) for path, _ in results},
            {"shared.txt", "shared (1).txt"},
        )
        for path, _ in results:
            with open(path, "rb") as file:
                self.assertEqual(file.read(), content)

    def start_response_server(self, response):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        def serve():
            try:
                client, _ = listener.accept()
                with client:
                    recv_message(client)
                    send_message(client, response)
            finally:
                listener.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        return port, thread

    def start_file_server(self, count):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        def serve():
            try:
                for _ in range(count):
                    client, _ = listener.accept()
                    with client:
                        handle_request(client, self.shared.name, self.logger)
            finally:
                listener.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        return port, thread


if __name__ == "__main__":
    unittest.main()
