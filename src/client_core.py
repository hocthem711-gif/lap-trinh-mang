"""Client Core kết nối Server và lưu một file nhận được."""

import os
import socket
from pathlib import Path

from protocol import CHUNK_SIZE, recv_message, send_message


def download_file(
    host: str,
    port: int,
    filename: str,
    output_dir: str,
) -> str:
    """Tải một file, lưu tạm trước rồi đổi tên khi nhận đủ dữ liệu."""
    if (
        not filename
        or filename in {".", ".."}
        or ".." in filename
        or "/" in filename
        or "\\" in filename
        or any(character in filename for character in '<>:"|?*')
    ):
        raise ValueError("Tên file không hợp lệ")

    os.makedirs(output_dir, exist_ok=True)
    temporary_path = Path(output_dir) / f"{filename}.part"

    try:
        with socket.create_connection((host, port), timeout=10) as server:
            server.settimeout(10)
            send_message(server, {"command": "GET", "name": filename})
            response = recv_message(server)
            if response.get("status") != "OK":
                raise RuntimeError(response.get("message", "Server báo lỗi"))

            size = response.get("size")
            if not isinstance(size, int) or size < 0:
                raise ValueError("Kích thước file Server gửi không hợp lệ")

            received = 0
            with temporary_path.open("wb") as output:
                while received < size:
                    chunk = server.recv(min(CHUNK_SIZE, size - received))
                    if not chunk:
                        raise ConnectionError("Server ngắt kết nối khi gửi file")
                    output.write(chunk)
                    received += len(chunk)

        final_path = Path(output_dir) / filename
        number = 1
        while final_path.exists():
            final_path = Path(output_dir) / f"{Path(filename).stem} ({number}){Path(filename).suffix}"
            number += 1
        os.replace(temporary_path, final_path)
        return str(final_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
