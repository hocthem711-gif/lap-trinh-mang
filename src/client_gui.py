"""Ứng dụng dòng lệnh để nhập tên file và tải từ Server."""

import argparse  

from client_core import download_file  
from logger_setup import create_logger  


def parse_args() -> argparse.Namespace:  
    """Đọc địa chỉ Server và thư mục lưu file."""
    parser = argparse.ArgumentParser(description="UDM_11 demo checkpoint 1 client")  
    parser.add_argument("--host", default="127.0.0.1")  
    parser.add_argument("--port", type=int, default=5000)  
    parser.add_argument("--output-dir", default="downloads")  
    return parser.parse_args()  


def main() -> None:  
    """Nhận tên file từ bàn phím, tải file và báo kết quả."""
    args = parse_args()  
    logger = create_logger("demo.client")  
    filename = input("Nhập tên file cần đọc từ Server: ").strip()  
    if not filename:  
        print("Tên file không được để trống.")  
        return  

    try:  
        saved_path = download_file(  
            args.host, args.port, filename, args.output_dir  
        )  
        logger.info("Tải thành công, file được lưu tại: %s", saved_path)  
    except (OSError, RuntimeError, ValueError) as error:  
        logger.error("Không tải được file: %s", error)  


if __name__ == "__main__":  
    main()  
