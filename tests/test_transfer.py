"""Kiểm thử luồng tải file từ Client qua TCP đến Server."""

import logging 
import os 
import socket 
import sys 
import tempfile 
import threading  
import unittest 
from pathlib import Path 

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src")) 
from client_core import download_file 
from file_service import handle_client 


class TransferTests(unittest.TestCase):  
    """Dùng loopback TCP thật nhưng không cần mở GUI."""

    def test_client_reads_file_from_server(self): 
        with tempfile.TemporaryDirectory() as share_dir: 
            with tempfile.TemporaryDirectory() as output_dir: 
                filename = "hello.txt" 
                expected = b"Hello from the checkpoint server." 
                with open(os.path.join(share_dir, filename), "wb") as file: 
                    file.write(expected) 

                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
                listener.bind(("127.0.0.1", 0)) 
                listener.listen(1) 
                port = listener.getsockname()[1] 
                logger = logging.getLogger("demo.test.server") 

                def serve_one_request(): 
                    client, _ = listener.accept() 
                    with client: 
                        handle_client(client, share_dir, logger) 
                    listener.close() 

                server_thread = threading.Thread(target=serve_one_request) 
                server_thread.start() 
                saved_path = download_file( 
                    "127.0.0.1", port, filename, output_dir 
                ) 
                server_thread.join(timeout=3) 

                self.assertFalse(server_thread.is_alive()) 
                with open(saved_path, "rb") as file: 
                    self.assertEqual(file.read(), expected) 
                self.assertEqual(os.listdir(output_dir), [filename]) 


if __name__ == "__main__": 
    unittest.main() 
