"""Các thao tác mạng của Client: lấy danh sách file và tải file."""

import os
import socket
import tempfile
import time

from protocol import CHUNK_SIZE, SOCKET_TIMEOUT, recv_message, send_message


def is_valid_filename(filename):
    """Chỉ chấp nhận tên file đơn, để tên do Server gửi không ghi ra ngoài thư mục tải."""
    return (
        isinstance(filename, str)
        and bool(filename)
        and filename not in {".", ".."}
        and ".." not in filename
        and "/" not in filename
        and "\\" not in filename
        and "\0" not in filename
        and not os.path.isabs(filename)
        and os.path.basename(filename) == filename
        and not any(character in filename for character in '<>:"|?*')  # ký tự Windows cấm
    )


def list_files(host, port):
    """Mở kết nối riêng gửi LIST, nhận danh sách [{name, size}] rồi đóng kết nối."""
    with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT) as server:
        server.settimeout(SOCKET_TIMEOUT)
        send_message(server, {"command": "LIST"})
        response = recv_message(server)

    if response.get("status") != "OK":
        code = response.get("code", "SERVER_ERROR")
        message = response.get("message", "Server không trả được danh sách file")
        raise RuntimeError(f"{code}: {message}")

    files = response.get("files")
    if not isinstance(files, list):
        raise ValueError("Danh sách file Server gửi không hợp lệ")
    for file_info in files:
        if (
            not isinstance(file_info, dict)
            or not is_valid_filename(file_info.get("name"))
            or type(file_info.get("size")) is not int  # loại bool, vì True cũng là int
            or file_info["size"] < 0
        ):
            raise ValueError("Thông tin file Server gửi không hợp lệ")
    return files


def choose_output_path(download_dir, filename):
    """Quy tắc file đã tồn tại: giữ cả hai, file mới đổi tên thành 'ten (1).txt', 'ten (2).txt'..."""
    name, extension = os.path.splitext(filename)
    number = 0
    while True:
        suffix = f" ({number})" if number else ""
        path = os.path.join(download_dir, f"{name}{suffix}{extension}")
        try:
            # O_EXCL: tạo thất bại nếu file đã có, nên hai luồng tải cùng tên không ghi đè nhau.
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return path, number > 0
        except FileExistsError:
            number += 1


def download_file(host, port, filename, download_dir, on_progress):
    """Tải vào file .part, nhận đủ byte mới đổi tên thành file chính thức.

    on_progress(đã_nhận, tổng, tốc_độ_byte_trên_giây) được gọi khoảng mỗi 0,5 giây.
    Trả về (đường_dẫn_file, có_bị_đổi_tên).
    """
    if not is_valid_filename(filename):
        raise ValueError("Tên file không hợp lệ")

    os.makedirs(download_dir, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=".udm11-", suffix=".part", dir=download_dir
    )
    os.close(descriptor)
    reserved_path = None  # tên đích đã đặt chỗ, dùng để dọn nếu đổi tên thất bại

    try:
        # Mỗi file một socket riêng, nên lỗi của file này không ảnh hưởng file khác.
        with socket.create_connection((host, port), timeout=SOCKET_TIMEOUT) as server:
            server.settimeout(SOCKET_TIMEOUT)
            send_message(server, {"command": "GET", "name": filename})
            response = recv_message(server)
            if response.get("status") != "OK":
                code = response.get("code", "SERVER_ERROR")
                message = response.get("message", "Lỗi Server")
                raise RuntimeError(f"{code}: {message}")

            size = response.get("size")
            if type(size) is not int or size < 0:
                raise ValueError("Kích thước file Server gửi không hợp lệ")

            received = 0
            previous_received = 0
            last_update = time.monotonic()
            with open(temporary_path, "wb") as output:
                while received < size:
                    # Chỉ đọc đúng số byte còn thiếu: TCP là luồng byte, không có ranh giới file.
                    chunk = server.recv(min(CHUNK_SIZE, size - received))
                    if not chunk:
                        raise ConnectionError(f"Server ngắt kết nối ({received}/{size} byte)")
                    output.write(chunk)
                    received += len(chunk)

                    now = time.monotonic()
                    if now - last_update >= 0.5:  # báo mỗi 0,5 giây để không làm GUI quá tải
                        speed = (received - previous_received) / (now - last_update)
                        on_progress(received, size, speed)
                        previous_received = received
                        last_update = now

        output_path, renamed = choose_output_path(download_dir, filename)
        reserved_path = output_path
        os.replace(temporary_path, output_path)  # chỉ công bố file sau khi đã nhận đủ byte
        reserved_path = None
        on_progress(size, size, 0)
        return output_path, renamed
    finally:
        # Lỗi giữa chừng thì xóa file dở dang; tải thành công thì .part đã được đổi tên.
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        if reserved_path and os.path.exists(reserved_path):
            os.remove(reserved_path)
