import json
import hashlib

class Packet:
    def __init__(self, seq_num, data, is_ack=False, ack_num=None):
        self.seq_num = seq_num
        self.data = data
        self.is_ack = is_ack
        self.ack_num = ack_num if ack_num is not None else seq_num
        self.checksum = self.calculate_checksum()

    def calculate_checksum(self):
        # Simple checksum using hashlib for reliability simulation
        content = f"{self.seq_num}|{self.data}|{self.is_ack}|{self.ack_num}"
        return hashlib.md5(content.encode()).hexdigest()

    def is_corrupt(self):
        return self.checksum != self.calculate_checksum()

    def __repr__(self):
        type_str = "ACK" if self.is_ack else "DATA"
        return f"Packet({type_str}, seq={self.seq_num}, ack={self.ack_num})"
