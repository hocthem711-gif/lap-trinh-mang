"""Kiểm thử gửi và nhận một JSON header."""

import socket
import sys 
import unittest 
from pathlib import Path 

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src")) 
from protocol import recv_message, send_message  


class ProtocolTests(unittest.TestCase):  
    def test_json_message_round_trip(self): 
        sender, receiver = socket.socketpair() 
        try: 
            send_message(sender, {"command": "GET", "name": "hello.txt"}) 
            self.assertEqual( 
                recv_message(receiver), 
                {"command": "GET", "name": "hello.txt"}, 
            ) 
        finally: 
            sender.close() 
            receiver.close() 


if __name__ == "__main__": 
    unittest.main() 
