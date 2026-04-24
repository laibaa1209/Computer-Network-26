import random
import time
from packet import Packet

class NetworkChannel:
    def __init__(self, loss_prob=0.1, corruption_prob=0.1, delay_range=(0.01, 0.05)):
        self.loss_prob = loss_prob
        self.corruption_prob = corruption_prob
        self.delay_range = delay_range

    def send(self, packet, destination_queue):
        """Simulates sending a packet with potential loss, corruption, and delay."""
        
        # 1. Simulate Loss
        if random.random() < self.loss_prob:
            return "LOST"

        # 2. Simulate Delay
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

        # 3. Simulate Corruption
        if random.random() < self.corruption_prob:
            packet = self._corrupt_packet(packet)
            destination_queue.append(packet)
            return "CORRUPTED"

        # 4. Success
        destination_queue.append(packet)
        return "SUCCESS"

    def _corrupt_packet(self, packet):
        # Corrupt the packet by changing its checksum
        packet.checksum = "INVALID_CHECKSUM"
        return packet
