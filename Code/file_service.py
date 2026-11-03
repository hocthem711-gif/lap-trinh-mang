"""Xử lý LIST/GET và truyền file nằm trong thư mục chia sẻ."""

import logging
import os
import socket

from protocol import CHUNK_SIZE, recv_message, send_message


def is_valid_filename(name: object) -> bool:
    """Chỉ cho phép tên file đơn; từ chối đường dẫn và ký tự không hợp lệ."""
    return (
        isinstance(name, str)
        and bool(name)
        and name not in {".", ".."}
        and ".." not in name
        and "/" not in name
        and "\\" not in name
        and not os.path.isabs(name)
        and os.path.basename(name) == name
        and not any(character in name for character in '<>:"|?*')
    )


def handle_request(
    client: socket.socket,
    share_dir: str,
    logger: logging.Logger,
) -> None:
    """Nhận một lệnh, trả header JSON và gửi body file nếu lệnh là GET."""
    try:
        request = recv_message(client)
    except (ConnectionError, socket.timeout) as error:
        logger.info("Client đóng kết nối khi gửi header: %s", error)
        return
    except (UnicodeError, ValueError) as error:
        logger.warning("Client gửi header không hợp lệ: %s", error)
        try:
            send_message(client, {
                "status": "ERROR",
                "code": "BAD_REQUEST",
                "message": "Header JSON không hợp lệ",
            })
        except OSError:
            logger.exception("Không gửi được phản hồi lỗi cho Client")
        return

    command = request.get("command")
    logger.info("Nhận lệnh %s", command)

    if command == "LIST":
        try:
            # realpath và kiểm tra thư mục cha để không liệt kê file qua symlink ra ngoài.
            root = os.path.realpath(share_dir)
            files = []
            for filename in os.listdir(root):
                path = os.path.realpath(os.path.join(root, filename))
                if os.path.dirname(path) == root and os.path.isfile(path):
                    files.append({"name": filename, "size": os.path.getsize(path)})
            files.sort(key=lambda item: item["name"].lower())
            send_message(client, {"status": "OK", "files": files})
            logger.info("Đã trả danh sách %d file", len(files))
        except OSError:
            logger.exception("Không đọc được thư mục chia sẻ")
            try:
                send_message(client, {
                    "status": "ERROR",
                    "code": "INTERNAL_ERROR",
                    "message": "Không đọc được thư mục chia sẻ",
                })
            except OSError:
                logger.exception("Không gửi được phản hồi lỗi cho Client")
        return

    if command != "GET":
        send_message(client, {
            "status": "ERROR",
            "code": "BAD_REQUEST",
            "message": "Lệnh chỉ hỗ trợ LIST hoặc GET",
        })
        return

    filename = request.get("name")
    if not is_valid_filename(filename):
        send_message(client, {
            "status": "ERROR",
            "code": "INVALID_NAME",
            "message": "Tên file không hợp lệ",
        })
        logger.warning("Từ chối tên file không hợp lệ")
        return

    root = os.path.realpath(share_dir)
    # Chuẩn hóa đường dẫn rồi xác nhận file vẫn nằm ngay trong thư mục chia sẻ.
    file_path = os.path.realpath(os.path.join(root, filename))
    if os.path.dirname(file_path) != root or not os.path.isfile(file_path):
        send_message(client, {
            "status": "ERROR",
            "code": "FILE_NOT_FOUND",
            "message": "Không tìm thấy file trong thư mục chia sẻ",
        })
        return

    source = None
    try:
        source = open(file_path, "rb")
        size = os.fstat(source.fileno()).st_size
    except OSError:
        logger.exception("Không mở được file %s", filename)
        if source is not None:
            source.close()
        try:
            send_message(client, {
                "status": "ERROR",
                "code": "INTERNAL_ERROR",
                "message": "Không thể mở file trên Server",
            })
        except OSError:
            logger.exception("Không gửi được phản hồi lỗi cho Client")
        return

    with source:
        # Gửi kích thước trước để Client biết chính xác khi nào nhận đủ file.
        send_message(client, {"status": "OK", "size": size})
        try:
            while True:
                chunk = source.read(CHUNK_SIZE)
                if not chunk:
                    break
                # sendall gửi đủ chunk hiện tại trước khi Server đọc chunk kế tiếp.
                client.sendall(chunk)
            logger.info("Gửi xong file %s (%d byte)", filename, size)
        except (ConnectionError, OSError, socket.timeout):
            logger.exception("Lỗi khi truyền file %s", filename)
