"""Kiểm tra LIST/GET và dọn file tạm khi kết nối bị ngắt."""

import logging
import os
import socket
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client_core import download_file, list_files
from file_service import handle_request, is_valid_filename
from protocol import recv_message, send_message


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.shared = tempfile.TemporaryDirectory()
        self.downloads = tempfile.TemporaryDirectory()
        self.logger = logging.getLogger("udm11.test")

    def tearDown(self):
        self.shared.cleanup()
        self.downloads.cleanup()

    def test_invalid_path_name_is_rejected(self):
        self.assertFalse(is_valid_filename("../secret.txt"))
        self.assertFalse(is_valid_filename(r"..\secret.txt"))
        self.assertTrue(is_valid_filename("hello.txt"))

    def test_server_returns_error_for_path_traversal(self):
        port, thread = self.start_server()
        with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
            send_message(client, {"command": "GET", "name": "../secret.txt"})
            response = recv_message(client)
        thread.join(timeout=2)
        self.assertEqual(response["status"], "ERROR")
        self.assertEqual(response["code"], "INVALID_NAME")

    def test_server_reports_missing_file(self):
        port, thread = self.start_server()
        with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
            send_message(client, {"command": "GET", "name": "missing.txt"})
            response = recv_message(client)
        thread.join(timeout=2)
        self.assertEqual(response["status"], "ERROR")
        self.assertEqual(response["code"], "FILE_NOT_FOUND")

    def start_server(self, count=1):
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

    def test_list_and_download_file_over_tcp(self):
        content = bytes(range(256)) * 40
        with open(os.path.join(self.shared.name, "hello.txt"), "wb") as file:
            file.write(content)
        port, thread = self.start_server(count=2)

        files = list_files("127.0.0.1", port)
        self.assertEqual(files[0]["name"], "hello.txt")
        self.assertEqual(files[0]["size"], len(content))
        path, renamed = download_file(
            "127.0.0.1", port, "hello.txt", self.downloads.name, lambda *_: None
        )
        thread.join(timeout=2)
        self.assertFalse(renamed)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), content)

    def test_interrupted_transfer_removes_part_file(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        def send_incomplete_file():
            client, _ = listener.accept()
            with client:
                recv_message(client)
                send_message(client, {"status": "OK", "size": 100})
                client.sendall(b"short")
            listener.close()

        thread = threading.Thread(target=send_incomplete_file, daemon=True)
        thread.start()
        with self.assertRaises(ConnectionError):
            download_file(
                "127.0.0.1", port, "partial.txt", self.downloads.name, lambda *_: None
            )
        thread.join(timeout=2)
        self.assertEqual(os.listdir(self.downloads.name), [])

    def test_existing_destination_is_renamed(self):
        with open(os.path.join(self.shared.name, "hello.txt"), "wb") as file:
            file.write(b"new data")
        existing = os.path.join(self.downloads.name, "hello.txt")
        with open(existing, "wb") as file:
            file.write(b"old data")
        port, thread = self.start_server()

        path, renamed = download_file(
            "127.0.0.1", port, "hello.txt", self.downloads.name, lambda *_: None
        )
        thread.join(timeout=2)
        self.assertTrue(renamed)
        self.assertEqual(os.path.basename(path), "hello (1).txt")
        with open(existing, "rb") as file:
            self.assertEqual(file.read(), b"old data")

    def test_same_file_can_be_downloaded_twice_in_one_session(self):
        content = b"download the same file again"
        with open(os.path.join(self.shared.name, "again.txt"), "wb") as file:
            file.write(content)
        port, thread = self.start_server(count=2)

        first_path, first_renamed = download_file(
            "127.0.0.1", port, "again.txt", self.downloads.name, lambda *_: None
        )
        second_path, second_renamed = download_file(
            "127.0.0.1", port, "again.txt", self.downloads.name, lambda *_: None
        )
        thread.join(timeout=2)

        self.assertFalse(first_renamed)
        self.assertTrue(second_renamed)
        self.assertNotEqual(first_path, second_path)
        for path in (first_path, second_path):
            with open(path, "rb") as file:
                self.assertEqual(file.read(), content)


if __name__ == "__main__":
    unittest.main()
