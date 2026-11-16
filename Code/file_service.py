"""Xử lý yêu cầu LIST/GET của một Client."""

import os

from protocol import CHUNK_SIZE, recv_message, send_message


def is_valid_filename(name):
    """Chỉ chấp nhận tên file đơn, không phải đường dẫn."""
    return (
        isinstance(name, str)
        and bool(name)
        and name not in {".", ".."}
        and ".." not in name
        and "/" not in name
        and "\\" not in name
        and "\0" not in name
        and not os.path.isabs(name)
        and os.path.basename(name) == name
        and not any(character in name for character in '<>:"|?*')
    )


def send_error(client, code, message):
    """Trả lỗi rõ ràng cho Client theo cùng định dạng JSON."""
    send_message(client, {"status": "ERROR", "code": code, "message": message})


def handle_request(client, share_dir, logger):
    """Nhận một lệnh: LIST trả danh sách file, GET gửi nội dung file."""
    try:
        request = recv_message(client)
    except (UnicodeError, ValueError) as error:
        logger.warning("Client gửi header không hợp lệ: %s", error)
        send_error(client, "BAD_REQUEST", "Header JSON không hợp lệ")
        return

    command = request.get("command")
    if command == "LIST":
        send_file_list(client, share_dir, logger)
    elif command == "GET":
        send_file(client, share_dir, request.get("name"), logger)
    else:
        logger.warning("Client gửi lệnh không hợp lệ: %r", command)
        send_error(client, "BAD_REQUEST", "Lệnh chỉ hỗ trợ LIST hoặc GET")


def send_file_list(client, share_dir, logger):
    try:
        root = os.path.realpath(share_dir)
        files = []
        for name in os.listdir(root):
            path = os.path.realpath(os.path.join(root, name))
            if (
                is_valid_filename(name)
                and os.path.dirname(path) == root
                and os.path.isfile(path)
            ):
                files.append({"name": name, "size": os.path.getsize(path)})
        files.sort(key=lambda item: item["name"].lower())
    except OSError:
        logger.exception("Không đọc được thư mục chia sẻ")
        send_error(client, "INTERNAL_ERROR", "Không đọc được thư mục chia sẻ")
        return
    send_message(client, {"status": "OK", "files": files})
    logger.info("LIST: %d file", len(files))


def send_file(client, share_dir, name, logger):
    if not is_valid_filename(name):
        send_error(client, "INVALID_NAME", "Tên file không hợp lệ")
        return

    root = os.path.realpath(share_dir)
    path = os.path.realpath(os.path.join(root, name))
    if os.path.dirname(path) != root or not os.path.isfile(path):
        logger.warning("Client yêu cầu file không tồn tại hoặc không thể truy cập: %s", name)
        send_error(client, "FILE_NOT_FOUND", "Không tìm thấy file trong thư mục chia sẻ")
        return

    try:
        source = open(path, "rb")
    except OSError:
        logger.exception("Không mở được file %s", name)
        send_error(client, "INTERNAL_ERROR", "Không thể mở file trên Server")
        return

    with source:  # tự đóng file kể cả khi gửi lỗi giữa chừng
        size = os.fstat(source.fileno()).st_size
        send_message(client, {"status": "OK", "size": size})
        while True:
            chunk = source.read(CHUNK_SIZE)
            if not chunk:
                break
            client.sendall(chunk)
    logger.info("GET: đã gửi file %s (%d byte)", name, size)
