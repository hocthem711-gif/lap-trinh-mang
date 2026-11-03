"""Các thao tác TCP của Client: LIST và tải file."""

import os
import socket
import tempfile
import time
from typing import Callable

from protocol import CHUNK_SIZE, SOCKET_TIMEOUT, recv_message, send_message

ProgressCallback = Callable[[int, int, float], None]


def list_files(host: str, port: int) -> list[dict]:
    """Mở kết nối LIST riêng, nhận tên/kích thước file rồi đóng kết nối."""
    with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT) as server:
        server.settimeout(SOCKET_TIMEOUT)
        send_message(server, {"command": "LIST"})
        response = recv_message(server)

    files = response.get("files")
    if response.get("status") != "OK" or not isinstance(files, list):
        raise RuntimeError(response.get("message", "Server không trả được danh sách file"))
    for file_info in files:
        if (
            not isinstance(file_info, dict)
            or not isinstance(file_info.get("name"), str)
            or not isinstance(file_info.get("size"), int)
            or file_info["size"] < 0
        ):
            raise ValueError("Danh sách file Server gửi không hợp lệ")
    return files


def _choose_output_path(download_dir: str, filename: str) -> tuple[str, bool]:
    """Đặt trước một tên file chưa tồn tại để tránh ghi đè khi tải đồng thời."""
    name, extension = os.path.splitext(filename)
    number = 0
    while True:
        suffix = f" ({number})" if number else ""
        output_path = os.path.join(download_dir, f"{name}{suffix}{extension}")
        try:
            descriptor = os.open(
                output_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            os.close(descriptor)
            return output_path, number > 0
        except FileExistsError:
            number += 1


def download_file(
    host: str,
    port: int,
    filename: str,
    download_dir: str,
    on_progress: ProgressCallback,
) -> tuple[str, bool]:
    """Tải vào file .part rồi đổi tên sau khi nhận đủ byte."""
    if (
        not filename
        or filename in {".", ".."}
        or ".." in filename
        or "/" in filename
        or "\\" in filename
        or any(character in filename for character in '<>:"|?*')
    ):
        raise ValueError("Tên file không hợp lệ")

    os.makedirs(download_dir, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".udm11-", suffix=".part", dir=download_dir
    )
    os.close(descriptor)

    try:
        # Mỗi file GET có TCP socket riêng để lỗi được cô lập theo từng file.
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT) as server:
            server.settimeout(SOCKET_TIMEOUT)
            send_message(server, {"command": "GET", "name": filename})
            response = recv_message(server)
            if response.get("status") != "OK":
                code = response.get("code", "SERVER_ERROR")
                raise RuntimeError(f"{code}: {response.get('message', 'Lỗi Server')}")

            size = response.get("size")
            if not isinstance(size, int) or size < 0:
                raise ValueError("Kích thước file Server gửi không hợp lệ")

            received = 0
            last_update = time.monotonic()
            previous_received = 0
            # File chưa hoàn chỉnh chỉ được ghi vào .part, không ghi vào tên cuối.
            with open(temporary_path, "wb") as output:
                while received < size:
                    chunk = server.recv(min(CHUNK_SIZE, size - received))
                    if not chunk:
                        raise ConnectionError(f"Server ngắt kết nối ({received}/{size} byte)")
                    output.write(chunk)
                    received += len(chunk)

                    now = time.monotonic()
                    if now - last_update >= 0.5:
                        # Tốc độ được tính từ số byte nhận trong khoảng thời gian vừa qua.
                        speed = (received - previous_received) / (now - last_update)
                        on_progress(received, size, speed)
                        previous_received = received
                        last_update = now

        output_path, renamed = _choose_output_path(download_dir, filename)
        try:
            # Chỉ công bố file hoàn chỉnh sau khi vòng lặp nhận đủ size byte.
            os.replace(temporary_path, output_path)
        except OSError:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise
        on_progress(size, size, 0)
        return str(output_path), renamed
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
