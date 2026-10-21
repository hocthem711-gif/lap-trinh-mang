"""Server xử lý yêu cầu đọc một file trong thư mục chia sẻ."""

import logging
import os
import socket
from pathlib import Path

from protocol import CHUNK_SIZE, recv_message, send_message


def is_valid_name(name: object) -> bool:
    return (
        isinstance(name, str)
        and bool(name)
        and name not in {".", ".."}
        and ".." not in name
        and "/" not in name
        and "\\" not in name
        and not any(character in name for character in '<>:"|?*')
        and not os.path.isabs(name)
        and Path(name).name == name
    )


def handle_client(
    client: socket.socket,
    share_dir: str,
    logger: logging.Logger,
) -> None:
    """Nhận lệnh GET, trả kích thước file rồi gửi nội dung theo chunk."""
    try:
        request = recv_message(client)
        if request.get("command") != "GET":
            send_message(client, {
                "status": "ERROR",
                "message": "Lệnh hỗ trợ duy nhất hiện tại là GET",
            })
            return

        filename = request.get("name")
        if not is_valid_name(filename):
            send_message(client, {
                "status": "ERROR",
                "message": "Tên file không hợp lệ",
            })
            return

        root = Path(share_dir).resolve()
        file_path = (root / filename).resolve()
        if file_path.parent != root or not file_path.is_file():
            send_message(client, {
                "status": "ERROR",
                "message": "Không tìm thấy file trong thư mục chia sẻ",
            })
            return

        size = file_path.stat().st_size
        send_message(client, {"status": "OK", "size": size})
        with file_path.open("rb") as file:
            while True:
                chunk = file.read(CHUNK_SIZE)
                if not chunk:
                    break
                client.sendall(chunk)
        logger.info("Đã gửi file %s (%d byte)", filename, size)
    except (OSError, ValueError, ConnectionError, socket.timeout):
        logger.exception("Không xử lý được yêu cầu Client")
